"""Logic for playing a YouTube video on an Android TV media_player target."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PLAY_VOLUME,
    CONF_PLAY_POWER_ON_ENTITY,
    DEFAULT_PLAY_VOLUME_PERCENT,
    OFF_STATES,
    TV_ON_POLL_INTERVAL_SECONDS,
    TV_ON_SETTLE_DELAY_SECONDS,
    TV_ON_TIMEOUT_SECONDS,
    YOUTUBE_PROFILE_PICKER_DELAY_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _youtube_intent_command(video_id: str) -> str:
    """Build the ADB shell command that opens a specific YouTube video."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    # Some Android TV YouTube builds show a profile/account picker on first launch.
    # Confirming the default selection immediately after launch dismisses that screen
    # and allows the video to open normally.
    return (
        f'am start -a android.intent.action.VIEW -d "{url}" '
        f"&& sleep {YOUTUBE_PROFILE_PICKER_DELAY_SECONDS} "
        "&& input keyevent KEYCODE_ENTER"
    )


async def async_play_on_media_player(
    hass: HomeAssistant, entry: ConfigEntry, entity_id: str, video_id: str
) -> None:
    """Turn on the TV if needed, wait for it, set volume, then launch the video."""
    state = hass.states.get(entity_id)
    is_off = state is None or state.state in OFF_STATES

    if is_off:
        _LOGGER.debug("%s is off, turning on before playback", entity_id)
        power_on_entity = entry.options.get(CONF_PLAY_POWER_ON_ENTITY)
        if power_on_entity:
            await _async_power_on_entity(hass, power_on_entity)
        else:
            await hass.services.async_call(
                "media_player",
                "turn_on",
                {"entity_id": entity_id},
                blocking=True,
            )
        await _async_wait_until_on(hass, entity_id)
        # ADB often isn't immediately responsive the instant the TV reports "on".
        await asyncio.sleep(TV_ON_SETTLE_DELAY_SECONDS)
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

    await hass.services.async_call(
        "androidtv",
        "adb_command",
        {"entity_id": entity_id, "command": _youtube_intent_command(video_id)},
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


async def _async_wait_until_on(hass: HomeAssistant, entity_id: str) -> None:
    """Poll the entity's state until it's no longer off, or time out."""
    elapsed = 0
    while elapsed < TV_ON_TIMEOUT_SECONDS:
        await asyncio.sleep(TV_ON_POLL_INTERVAL_SECONDS)
        elapsed += TV_ON_POLL_INTERVAL_SECONDS
        state = hass.states.get(entity_id)
        if state and state.state not in OFF_STATES:
            return

    _LOGGER.warning(
        "Timed out after %ss waiting for %s to turn on; trying playback anyway",
        TV_ON_TIMEOUT_SECONDS,
        entity_id,
    )
