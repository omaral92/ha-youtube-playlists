"""Tests for the Android TV playback wake logic."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.youtube_playlists.const import (
    CONF_PLAY_ONLINE_TIMEOUT,
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


def _build(initial_state: str, options: dict, unavailable_polls: int = 0):
    """Build a fake hass whose calls are recorded, in order, in ``events``.

    After the Android TV entry is reloaded the entity reports "unavailable"
    for ``unavailable_polls`` state lookups (the TV's ADB server is still
    starting), then "idle". ``unavailable_polls=None`` means it never returns.
    """
    events: list[tuple] = []
    box = {"reloaded": False, "polls_left": unavailable_polls}

    def _get_state(_entity_id):
        if not box["reloaded"]:
            return SimpleNamespace(state=initial_state)
        if box["polls_left"] is None:
            return SimpleNamespace(state="unavailable")
        if box["polls_left"] > 0:
            box["polls_left"] -= 1
            return SimpleNamespace(state="unavailable")
        return SimpleNamespace(state="idle")

    async def _service(domain, service, data=None, blocking=False):
        events.append(("service", domain, service))

    async def _reload(entry_id):
        box["reloaded"] = True
        events.append(("reload", entry_id))

    async def _sleep(seconds):
        events.append(("sleep", seconds))

    hass = MagicMock()
    hass.states.get.side_effect = _get_state
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


def _sleeps(events):
    return [e[1] for e in events if e[0] == "sleep"]


@pytest.mark.asyncio
async def test_wake_sequence_runs_in_order(monkeypatch) -> None:
    """off -> turn on, wait, reload, (online), settle, volume, ADB launch."""
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
async def test_waits_for_entity_to_come_online_before_launching(monkeypatch) -> None:
    """Regression: the ADB server took ~17s to come up after the reload.

    The launch command used to be sent after a fixed 3s, while the entity was
    still unavailable, and Home Assistant silently dropped it.
    """
    hass, entry, registry, events, sleep = _build("off", {}, unavailable_polls=17)
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    reload_idx = events.index(("reload", "abc123"))
    adb_idx = events.index(("service", "androidtv", "adb_command"))
    polls_between = [
        e for e in events[reload_idx:adb_idx] if e == ("sleep", 1)
    ]
    assert len(polls_between) == 17  # polled until the entity was available
    assert events[adb_idx - 2 : adb_idx] == [  # settle delay comes after it's online
        ("sleep", DEFAULT_PLAY_SETTLE_DELAY_SECONDS),
        ("service", "media_player", "volume_set"),
    ]


@pytest.mark.asyncio
async def test_timeout_raises_and_does_not_send_launch(monkeypatch) -> None:
    """If the TV never comes online, fail loudly and don't fire into the void."""
    hass, entry, registry, events, sleep = _build(
        "off", {CONF_PLAY_ONLINE_TIMEOUT: 10}, unavailable_polls=None
    )
    _patch(monkeypatch, registry, sleep)

    with pytest.raises(HomeAssistantError):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert ("service", "androidtv", "adb_command") not in events
    assert ("service", "media_player", "volume_set") not in events
    assert _sleeps(events).count(1) == 10


@pytest.mark.asyncio
async def test_delays_are_configurable(monkeypatch) -> None:
    """The wake-up and settle delays come from the integration options."""
    options = {CONF_PLAY_WAKE_DELAY: 8, CONF_PLAY_SETTLE_DELAY: 1.5}
    hass, entry, registry, events, sleep = _build("off", options)
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _sleeps(events) == [8.0, 1.5]


@pytest.mark.asyncio
async def test_invalid_delay_falls_back_to_default(monkeypatch) -> None:
    """A garbage/negative option must not break playback."""
    options = {CONF_PLAY_WAKE_DELAY: "abc", CONF_PLAY_SETTLE_DELAY: -4}
    hass, entry, registry, events, sleep = _build("off", options)
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _sleeps(events) == [float(DEFAULT_PLAY_WAKE_DELAY_SECONDS), 0.0]


@pytest.mark.asyncio
async def test_tv_already_on_skips_wake_sequence(monkeypatch) -> None:
    """If the TV is on, go straight to volume + launch (no reload, no waits)."""
    hass, entry, registry, events, sleep = _build("on", {})
    _patch(monkeypatch, registry, sleep)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    hass.config_entries.async_reload.assert_not_awaited()
    assert not _sleeps(events)
    hass.services.async_call.assert_any_call(
        "media_player",
        "volume_set",
        {"entity_id": MEDIA_PLAYER, "volume_level": DEFAULT_PLAY_VOLUME_PERCENT / 100},
        blocking=True,
    )
    assert events[-1] == ("service", "androidtv", "adb_command")
