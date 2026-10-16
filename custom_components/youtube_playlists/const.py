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
CONF_PLAY_VOLUME_ENTITY = "play_volume_entity"
CONF_PLAY_SETTLE_DELAY = "play_settle_delay"
CONF_PLAY_ONLINE_TIMEOUT = "play_online_timeout"
# Options from older versions, no longer used (dropped when the options are saved)
LEGACY_PLAY_OPTIONS = ("play_wake_delay", "play_reload_interval")

FILTER_MODE_ALL = "all"
FILTER_MODE_PATTERN = "pattern"
DEFAULT_PLAYLIST_PATTERN = "HA*"

PLAY_TARGET_SCRIPT = "script"
PLAY_TARGET_MEDIA_PLAYER = "media_player"
DEFAULT_PLAY_VOLUME_PERCENT = 30

# Android TV wake-up sequence (see play.py). Only the timeout and settle delay
# are options; these are the defaults.
#   1. turn the TV on
#   2. wait for the media player to come online: ask it to reconnect (force an
#      entity update; reload the Android TV entry only if it isn't loaded) and
#      react the moment its state changes. Some TVs need 30s+ after power-on
#      before their ADB server accepts connections; until then the entity is
#      unavailable and Home Assistant silently ignores service calls to it, so
#      we must not send the launch command before this. Give up after
#      DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS (counted from the power-on).
#   3. wait DEFAULT_PLAY_SETTLE_DELAY_SECONDS (lets the device settle)
#   4. send the ADB YouTube launch command
DEFAULT_PLAY_SETTLE_DELAY_SECONDS = 3
DEFAULT_PLAY_ONLINE_TIMEOUT_SECONDS = 90
MAX_PLAY_DELAY_SECONDS = 60
MAX_PLAY_ONLINE_TIMEOUT_SECONDS = 180
# Pause between connection attempts while the TV is still booting (a state
# change ends the pause early).
PLAY_ONLINE_NUDGE_INTERVAL_SECONDS = 2
# Once the playback device is online and settled, how much longer to hold the
# launch for the volume entity (e.g. the TV itself) to come online so the volume
# can be set first. Past this the video starts anyway, without the volume step.
PLAY_VOLUME_ENTITY_GRACE_SECONDS = 15
# How often to log progress at INFO level while waiting, so a slow/failed
# wake-up is visible without needing debug logging enabled.
PLAY_ONLINE_PROGRESS_LOG_INTERVAL_SECONDS = 10
OFF_STATES = ("off", "unavailable", "unknown", "standby")
# States meaning the entity cannot accept service calls yet.
UNAVAILABLE_STATES = ("unavailable", "unknown")

SERVICE_PLAY_VIDEO = "play_video"

# Frontend card (served directly by the integration, no manual resource needed)
CARD_URL_PATH = "/youtube_playlists_files"
CARD_FILENAME = "youtube-playlist-card.js"
