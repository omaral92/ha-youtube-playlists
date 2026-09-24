"""Logic for playing a YouTube video on an Android TV media_player target."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_PLAY_ONLINE_TIMEOUT,
    CONF_PLAY_POWER_ON_ENTITY,
    CONF_PLAY_SETTLE_DELAY,
    CONF_PLAY_VOLUME,
    CONF_PLAY_WAKE_DELAY,
    DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS,
    DEFAULT_PLAY_SETTLE_DELAY_SECONDS,
    DEFAULT_PLAY_VOLUME_PERCENT,
    DEFAULT_PLAY_WAKE_DELAY_SECONDS,
    OFF_STATES,
    PLAY_ONLINE_POLL_INTERVAL_SECONDS,
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
    """Wake the TV if needed, bring ADB online, then launch the video.

    Sequence when the TV is off:
      1. Turn on the TV
      2. Wait ``play_wake_delay`` seconds (default 5)
      3. Reload the Android TV / ADB config entry so the device comes online,
         then wait until the media player entity is actually available again
         (up to ``play_online_timeout`` seconds, default 60)
      4. Wait ``play_settle_delay`` seconds (default 3)
      5. Send the ADB YouTube launch command
    """
    state = hass.states.get(entity_id)
    is_off = state is None or state.state in OFF_STATES

    if is_off:
        wake_delay = _delay_option(
            entry, CONF_PLAY_WAKE_DELAY, DEFAULT_PLAY_WAKE_DELAY_SECONDS
        )
        settle_delay = _delay_option(
            entry, CONF_PLAY_SETTLE_DELAY, DEFAULT_PLAY_SETTLE_DELAY_SECONDS
        )
        online_timeout = _delay_option(
            entry, CONF_PLAY_ONLINE_TIMEOUT, DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS
        )
        _LOGGER.debug("%s is off, turning on before playback", entity_id)

        # 1. Turn on the TV.
        await _async_turn_on_tv(hass, entry, entity_id)
        # 2. Give it time to boot. The entity usually cannot report online yet,
        #    so we wait a fixed period rather than polling its state.
        await asyncio.sleep(wake_delay)
        # 3. Reload the Android TV / ADB entry to make the device come online.
        await _async_reload_androidtv_entry(hass, entity_id)
        #    The TV's ADB server can take 20s+ to start after power-on. Until
        #    the entity is available, HA silently drops service calls to it,
        #    so wait for it here instead of firing commands into the void.
        await _async_wait_until_available(hass, entity_id, online_timeout)
        # 4. Brief settle period once the device is online.
        await asyncio.sleep(settle_delay)
    else:
        _LOGGER.debug("%s is already on, skipping power-on", entity_id)

    volume_percent = entry.options.get(CONF_PLAY_VOLUME, DEFAULT_PLAY_VOLUME_PERCENT)
    if volume_percent is not None:
        try:
            await hass.services.async_call(
                "media_player",
                "volume_set",
                {"entity_id": entity_id, "volume_level": volume_percent / 100},
                blocking=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Could not set volume on %s: %s", entity_id, err)

    # 5. Send the ADB YouTube launch command.
    await hass.services.async_call(
        "androidtv",
        "adb_command",
        {"entity_id": entity_id, "command": _youtube_intent_command(video_id)},
        blocking=True,
    )


async def _async_turn_on_tv(
    hass: HomeAssistant, entry: ConfigEntry, media_player_entity: str
) -> None:
    """Turn on the TV through the configured power entity when available."""
    power_on_entity = entry.options.get(CONF_PLAY_POWER_ON_ENTITY)
    if power_on_entity:
        await _async_power_on_entity(hass, power_on_entity)
        return

    await hass.services.async_call(
        "media_player",
        "turn_on",
        {"entity_id": media_player_entity},
        blocking=True,
    )


async def _async_power_on_entity(hass: HomeAssistant, entity_id: str) -> None:
    """Power on a helper entity before playback."""
    domain = entity_id.split(".", 1)[0]
    if domain == "button":
        service_domain = "button"
        service = "press"
    else:
        service_domain = "homeassistant"
        service = "turn_on"

    await hass.services.async_call(
        service_domain,
        service,
        {"entity_id": entity_id},
        blocking=True,
    )


async def _async_reload_androidtv_entry(hass: HomeAssistant, entity_id: str) -> None:
    """Reload the underlying Android TV config entry so ADB becomes available again."""
    entity_registry = er.async_get(hass)
    registry_entry = entity_registry.async_get(entity_id)
    if registry_entry is None or not registry_entry.config_entry_id:
        _LOGGER.debug("No Android TV config entry found for %s; skipping reload", entity_id)
        return

    try:
        await hass.config_entries.async_reload(registry_entry.config_entry_id)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning(
            "Could not reload Android TV config entry %s for %s: %s",
            registry_entry.config_entry_id,
            entity_id,
            err,
        )
        return

    _LOGGER.debug(
        "Reloaded Android TV config entry %s for %s after power-on",
        registry_entry.config_entry_id,
        entity_id,
    )


async def _async_wait_until_available(
    hass: HomeAssistant, entity_id: str, timeout: float
) -> None:
    """Wait for the entity to exist and be available, or raise on timeout.

    Home Assistant does not raise when a service call targets an unavailable
    entity - it logs "Referenced entities ... are missing or not currently
    available" and skips the call. Raising here makes that failure visible
    instead of the launch command being silently dropped.
    """
    elapsed = 0.0
    while True:
        state = hass.states.get(entity_id)
        if state is not None and state.state not in UNAVAILABLE_STATES:
            _LOGGER.debug("%s is available after ~%ss", entity_id, elapsed)
            return
        if elapsed >= timeout:
            break
        await asyncio.sleep(PLAY_ONLINE_POLL_INTERVAL_SECONDS)
        elapsed += PLAY_ONLINE_POLL_INTERVAL_SECONDS

    message = (
        f"{entity_id} did not become available within {timeout:g}s after being "
        "turned on, so the YouTube launch command was not sent. Check that ADB "
        "debugging is enabled on the TV, or increase the online timeout."
    )
    _LOGGER.error(message)
    raise HomeAssistantError(message)
