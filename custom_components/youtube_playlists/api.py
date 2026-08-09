"""YouTube Data API client."""
from __future__ import annotations

import fnmatch
from typing import Any

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import FILTER_MODE_ALL

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeApi:
    """Small async client for the YouTube Data API v3."""

    def __init__(self, hass, oauth: OAuth2Session) -> None:
        self.hass = hass
        self.oauth = oauth

    async def _get(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        response = await self.oauth.async_request(
            "GET",
            f"{BASE_URL}/{resource}",
            params=params,
        )
        response.raise_for_status()
        return await response.json()

    async def get_playlists(
        self, filter_mode: str = FILTER_MODE_ALL, pattern: str = ""
    ) -> list[dict[str, Any]]:
        """Return playlists, optionally filtered by a glob-style title pattern.

        filter_mode "all" returns every playlist owned by the account.
        filter_mode "pattern" returns only playlists whose title matches
        `pattern` (case-insensitive, glob syntax e.g. "HA*", "*Podcast*").
        """
        playlists: list[dict[str, Any]] = []
        page_token: str | None = None
        pattern_lower = pattern.lower().strip()

        while True:
            params: dict[str, Any] = {
                "part": "snippet,contentDetails",
                "mine": "true",
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token

            data = await self._get("playlists", params)

            for item in data.get("items", []):
                title = item["snippet"]["title"]

                if filter_mode != FILTER_MODE_ALL and pattern_lower:
                    if not fnmatch.fnmatch(title.lower(), pattern_lower):
                        continue

                playlists.append(
                    {
                        "id": item["id"],
                        "title": title,
                        "description": item["snippet"].get("description", ""),
                        "thumbnail": (
                            item["snippet"].get("thumbnails", {}).get("medium", {}).get("url")
                            or item["snippet"].get("thumbnails", {}).get("default", {}).get("url")
                        ),
                        "item_count": item.get("contentDetails", {}).get("itemCount", 0),
                    }
                )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return playlists

    async def get_playlist_videos(self, playlist_id: str) -> list[dict[str, Any]]:
        """Return videos in a playlist."""
        videos: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            params: dict[str, Any] = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token

            data = await self._get("playlistItems", params)

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                resource = snippet.get("resourceId", {})
                video_id = resource.get("videoId")
                if not video_id:
                    continue

                videos.append(
                    {
                        "id": video_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "position": snippet.get("position", 0),
                        "thumbnail": (
                            snippet.get("thumbnails", {}).get("high", {}).get("url")
                            or snippet.get("thumbnails", {}).get("medium", {}).get("url")
                            or snippet.get("thumbnails", {}).get("default", {}).get("url")
                        ),
                        "published_at": snippet.get("publishedAt"),
                    }
                )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return videos

    async def get_data(
        self, filter_mode: str = FILTER_MODE_ALL, pattern: str = ""
    ) -> list[dict[str, Any]]:
        """Return playlists and their videos."""
        playlists = await self.get_playlists(filter_mode, pattern)
        result = []
        for playlist in playlists:
            videos = await self.get_playlist_videos(playlist["id"])
            playlist["videos"] = videos
            playlist["item_count"] = len(videos)
            result.append(playlist)
        return result
