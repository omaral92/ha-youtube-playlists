"""Data coordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YouTubeApi
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES

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
        try:
            return await self.api.get_data()
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch YouTube playlists: {err}") from err