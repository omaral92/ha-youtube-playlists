"""YouTube Playlists integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from typing import Any

from aiohttp import ClientResponseError

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.loader import async_get_integration

from .api import YouTubeApi
from .const import CARD_FILENAME, CARD_URL_PATH, DOMAIN
from .coordinator import YouTubeCoordinator
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

type YouTubeConfigEntry = ConfigEntry[YouTubeCoordinator]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    async_register_websocket(hass)
    await _async_register_frontend_card(hass)
    return True


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and add it as a frontend resource.

    This means users never need to manually add a Lovelace resource -
    installing (or updating) the integration is enough.
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
    add_extra_js_url(hass, card_url)


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
    return True


async def _async_update_listener(hass: HomeAssistant, entry: YouTubeConfigEntry) -> None:
    """Reload the entry when its options change (e.g. a different script picked)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: YouTubeConfigEntry) -> bool:
    """Unload a config entry."""
    return True
