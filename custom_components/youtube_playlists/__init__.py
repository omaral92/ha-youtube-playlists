"""YouTube Playlists integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow

from .api import YouTubeApi
from .const import DOMAIN
from .coordinator import YouTubeCoordinator
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

type YouTubeConfigEntry = ConfigEntry[YouTubeCoordinator]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration."""
    async_register_websocket(hass)
    return True


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
