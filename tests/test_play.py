"""Tests for the Android TV playback wake logic."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from custom_components.youtube_playlists.const import (
    CONF_PLAY_ONLINE_TIMEOUT,
    CONF_PLAY_SETTLE_DELAY,
    CONF_PLAY_VOLUME,
    DEFAULT_PLAY_SETTLE_DELAY_SECONDS,
    DEFAULT_PLAY_VOLUME_PERCENT,
)
from custom_components.youtube_playlists.play import async_play_on_media_player

MEDIA_PLAYER = "media_player.mi_tv_stick"
LG_TV = "media_player.tv"
ADB_COMMAND = (
    'am start -a android.intent.action.VIEW '
    '-d "https://www.youtube.com/watch?v=abc123xyz" '
    "&& sleep 2 && input keyevent KEYCODE_ENTER"
)
CONNECT_SECONDS = 1  # how long a forced update (connection attempt) takes
HA_POLL_SECONDS = 14  # after boot, HA's own polling notices the TV this much later


class FakeTV:
    """A media player whose ADB server accepts connections ``boot`` seconds
    after the power-on (None = never).

    Before that it is unavailable. Once booted, a forced update brings it
    online at once; otherwise Home Assistant's own polling does,
    ``HA_POLL_SECONDS`` later. Time is a fake clock advanced by the fakes.
    """

    def __init__(self, initial_state, boot=30.0, power_state="unknown", entry_state=ConfigEntryState.LOADED,
                 tv_boot=0.0, tv_initial="unavailable"):
        self.t = 0.0
        self.initial_state = initial_state
        self.boot = boot
        self.powered_at = None
        self.online = False
        self.power_state = power_state
        self.entry = SimpleNamespace(entry_id="abc123", state=entry_state)
        self.events: list[tuple] = []
        # The LG TV's own entity: reaches "on" ``tv_boot`` seconds after the
        # power-on (None = never), once a forced update reconnects it.
        self.tv_boot = tv_boot
        self.tv_initial = tv_initial
        self.tv_on = False

    @property
    def booted(self):
        return self.powered_at is not None and self.boot is not None and self.t >= self.powered_at + self.boot

    def state(self, entity_id):
        if entity_id == LG_TV:
            if self.powered_at is None:
                return SimpleNamespace(state=self.tv_initial)
            return SimpleNamespace(state="on" if self.tv_on else "unavailable")
        if entity_id != MEDIA_PLAYER:  # the power-on entity
            return None if self.power_state is None else SimpleNamespace(state=self.power_state)
        if self.powered_at is None:
            return SimpleNamespace(state=self.initial_state)
        return SimpleNamespace(state="idle" if self.online else "unavailable")

    async def service(self, domain, service, data=None, blocking=False):
        self.events.append(("service", domain, service))
        if service in ("turn_on", "press") and self.powered_at is None:
            self.powered_at = self.t
        if service == "update_entity":
            self.t += CONNECT_SECONDS
            if data["entity_id"] == LG_TV:
                if self.tv_boot is not None and self.t >= self.powered_at + self.tv_boot:
                    self.tv_on = True
            elif self.booted:
                self.online = True

    async def reload(self, entry_id):
        self.events.append(("reload", entry_id))
        self.t += CONNECT_SECONDS
        if self.booted:
            self.entry.state = ConfigEntryState.LOADED

    async def sleep(self, seconds):
        self.events.append(("sleep", seconds))
        self.t += seconds

    async def wait_for_change(self, changed, timeout):
        """No nudge: only HA's own poll can bring it online meanwhile."""
        if not self.online and self.powered_at is not None and self.boot is not None:
            natural = self.powered_at + self.boot + HA_POLL_SECONDS
            if self.t + timeout >= natural:
                self.t = max(self.t, natural)
                self.online = True
                return
        self.t += timeout


def _build(initial_state, options, **tv_kwargs):
    tv = FakeTV(initial_state, **tv_kwargs)
    hass = MagicMock()
    hass.states.get.side_effect = tv.state
    hass.services.async_call = AsyncMock(side_effect=tv.service)
    hass.config_entries.async_reload = AsyncMock(side_effect=tv.reload)
    hass.config_entries.async_get_entry.side_effect = lambda _id: tv.entry
    return hass, SimpleNamespace(options=options), tv


@pytest.fixture
def patched(monkeypatch):
    """Patch play.py's clock, sleeps, registry and state listener onto a FakeTV."""
    import custom_components.youtube_playlists.play as play

    def _apply(tv):
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(config_entry_id="abc123")
        monkeypatch.setattr(play.er, "async_get", lambda _h: registry)
        monkeypatch.setattr(play.asyncio, "sleep", tv.sleep)
        monkeypatch.setattr(play, "_monotonic", lambda: tv.t)
        monkeypatch.setattr(play, "_async_wait_for_change", tv.wait_for_change)
        monkeypatch.setattr(play, "async_track_state_change_event", lambda *_a: lambda: None)

    return _apply


def _patch_log(monkeypatch):
    """Capture play.py's _LOGGER.info/.error calls as (level, message) tuples."""
    records: list[tuple[str, str]] = []
    import custom_components.youtube_playlists.play as play_module

    for level in ("info", "error"):
        def _make(level=level):
            def _log(msg, *args, **kwargs):
                records.append((level, msg % args if args else msg))
            return _log
        monkeypatch.setattr(play_module._LOGGER, level, _make())
    return records


def _count(events, *event):
    return events.count(event)


@pytest.mark.asyncio
async def test_wake_sequence_runs_in_order(patched) -> None:
    """off -> turn on, connect attempts until online, settle, volume, ADB launch."""
    hass, entry, tv = _build("off", {CONF_PLAY_VOLUME: 20}, boot=0)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert tv.events == [
        ("service", "media_player", "turn_on"),
        ("service", "homeassistant", "update_entity"),
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
async def test_launches_as_soon_as_the_tv_is_up_not_after_a_fixed_wait(patched) -> None:
    """Regression: the Mi TV Stick takes ~30s to accept ADB after power-on.

    Fixed waits + reloads every few seconds kept restarting its connection;
    now we keep asking it to connect and go the moment it can.
    """
    hass, entry, tv = _build("unavailable", {"play_power_on_entity": "button.tv"}, boot=30)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    launch_at = tv.t - DEFAULT_PLAY_SETTLE_DELAY_SECONDS
    assert 30 <= launch_at <= 30 + CONNECT_SECONDS + 2  # within one attempt of booting
    assert ("reload", "abc123") not in tv.events  # a loaded entry is never reloaded
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_state_change_from_ha_polling_is_picked_up_immediately(patched, monkeypatch) -> None:
    """If HA's own poll brings the TV online between our attempts, go at once."""
    import custom_components.youtube_playlists.play as play

    hass, entry, tv = _build("off", {}, boot=0)
    patched(tv)
    # Our connection attempts never get through, but HA's poll does at t=14s.
    async def _no_luck(domain, service, data=None, blocking=False):
        tv.events.append(("service", domain, service))
        if service == "turn_on":
            tv.powered_at = tv.t
        if service == "update_entity":
            tv.t += CONNECT_SECONDS
    hass.services.async_call = AsyncMock(side_effect=_no_luck)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert tv.t - DEFAULT_PLAY_SETTLE_DELAY_SECONDS == pytest.approx(HA_POLL_SECONDS)
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_unloaded_android_tv_entry_is_reloaded_until_it_sets_up(patched) -> None:
    """The Android TV entry failed to set up (TV was off at HA start): reload it."""
    hass, entry, tv = _build("unavailable", {"play_power_on_entity": "button.tv"},
                             boot=6, entry_state=ConfigEntryState.SETUP_RETRY)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _count(tv.events, "reload", "abc123") >= 2  # retried while booting
    assert tv.entry.state is ConfigEntryState.LOADED
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_timeout_raises_and_does_not_send_launch(patched) -> None:
    """If the TV never comes online, fail loudly and don't fire into the void."""
    hass, entry, tv = _build("off", {CONF_PLAY_ONLINE_TIMEOUT: 20}, boot=None)
    patched(tv)

    with pytest.raises(HomeAssistantError):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert ("service", "androidtv", "adb_command") not in tv.events
    assert ("service", "media_player", "volume_set") not in tv.events
    assert 20 <= tv.t <= 21  # gave up at the timeout, counted from power-on


@pytest.mark.asyncio
async def test_settle_delay_is_configurable(patched) -> None:
    hass, entry, tv = _build("off", {CONF_PLAY_SETTLE_DELAY: 1.5}, boot=0)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert [e[1] for e in tv.events if e[0] == "sleep"] == [1.5]


@pytest.mark.asyncio
async def test_invalid_delay_falls_back_safely(patched) -> None:
    """A garbage/negative option must not break playback."""
    hass, entry, tv = _build("off", {CONF_PLAY_SETTLE_DELAY: -4, CONF_PLAY_ONLINE_TIMEOUT: "abc"}, boot=0)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert [e[1] for e in tv.events if e[0] == "sleep"] == [0.0]
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_legacy_wake_options_are_ignored(patched) -> None:
    """Old play_wake_delay / play_reload_interval options no longer add waits."""
    hass, entry, tv = _build("off", {"play_wake_delay": 10, "play_reload_interval": 2}, boot=0)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert [e[1] for e in tv.events if e[0] == "sleep"] == [DEFAULT_PLAY_SETTLE_DELAY_SECONDS]
    assert ("reload", "abc123") not in tv.events


@pytest.mark.asyncio
async def test_tv_already_on_skips_wake_sequence(patched) -> None:
    """If the TV is on, go straight to volume + launch (no reload, no waits)."""
    hass, entry, tv = _build("on", {})
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    hass.config_entries.async_reload.assert_not_awaited()
    assert not [e for e in tv.events if e[0] == "sleep"]
    hass.services.async_call.assert_any_call(
        "media_player",
        "volume_set",
        {"entity_id": MEDIA_PLAYER, "volume_level": DEFAULT_PLAY_VOLUME_PERCENT / 100},
        blocking=True,
    )
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_power_on_button_is_pressed_not_the_media_player(patched) -> None:
    """A configured button entity powers the TV; the media player only gets ADB."""
    options = {"play_power_on_entity": "button.tv_power"}
    hass, entry, tv = _build("unavailable", options)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    calls = hass.services.async_call.await_args_list
    assert calls[0].args == ("button", "press", {"entity_id": "button.tv_power"})
    assert ("service", "media_player", "turn_on") not in tv.events
    assert calls[-1].args[:2] == ("androidtv", "adb_command")
    assert calls[-1].args[2]["entity_id"] == MEDIA_PLAYER


@pytest.mark.asyncio
async def test_unavailable_power_on_button_raises_and_stops(patched) -> None:
    """HA silently skips calls to unavailable entities; we must not."""
    options = {"play_power_on_entity": "button.tv_power"}
    hass, entry, tv = _build(
        "unavailable", options, power_state="unavailable"
    )
    patched(tv)

    with pytest.raises(HomeAssistantError, match="button.tv_power"):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert tv.events == []  # nothing pressed, nothing launched


@pytest.mark.asyncio
async def test_missing_power_on_entity_raises(patched) -> None:
    options = {"play_power_on_entity": "button.tv_power"}
    hass, entry, tv = _build("off", options, power_state=None)
    patched(tv)

    with pytest.raises(HomeAssistantError, match="missing"):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert tv.events == []


@pytest.mark.asyncio
async def test_never_pressed_button_is_fine(patched) -> None:
    """A button that was never pressed reports "unknown" - that is normal."""
    options = {"play_power_on_entity": "button.tv_power"}
    hass, entry, tv = _build("unavailable", options, power_state="unknown")
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert hass.services.async_call.await_args_list[0].args[:2] == ("button", "press")


@pytest.mark.asyncio
async def test_input_button_is_pressed(patched) -> None:
    options = {"play_power_on_entity": "input_button.tv_power"}
    hass, entry, tv = _build("off", options)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert hass.services.async_call.await_args_list[0].args[:2] == ("input_button", "press")


@pytest.mark.asyncio
async def test_switch_power_on_entity_is_turned_on(patched) -> None:
    options = {"play_power_on_entity": "switch.tv_plug"}
    hass, entry, tv = _build("off", options)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert hass.services.async_call.await_args_list[0].args[:2] == ("homeassistant", "turn_on")


@pytest.mark.asyncio
async def test_no_power_entity_and_media_player_unavailable_raises(patched) -> None:
    """Without a power-on entity, an unavailable media player can't be turned on."""
    hass, entry, tv = _build("unavailable", {})
    patched(tv)

    with pytest.raises(HomeAssistantError, match="power-on entity|turning on the TV"):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert tv.events == []


@pytest.mark.asyncio
async def test_failing_button_press_is_raised(patched) -> None:
    """An error from the button press must surface, not be swallowed."""
    options = {"play_power_on_entity": "button.tv_power"}
    hass, entry, tv = _build("off", options)
    hass.services.async_call = AsyncMock(side_effect=HomeAssistantError("device unreachable"))
    patched(tv)

    with pytest.raises(HomeAssistantError, match="device unreachable"):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")


@pytest.mark.asyncio
async def test_timeout_message_reports_last_state_and_attempts(patched, monkeypatch) -> None:
    """The error should say what the entity's state actually was, not just "no"."""
    hass, entry, tv = _build("off", {CONF_PLAY_ONLINE_TIMEOUT: 10}, boot=None)
    patched(tv)
    log = _patch_log(monkeypatch)

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert "last seen state: unavailable" in str(exc_info.value)
    assert "connection attempt(s)" in str(exc_info.value)
    errors = [m for level, m in log if level == "error"]
    assert errors and "unavailable" in errors[0]


@pytest.mark.asyncio
async def test_progress_is_logged_at_info_without_debug_enabled(patched, monkeypatch) -> None:
    """A slow wake-up must be visible at INFO level, not just DEBUG."""
    hass, entry, tv = _build("off", {CONF_PLAY_ONLINE_TIMEOUT: 25}, boot=None)
    patched(tv)
    log = _patch_log(monkeypatch)

    with pytest.raises(HomeAssistantError):
        await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    progress = [m for level, m in log if level == "info" and "Still waiting" in m]
    # 25s timeout, logged every 10s -> at ~10s and ~20s.
    assert len(progress) == 2
    assert "state=unavailable" in progress[0]


@pytest.mark.asyncio
async def test_wait_for_change_returns_on_the_event_not_the_timeout() -> None:
    """The pause between connection attempts ends the moment the state changes."""
    import asyncio
    import time

    from custom_components.youtube_playlists.play import _async_wait_for_change

    changed = asyncio.Event()
    asyncio.get_running_loop().call_later(0.05, changed.set)
    started = time.monotonic()
    await _async_wait_for_change(changed, 5)
    assert time.monotonic() - started < 1

    changed.clear()
    started = time.monotonic()
    await _async_wait_for_change(changed, 0.05)  # no change: returns at the timeout
    assert time.monotonic() - started < 1


def _volume_calls(hass):
    return [c.args[2] for c in hass.services.async_call.await_args_list if c.args[:2] == ("media_player", "volume_set")]


@pytest.mark.asyncio
async def test_volume_is_set_on_the_tv_not_the_stick(patched) -> None:
    """With a volume entity configured, the TV gets the volume, before the launch."""
    options = {"play_power_on_entity": "button.tv", "play_volume_entity": LG_TV, CONF_PLAY_VOLUME: 12}
    hass, entry, tv = _build("unavailable", options, boot=20, tv_boot=25)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _volume_calls(hass) == [{"entity_id": LG_TV, "volume_level": 0.12}]
    volume_idx = tv.events.index(("service", "media_player", "volume_set"))
    assert volume_idx == len(tv.events) - 2  # right before the launch
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_video_still_starts_when_the_tv_entity_never_comes_on(patched, monkeypatch) -> None:
    """The volume step is skipped (with a warning), playback is not."""
    import custom_components.youtube_playlists.play as play

    warnings: list[str] = []
    monkeypatch.setattr(play._LOGGER, "warning", lambda msg, *a: warnings.append(msg % a))
    options = {"play_power_on_entity": "button.tv", "play_volume_entity": LG_TV}
    hass, entry, tv = _build("unavailable", options, boot=20, tv_boot=None)
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _volume_calls(hass) == []
    assert tv.events[-1] == ("service", "androidtv", "adb_command")
    assert any("Not setting the volume" in w and LG_TV in w for w in warnings)


@pytest.mark.asyncio
async def test_tv_already_on_sets_volume_on_the_tv(patched) -> None:
    options = {"play_volume_entity": LG_TV, CONF_PLAY_VOLUME: 40}
    hass, entry, tv = _build("playing", options, tv_initial="on")
    patched(tv)

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _volume_calls(hass) == [{"entity_id": LG_TV, "volume_level": 0.4}]
    assert tv.events[-1] == ("service", "androidtv", "adb_command")


@pytest.mark.asyncio
async def test_stick_in_off_state_still_gets_the_volume_without_a_volume_entity(patched) -> None:
    """Default (no volume entity): the stick takes volume over ADB even when "off"."""
    hass, entry, tv = _build("off", {CONF_PLAY_VOLUME: 20}, boot=0)
    patched(tv)
    tv.online = True  # reachable over ADB, screen off

    await async_play_on_media_player(hass, entry, MEDIA_PLAYER, "abc123xyz")

    assert _volume_calls(hass) == [{"entity_id": MEDIA_PLAYER, "volume_level": 0.2}]
