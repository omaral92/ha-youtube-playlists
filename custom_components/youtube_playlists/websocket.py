"""WebSocket API for the frontend card."""
from __future__ import annotations

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from .const import (
    CONF_PLAY_MEDIA_PLAYER,
    CONF_PLAY_TARGET_MODE,
    CONF_PLAY_TV,
    DOMAIN,
    PLAY_TARGET_MEDIA_PLAYER,
    WS_TYPE,
)


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register websocket commands."""
    websocket_api.async_register_command(hass, websocket_get_data)


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE,
    }
)
@callback
def websocket_get_data(hass: HomeAssistant, connection, msg) -> None:
    """Return YouTube playlist data."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], "not_configured", "YouTube Playlists is not configured")
        return

    entry = entries[0]
    coordinator = entry.runtime_data
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], "no_data", "YouTube data is not available")
        return

    options = entry.options
    connection.send_result(
        msg["id"],
        {
            "playlists": coordinator.data,
            "playback": {
                "speaker": (
                    options.get(CONF_PLAY_TARGET_MODE) == PLAY_TARGET_MEDIA_PLAYER
                    and bool(options.get(CONF_PLAY_MEDIA_PLAYER))
                ),
                "tv": (
                    options.get(CONF_PLAY_TARGET_MODE) == PLAY_TARGET_MEDIA_PLAYER
                    and bool(options.get(CONF_PLAY_TV))
                ),
            },
        },
    )
