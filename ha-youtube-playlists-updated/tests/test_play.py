"""Tests for the Android TV playback wake logic."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.youtube_playlists.const import (
    CONF_PLAY_SETTLE_DELAY,
    CONF_PLAY_VOLUME,
    CONF_PLAY_WAKE_DELAY,
    DEFAULT_PLAY_SETTLE_DELAY_SECONDS,
    DEFAULT_PLAY_VOLUME_PERCENT,
    DEFAULT_PLAY_WAKE_DELAY_SECONDS,
)
from custom_components.youtube_playlists.play import async_play_on_media_player

MEDIA_PLAYER = "media_player.mi_tv_stick"
ADB_COMMAND = (
    'am start -a android.intent.action.VIEW '
    '-d "https://www.youtube.com/watch?v=abc123xyz" '
    "&& sleep 2 && input keyevent KEYCODE_ENTER"
)


def _build(state: str, options: dict):
    """Build a fake hass whose calls are recorded, in order, in ``events``."""
    events: list[tuple] = []

    async def _service(domain, service, data=None, blocking=False):
        events.append(("service", domain, service))

    async def _reload(entry_id):
        events.append(("reload", entry_id))

    async def _sleep(seconds):
        events.append(("sleep", seconds))

    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state=state)
    hass.services.async_call = AsyncMock(side_effect=_service)
    hass.config_entries.async_reload = AsyncMock(side_effect=_reload)

    registry = MagicMock()
    registry.async_get.return_value = SimpleNamespace(config_entry_id="abc123")

    return hass, SimpleNamespace(options=options), registry, events, _sleep


def _patch(monkeypatch, registry, sleep):
    monkeypatch.setattr(
        "custom_components.youtube_playlists.play.er.async_get", lambda _h: registry
    )
    monkeypatch.setattr("custom_components.youtube_playlists.play.asyncio.sleep", sleep)


@pytest.mark.asyncio
async def test_wake_sequence_runs_in_order(monkeypatch) -> None:
    """off -> turn on, wait, reload, settle, (volume), ADB launch."""
    hass, entry, registry, events, sleep = _build("off", {CONF_PLAY_VOLUME: 20})
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert events == [
        ("service", "media_player", "turn_on"),
        ("sleep", DEFAULT_PLAY_WAKE_DELAY_SECONDS),
        ("reload", "abc123"),
        ("sleep", DEFAULT_PLAY_SETTLE_DELAY_SECONDS),
        ("service", "media_player", "volume_set"),
        ("service", "androidtv", "adb_command"),
    ]
    hass.services.async_call.assert_any_call(
        "androidtv",
        "adb_command",
        {"entity_id": MEDIA_PLAYER, "command": ADB_COMMAND},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_delays_are_configurable(monkeypatch) -> None:
    """The wake-up and settle delays come from the integration options."""
    options = {CONF_PLAY_WAKE_DELAY: 8, CONF_PLAY_SETTLE_DELAY: 1.5}
    hass, entry, registry, events, sleep = _build("off", options)
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert [e for e in events if e[0] == "sleep"] == [("sleep", 8.0), ("sleep", 1.5)]


@pytest.mark.asyncio
async def test_invalid_delay_falls_back_to_default(monkeypatch) -> None:
    """A garbage/negative option must not break playback."""
    options = {CONF_PLAY_WAKE_DELAY: "abc", CONF_PLAY_SETTLE_DELAY: -4}
    hass, entry, registry, events, sleep = _build("off", options)
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert [e for e in events if e[0] == "sleep"] == [
        ("sleep", float(DEFAULT_PLAY_WAKE_DELAY_SECONDS)),
        ("sleep", 0.0),
    ]


@pytest.mark.asyncio
async def test_tv_already_on_skips_wake_sequence(monkeypatch) -> None:
    """If the TV is on, go straight to volume + launch (no reload, no waits)."""
    hass, entry, registry, events, sleep = _build("on", {})
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    hass.config_entries.async_reload.assert_not_awaited()
    assert not [e for e in events if e[0] == "sleep"]
    hass.services.async_call.assert_any_call(
        "media_player",
        "volume_set",
        {"entity_id": MEDIA_PLAYER, "volume_level": DEFAULT_PLAY_VOLUME_PERCENT / 100},
        blocking=True,
    )
    assert events[-1] == ("service", "androidtv", "adb_command")
