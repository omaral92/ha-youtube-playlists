"""Logic for playing a YouTube video on an Android TV media_player target."""
from __future__ import annotations

import asyncio
import time
import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_PLAY_ONLINE_TIMEOUT,
    CONF_PLAY_POWER_ON_ENTITY,
    CONF_PLAY_SETTLE_DELAY,
    CONF_PLAY_VOLUME,
    CONF_PLAY_VOLUME_ENTITY,
    DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS,
    DEFAULT_PLAY_SETTLE_DELAY_SECONDS,
    DEFAULT_PLAY_VOLUME_PERCENT,
    OFF_STATES,
    PLAY_ONLINE_NUDGE_INTERVAL_SECONDS,
    PLAY_ONLINE_PROGRESS_LOG_INTERVAL_SECONDS,
    PLAY_VOLUME_ENTITY_GRACE_SECONDS,
    UNAVAILABLE_STATES,
)

_LOGGER = logging.getLogger(__name__)


def _delay_option(entry: ConfigEntry, key: str, default: float) -> float:
    """Read a delay (seconds) from the entry options, falling back safely."""
    try:
        return max(0.0, float(entry.options.get(key, default)))
    except (TypeError, ValueError):
        return float(default)


def _youtube_intent_command(video_id: str) -> str:
    """Build the ADB shell command that opens a specific YouTube video."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    # Some Android TV YouTube builds show a profile/account picker on first launch.
    # Confirming the default selection immediately after launch dismisses that screen
    # and allows the video to open normally.
    return (
        f'am start -a android.intent.action.VIEW -d "{url}" '
        "&& sleep 2 && input keyevent KEYCODE_ENTER"
    )


async def async_play_on_media_player(
    hass: HomeAssistant, entry: ConfigEntry, entity_id: str, video_id: str
) -> None:
    """Wake the TV if needed, wait for ADB to come online, then launch the video.

    Sequence when the TV is off:
      1. Turn on the TV
      2. Wait for the media player to come online (see
         ``_async_wait_until_available``), up to ``play_online_timeout``
         seconds after the power-on (default 90). There is no fixed wait: the
         entity is asked to reconnect over and over, and we carry on the
         moment its state changes to something available.
      3. Wait ``play_settle_delay`` seconds (default 3)
      4. Set the volume and send the ADB YouTube launch command

    The volume is set on ``play_volume_entity`` when configured (for example
    the TV itself, when the Android TV device is a stick plugged into it),
    otherwise on the playback media player. A separate volume entity is
    waited for alongside the playback device; if it is still not on a little
    after the device is ready (``PLAY_VOLUME_ENTITY_GRACE_SECONDS``), the
    video starts without the volume step rather than not at all.
    """
    state = hass.states.get(entity_id)
    is_off = state is None or state.state in OFF_STATES
    volume_percent = entry.options.get(CONF_PLAY_VOLUME, DEFAULT_PLAY_VOLUME_PERCENT)
    volume_entity = entry.options.get(CONF_PLAY_VOLUME_ENTITY) or entity_id
    volume_wait: asyncio.Task[bool] | None = None

    if is_off:
        settle_delay = _delay_option(
            entry, CONF_PLAY_SETTLE_DELAY, DEFAULT_PLAY_SETTLE_DELAY_SECONDS
        )
        online_timeout = _delay_option(
            entry, CONF_PLAY_ONLINE_TIMEOUT, DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS
        )
        _LOGGER.debug(
            "%s is %s, powering on the TV before playback",
            entity_id,
            state.state if state else "missing",
        )

        # 1. Turn on the TV.
        started = _monotonic()
        await _async_turn_on_tv(hass, entry, entity_id)
        _LOGGER.info(
            "Power-on triggered; waiting up to %gs for %s to come online",
            online_timeout,
            entity_id,
        )
        remaining = online_timeout - (_monotonic() - started)
        if volume_percent is not None and volume_entity != entity_id:
            # The TV's own entity (e.g. webOS) comes online on its own
            # schedule; wait for it in parallel. It must be on, not just
            # reachable, to take a volume change.
            volume_wait = asyncio.create_task(
                _async_wait_until_available(
                    hass, volume_entity, remaining, not_ready=OFF_STATES, required=False
                )
            )
        # 2. Until the entity is available, HA silently drops service calls to
        #    it, so wait for it here instead of firing commands into the void.
        try:
            await _async_wait_until_available(hass, entity_id, remaining)
        except BaseException:
            if volume_wait is not None:
                volume_wait.cancel()
            raise
        _LOGGER.info(
            "%s is online %.1fs after power-on; settling %ss before the launch command",
            entity_id,
            _monotonic() - started,
            settle_delay,
        )
        # 3. Brief settle period once the device is online.
        await asyncio.sleep(settle_delay)
    else:
        _LOGGER.debug(
            "%s is %s (not off), skipping power-on", entity_id, state.state
        )

    if volume_wait is not None:
        try:
            async with asyncio.timeout(PLAY_VOLUME_ENTITY_GRACE_SECONDS):
                await asyncio.shield(volume_wait)
        except TimeoutError:
            volume_wait.cancel()

    if volume_percent is not None:
        await _async_set_volume(
            hass,
            volume_entity,
            volume_percent,
            # The playback device takes volume over ADB even with its screen
            # "off"; a separate TV entity has to actually be on.
            UNAVAILABLE_STATES if volume_entity == entity_id else OFF_STATES,
        )

    # 4. Send the ADB YouTube launch command.
    _LOGGER.info("Sending ADB launch command to %s", entity_id)
    await hass.services.async_call(
        "androidtv",
        "adb_command",
        {"entity_id": entity_id, "command": _youtube_intent_command(video_id)},
        blocking=True,
    )
    _LOGGER.info("ADB launch command sent to %s", entity_id)


async def _async_set_volume(
    hass: HomeAssistant, entity_id: str, percent: float, not_ready: tuple[str, ...]
) -> None:
    """Set the volume, warning (not failing) when it can't be done.

    Home Assistant silently skips service calls to unavailable entities, so
    check first to make a skipped volume change visible in the log.
    """
    state = hass.states.get(entity_id)
    if state is None or state.state in not_ready:
        _LOGGER.warning(
            "Not setting the volume: %s is %s, so it can't take a volume change; "
            "starting the video without it",
            entity_id,
            "missing" if state is None else state.state,
        )
        return
    try:
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": entity_id, "volume_level": percent / 100},
            blocking=True,
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not set volume on %s: %s", entity_id, err)
        return
    _LOGGER.info("Volume on %s set to %g%%", entity_id, percent)


async def _async_turn_on_tv(
    hass: HomeAssistant, entry: ConfigEntry, media_player_entity: str
) -> None:
    """Turn on the TV.

    If a power-on entity is configured (typically a button that powers the TV
    on when pressed) that entity is used. The media player is only the ADB
    target: when the TV is off it is usually unavailable and cannot be told
    to turn on.
    """
    power_on_entity = entry.options.get(CONF_PLAY_POWER_ON_ENTITY)
    if power_on_entity:
        await _async_power_on_entity(hass, power_on_entity)
        return

    # No power-on entity: fall back to the media player itself. This can only
    # work while the media player is available.
    state = hass.states.get(media_player_entity)
    if state is None or state.state in UNAVAILABLE_STATES:
        message = (
            "The TV is off and no 'Entity to use for turning on the TV' is "
            f"configured, and {media_player_entity} is unavailable, so it "
            "cannot be turned on. Set a power-on entity (for example a "
            "button) in the YouTube Playlists options."
        )
        _LOGGER.error(message)
        raise HomeAssistantError(message)

    _LOGGER.debug("Turning on %s via media_player.turn_on", media_player_entity)
    await hass.services.async_call(
        "media_player",
        "turn_on",
        {"entity_id": media_player_entity},
        blocking=True,
    )


async def _async_power_on_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Power on the TV through the configured power-on entity.

    Buttons are pressed; other entities are turned on. Home Assistant silently
    skips service calls to missing/unavailable entities, so check first and
    fail loudly instead of leaving the TV off with no explanation.
    (A button that has never been pressed reports "unknown", which is normal.)
    """
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        message = (
            f"The power-on entity {entity_id} is "
            f"{'missing' if state is None else 'unavailable'}, so the TV was "
            "not turned on and the YouTube launch command was not sent."
        )
        _LOGGER.error(message)
        raise HomeAssistantError(message)

    domain = entity_id.split(".", 1)[0]
    if domain in ("button", "input_button"):
        service_domain, service = domain, "press"
    else:
        service_domain, service = "homeassistant", "turn_on"

    _LOGGER.debug("Powering on TV: calling %s.%s on %s", service_domain, service, entity_id)
    state_before = state.state
    try:
        await hass.services.async_call(
            service_domain,
            service,
            {"entity_id": entity_id},
            blocking=True,
        )
    except Exception:
        _LOGGER.exception(
            "Powering on the TV failed: %s.%s on %s raised an error",
            service_domain,
            service,
            entity_id,
        )
        raise

    # A pressed button's state becomes the time of the press, so a change here
    # proves Home Assistant registered the press.
    state_after = hass.states.get(entity_id)
    after = state_after.state if state_after else "missing"
    _LOGGER.info(
        "%s.%s on %s completed (entity state: %s -> %s)",
        service_domain,
        service,
        entity_id,
        state_before,
        after,
    )
    if domain in ("button", "input_button") and after == state_before:
        _LOGGER.warning(
            "%s state did not change after the press; Home Assistant may not "
            "have registered it",
            entity_id,
        )


def _androidtv_entry(hass: HomeAssistant, entity_id: str) -> ConfigEntry | None:
    """The config entry (Android TV integration) behind the media player."""
    registry_entry = er.async_get(hass).async_get(entity_id)
    if registry_entry is None or not registry_entry.config_entry_id:
        return None
    return hass.config_entries.async_get_entry(registry_entry.config_entry_id)


def _monotonic() -> float:
    """Monotonic clock (a function so tests can fake it)."""
    return time.monotonic()


async def _async_wait_for_change(changed: asyncio.Event, timeout: float) -> None:
    """Wait until ``changed`` is set or ``timeout`` seconds pass."""
    try:
        async with asyncio.timeout(timeout):
            await changed.wait()
    except TimeoutError:
        pass


async def _async_nudge(hass: HomeAssistant, entity_id: str, timeout: float) -> bool:
    """Ask the Android TV integration to try connecting right now.

    Normally the entity exists and only its ADB connection is down: the
    Android TV media player reconnects inside its own update, so forcing an
    update (``homeassistant.update_entity``) is an immediate connection
    attempt that leaves the integration alone. Its own polling only does this
    every 10s or so, and right after a reload the entity sits at "unknown"
    until that first poll, so this also skips that wait.

    Only when the Android TV entry itself is not loaded (for example it failed
    to set up because the TV was off when Home Assistant started) is there no
    entity to update, and the entry is reloaded instead. Reloading a loaded
    entry would throw away a connection that is about to come up.

    Returns True if it reloaded the entry.
    """
    entry = _androidtv_entry(hass, entity_id)
    if entry is not None and entry.state is not ConfigEntryState.LOADED:
        _LOGGER.debug(
            "Android TV entry %s is %s; reloading it", entry.entry_id, entry.state
        )
        try:
            await hass.config_entries.async_reload(entry.entry_id)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Reloading Android TV entry %s failed: %s", entry.entry_id, err)
        return True
    if hass.states.get(entity_id) is None:
        return False  # nothing to update (yet)
    try:
        async with asyncio.timeout(max(timeout, 0.1)):
            await hass.services.async_call(
                "homeassistant",
                "update_entity",
                {"entity_id": entity_id},
                blocking=True,
            )
    except TimeoutError:
        pass
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Forcing an update of %s failed: %s", entity_id, err)
    return False


async def _async_wait_until_available(
    hass: HomeAssistant,
    entity_id: str,
    timeout: float,
    not_ready: tuple[str, ...] = UNAVAILABLE_STATES,
    required: bool = True,
) -> bool:
    """Wait for the entity to exist and leave the ``not_ready`` states.

    Returns True once it has. On timeout, raises if ``required``, otherwise
    logs a warning and returns False.

    How long a TV takes to boot varies, so instead of fixed delays this
    nudges the entity to reconnect (see ``_async_nudge``) and, between
    nudges, listens for its state changes, returning as soon as it is
    available - whether our nudge or Home Assistant's own polling got it
    there.

    Home Assistant does not raise when a service call targets an unavailable
    entity - it logs "Referenced entities ... are missing or not currently
    available" and skips the call. Raising here makes that failure visible
    instead of the launch command being silently dropped.
    """
    started = _monotonic()
    deadline = started + timeout
    last_progress_log = started
    nudges = reloads = 0
    last_seen_state = "missing"

    changed = asyncio.Event()

    @callback
    def _on_change(_event) -> None:
        changed.set()

    unsub = async_track_state_change_event(hass, [entity_id], _on_change)
    try:
        while True:
            state = hass.states.get(entity_id)
            last_seen_state = state.state if state is not None else "missing"
            if state is not None and state.state not in not_ready:
                _LOGGER.debug(
                    "%s is available after %.1fs (%d nudge(s), %d reload(s)); state=%s",
                    entity_id,
                    _monotonic() - started,
                    nudges,
                    reloads,
                    last_seen_state,
                )
                return True
            now = _monotonic()
            if now >= deadline:
                break
            if now - last_progress_log >= PLAY_ONLINE_PROGRESS_LOG_INTERVAL_SECONDS:
                # INFO, not DEBUG: makes a slow or failed wake-up visible
                # without needing debug logging enabled ahead of time.
                _LOGGER.info(
                    "Still waiting for %s to come online (%.0fs elapsed, "
                    "state=%s, %d connection attempt(s), %d reload(s))",
                    entity_id,
                    now - started,
                    last_seen_state,
                    nudges,
                    reloads,
                )
                last_progress_log = now

            changed.clear()
            if await _async_nudge(hass, entity_id, deadline - now):
                reloads += 1
            else:
                nudges += 1
            if changed.is_set():
                continue  # the nudge itself changed the state: check it now
            # Pause briefly before the next attempt, but wake up the moment
            # the state changes.
            await _async_wait_for_change(
                changed,
                max(0.0, min(PLAY_ONLINE_NUDGE_INTERVAL_SECONDS, deadline - _monotonic())),
            )
    finally:
        unsub()

    if not required:
        _LOGGER.warning(
            "%s did not come on within %.0fs (last seen state: %s)",
            entity_id,
            timeout,
            last_seen_state,
        )
        return False
    message = (
        f"{entity_id} did not come online within {timeout:.0f}s of the TV being "
        f"turned on (last seen state: {last_seen_state}, {nudges} connection "
        f"attempt(s), {reloads} reload(s)), so the YouTube launch command was not "
        "sent. If the TV normally takes longer than this to boot, increase the "
        "online timeout; otherwise check that ADB debugging is enabled on the TV."
    )
    _LOGGER.error(message)
    raise HomeAssistantError(message)
