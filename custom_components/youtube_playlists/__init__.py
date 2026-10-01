"""YouTube Playlists integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

from aiohttp import ClientResponseError
import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.loader import async_get_integration

from .api import YouTubeApi
from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    CONF_PLAY_MEDIA_PLAYER,
    CONF_PLAY_SCRIPT,
    CONF_PLAY_TARGET_MODE,
    DOMAIN,
    PLAY_TARGET_MEDIA_PLAYER,
    PLAY_TARGET_SCRIPT,
    SERVICE_PLAY_VIDEO,
)
from .coordinator import YouTubeCoordinator
from .play import async_play_on_media_player
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

type YouTubeConfigEntry = ConfigEntry[YouTubeCoordinator]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    async_register_websocket(hass)
    await _async_register_frontend_card(hass)
    return True


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and register it for the frontend.

    This means users never need to manually add a Lovelace resource -
    installing (or updating) the integration is enough.

    IMPORTANT: this is added as a Lovelace *resource*, not via
    ``add_extra_js_url()``. add_extra_js_url() injects a <script> into the
    frontend's index page, so it loads during bootstrap, racing Home
    Assistant's own app bundle. That bundle installs a scoped custom-element
    registry over window.customElements; if our script's customElements
    .define() runs first, it lands in the *native* registry, the scoped one
    then shadows it, and Lovelace's customElements.get("youtube-playlist-card")
    comes back empty even though the element is registered. That is the
    intermittent "Custom element doesn't exist" error - it is a registry race,
    not a loading failure, which is also why it clears up on some reloads and
    a warm cache makes it worse rather than better. Lovelace resources are
    fetched by the dashboard loader well after bootstrap, so they always see
    the scoped registry already in place.
    """
    www_dir = Path(__file__).parent / "www"

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(www_dir), cache_headers=False)]
        )
    except AttributeError:
        # Fallback for older Home Assistant cores without the async API.
        hass.http.register_static_path(CARD_URL_PATH, str(www_dir), cache_headers=False)

    # Bust the browser cache automatically whenever the integration version changes,
    # so users don't have to manually edit a ?v= query string after every update.
    integration = await async_get_integration(hass, DOMAIN)
    card_url = f"{CARD_URL_PATH}/{CARD_FILENAME}?v={integration.version}"

    if await _async_register_lovelace_resource(hass, card_url):
        return

    # Fall back to add_extra_js_url for YAML-mode Lovelace (which has no
    # resource storage to write to) or if anything above went wrong. This
    # keeps the card working, just with a small chance of the registry race
    # this function exists to avoid.
    _LOGGER.warning(
        "Could not register %s as a Lovelace resource; falling back to "
        "add_extra_js_url. If the card intermittently fails to load with "
        "'Custom element doesn't exist', add it manually as a Lovelace "
        "resource (Settings > Dashboards > Resources) instead.",
        card_url,
    )
    add_extra_js_url(hass, card_url)


async def _async_register_lovelace_resource(hass: HomeAssistant, card_url: str) -> bool:
    """Add ``card_url`` as a Lovelace module resource, if possible.

    Returns True if the resource is registered (or already was), False if
    Lovelace resource storage isn't available here (YAML resource mode, or
    Lovelace not set up) and the caller should fall back.
    """
    try:
        from homeassistant.components.lovelace.resources import (  # noqa: PLC0415
            ResourceStorageCollection,
        )

        lovelace_data = hass.data.get("lovelace")
        resources = getattr(lovelace_data, "resources", None)
        if resources is None and isinstance(lovelace_data, dict):
            resources = lovelace_data.get("resources")  # older HA cores
        if not isinstance(resources, ResourceStorageCollection):
            # Either Lovelace isn't set up yet, or it's in YAML resource mode
            # (ResourceYAMLCollection), which has no way to add items -
            # editing resources there means editing the user's YAML file.
            return False

        # async_get_info() forces the collection to load; async_items() alone
        # does not, and would look empty (and so create a duplicate) on an
        # unloaded collection every restart.
        await resources.async_get_info()

        prefix = card_url.split("?", 1)[0]
        already_present = any(
            item.get("url", "").split("?", 1)[0] == prefix
            for item in resources.async_items() or []
        )
        if already_present:
            return True

        await resources.async_create_item({"res_type": "module", "url": card_url})
        _LOGGER.debug("Registered %s as a Lovelace resource", card_url)
        return True
    except Exception:  # noqa: BLE001 - never break setup over the card resource
        _LOGGER.debug(
            "Registering %s as a Lovelace resource failed; will fall back",
            card_url,
            exc_info=True,
        )
        return False


async def async_setup_entry(hass: HomeAssistant, entry: YouTubeConfigEntry) -> bool:
    """Set up YouTube Playlists from a config entry."""
    try:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    except config_entry_oauth2_flow.ImplementationUnavailableError as err:
        raise ConfigEntryNotReady(
            "OAuth implementation temporarily unavailable"
        ) from err

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    api = YouTubeApi(hass, session)
    coordinator = YouTubeCoordinator(hass, entry, api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ClientResponseError as err:
        if err.status in (401, 403):
            raise ConfigEntryAuthFailed from err
        raise ConfigEntryNotReady from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def _async_handle_play_video(call: ServiceCall) -> None:
        """Route a play request to either the configured script or media_player."""
        video_id = call.data["video_id"]
        mode = entry.options.get(CONF_PLAY_TARGET_MODE, PLAY_TARGET_SCRIPT)
        media_player_entity = entry.options.get(CONF_PLAY_MEDIA_PLAYER)

        if mode == PLAY_TARGET_MEDIA_PLAYER and media_player_entity:
            await async_play_on_media_player(
                hass, entry, media_player_entity, video_id
            )
            return

        script_entity_id = entry.options.get(CONF_PLAY_SCRIPT)
        if not script_entity_id:
            _LOGGER.error(
                "No script configured for YouTube Playlists playback. "
                "Set one under Settings > Devices & Services > YouTube Playlists > Configure."
            )
            return

        domain, object_id = script_entity_id.split(".", 1)
        await hass.services.async_call(
            domain, object_id, {"video_id": video_id}, blocking=False
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_VIDEO,
        _async_handle_play_video,
        schema=vol.Schema({vol.Required("video_id"): str}),
    )
    entry.async_on_unload(lambda: hass.services.async_remove(DOMAIN, SERVICE_PLAY_VIDEO))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: YouTubeConfigEntry) -> None:
    """Reload the entry when its options change (e.g. a different script picked)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: YouTubeConfigEntry) -> bool:
    """Unload a config entry."""
    return True
