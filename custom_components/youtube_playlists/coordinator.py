"""Data coordinator."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import YouTubeApi
from .const import (
    CONF_NOTIFY_SCRIPT,
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
        self._known_video_ids: set[str] | None = None

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data."""
        filter_mode = self.config_entry.options.get(
            CONF_PLAYLIST_FILTER_MODE, FILTER_MODE_ALL
        )
        pattern = self.config_entry.options.get(
            CONF_PLAYLIST_PATTERN, DEFAULT_PLAYLIST_PATTERN
        )

        try:
            data = await self.api.get_data(filter_mode, pattern)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch YouTube playlists: {err}") from err

        await self._notify_new_videos(data)
        return data

    async def _notify_new_videos(self, data: list[dict[str, Any]]) -> None:
        """Run the configured script if new videos showed up since the last refresh."""
        current_ids = {
            video["id"] for playlist in data for video in playlist.get("videos", [])
        }

        if self._known_video_ids is None:
            # First refresh: just establish the baseline, don't fire for existing videos.
            self._known_video_ids = current_ids
            return

        new_ids = current_ids - self._known_video_ids
        self._known_video_ids = current_ids

        if not new_ids:
            return

        script_entity_id = self.config_entry.options.get(CONF_NOTIFY_SCRIPT)
        if not script_entity_id:
            return

        new_videos = [
            {"playlist_id": playlist["id"], "playlist_title": playlist["title"], **video}
            for playlist in data
            for video in playlist.get("videos", [])
            if video["id"] in new_ids
        ]

        domain, object_id = script_entity_id.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain,
                object_id,
                {"variables": {"new_videos": new_videos}},
                blocking=False,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to run script %s: %s", script_entity_id, err)
