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
CONF_PLAY_WAKE_DELAY = "play_wake_delay"
CONF_PLAY_SETTLE_DELAY = "play_settle_delay"

FILTER_MODE_ALL = "all"
FILTER_MODE_PATTERN = "pattern"
DEFAULT_PLAYLIST_PATTERN = "HA*"

PLAY_TARGET_SCRIPT = "script"
PLAY_TARGET_MEDIA_PLAYER = "media_player"
DEFAULT_PLAY_VOLUME_PERCENT = 30

# Android TV wake-up sequence (see play.py). Both delays are configurable in
# the integration options; these are the defaults.
#   1. turn the TV on
#   2. wait DEFAULT_PLAY_WAKE_DELAY_SECONDS   (lets the TV finish booting)
#   3. reload the Android TV / ADB config entry (brings the device back online)
#   4. wait DEFAULT_PLAY_SETTLE_DELAY_SECONDS (lets the reloaded entry settle)
#   5. send the ADB YouTube launch command
DEFAULT_PLAY_WAKE_DELAY_SECONDS = 5
DEFAULT_PLAY_SETTLE_DELAY_SECONDS = 3
MAX_PLAY_DELAY_SECONDS = 60
OFF_STATES = ("off", "unavailable", "unknown", "standby")

SERVICE_PLAY_VIDEO = "play_video"

# Frontend card (served directly by the integration, no manual resource needed)
CARD_URL_PATH = "/youtube_playlists_files"
CARD_FILENAME = "youtube-playlist-card.js"
