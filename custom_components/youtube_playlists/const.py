"""Constants."""
from homeassistant.const import Platform

DOMAIN = "youtube_playlists"
NAME = "YouTube Playlists"
MANUFACTURER = "YouTube"
PLAYLIST_PREFIX = "HA"
UPDATE_INTERVAL_MINUTES = 15
PLATFORMS: list[Platform] = []
WS_TYPE = "youtube_playlists/get_data"

# Options
CONF_NOTIFY_SCRIPT = "notify_script"
