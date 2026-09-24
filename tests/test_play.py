"""Tests for the Android TV playback wake logic."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.youtube_playlists.const import (
    CONF_PLAY_VOLUME,
    DEFAULT_PLAY_VOLUME_PERCENT,
)
from custom_components.youtube_playlists.play import async_play_on_media_player


@pytest.mark.asyncio
async def test_async_play_on_media_player_reloads_androidtv_entry_after_wake() -> None:
    """Playback should reload the Android TV config entry after the TV comes on."""
    entry = SimpleNamespace(options={CONF_PLAY_VOLUME: 20})
    media_player_entity = "media_player.mi_tv_stick"

    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state="off")
    hass.services.async_call = AsyncMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_entries.return_value = []

    entity_registry = MagicMock()
    entity_registry.async_get.return_value = SimpleNamespace(config_entry_id="abc123")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "custom_components.youtube_playlists.play.er.async_get",
            lambda _hass: entity_registry,
        )

        await async_play_on_media_player(hass, entry, media_player_entity, "abc123xyz")

    assert hass.config_entries.async_reload.await_count == 1
    hass.config_entries.async_reload.assert_awaited_once_with("abc123")

    hass.services.async_call.assert_any_call(
        "androidtv",
        "adb_command",
        {"entity_id": media_player_entity, "command": "am start -a android.intent.action.VIEW -d \"https://www.youtube.com/watch?v=abc123xyz\" && sleep 2 && input keyevent KEYCODE_ENTER"},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_async_play_on_media_player_uses_default_volume_when_not_configured() -> None:
    """Default playback volume should still be applied when no option is set."""
    entry = SimpleNamespace(options={})
    media_player_entity = "media_player.mi_tv_stick"

    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state="on")
    hass.services.async_call = AsyncMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_entries.return_value = []

    entity_registry = MagicMock()
    entity_registry.async_get.return_value = SimpleNamespace(config_entry_id="abc123")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "custom_components.youtube_playlists.play.er.async_get",
            lambda _hass: entity_registry,
        )

        await async_play_on_media_player(hass, entry, media_player_entity, "abc123xyz")

    hass.services.async_call.assert_any_call(
        "media_player",
        "volume_set",
        {"entity_id": media_player_entity, "volume_level": DEFAULT_PLAY_VOLUME_PERCENT / 100},
        blocking=True,
    )
