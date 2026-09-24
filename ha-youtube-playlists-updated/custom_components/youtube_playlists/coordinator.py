"""Data coordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YouTubeApi
from .const import (
    CONF_PLAYLIST_FILTER_MODE,
    CONF_PLAYLIST_PATTERN,
    DEFAULT_PLAYLIST_PATTERN,
    DOMAIN,
    FILTER_MODE_ALL,
    UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class YouTubeCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinate YouTube data."""

    def __init__(self, hass, entry: ConfigEntry, api: YouTubeApi) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
            config_entry=entry,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data."""
        filter_mode = self.config_entry.options.get(
            CONF_PLAYLIST_FILTER_MODE, FILTER_MODE_ALL
        )
        pattern = self.config_entry.options.get(
            CONF_PLAYLIST_PATTERN, DEFAULT_PLAYLIST_PATTERN
        )

        try:
            return await self.api.get_data(filter_mode, pattern)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch YouTube playlists: {err}") from err
