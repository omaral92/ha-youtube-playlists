"""Constants."""
from homeassistant.const import Platform

DOMAIN = "youtube_playlists"
NAME = "YouTube Playlists"
MANUFACTURER = "YouTube"
UPDATE_INTERVAL_MINUTES = 15
PLATFORMS: list[Platform] = []
WS_TYPE = "youtube_playlists/get_data"

# Options
CONF_PLAYLIST_FILTER_MODE = "playlist_filter_mode"
CONF_PLAYLIST_PATTERN = "playlist_pattern"
CONF_PLAY_TARGET_MODE = "play_target_mode"
CONF_PLAY_MEDIA_PLAYER = "play_media_player"
CONF_PLAY_POWER_ON_ENTITY = "play_power_on_entity"
CONF_PLAY_SCRIPT = "play_script"
CONF_PLAY_VOLUME = "play_volume"

FILTER_MODE_ALL = "all"
FILTER_MODE_PATTERN = "pattern"
DEFAULT_PLAYLIST_PATTERN = "HA*"

PLAY_TARGET_SCRIPT = "script"
PLAY_TARGET_MEDIA_PLAYER = "media_player"
DEFAULT_PLAY_VOLUME_PERCENT = 30

# How long to wait for a TV to report "on" after turning it on, and how
# often to check, plus a settle delay after it does before ADB is reliable.
TV_ON_TIMEOUT_SECONDS = 35
TV_ON_POLL_INTERVAL_SECONDS = 2
TV_ON_SETTLE_DELAY_SECONDS = 3
YOUTUBE_PROFILE_PICKER_DELAY_SECONDS = 5
OFF_STATES = ("off", "unavailable", "unknown", "standby")

SERVICE_PLAY_VIDEO = "play_video"

# Frontend card (served directly by the integration, no manual resource needed)
CARD_URL_PATH = "/youtube_playlists_files"
CARD_FILENAME = "youtube-playlist-card.js"
