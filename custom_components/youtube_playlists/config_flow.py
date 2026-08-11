"""Config flow for YouTube Playlists."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers import selector
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .const import (
    CONF_PLAY_MEDIA_PLAYER,
    CONF_PLAY_POWER_ON_ENTITY,
    CONF_PLAY_SCRIPT,
    CONF_PLAY_TARGET_MODE,
    CONF_PLAY_VOLUME,
    CONF_PLAYLIST_FILTER_MODE,
    CONF_PLAYLIST_PATTERN,
    DEFAULT_PLAY_VOLUME_PERCENT,
    DEFAULT_PLAYLIST_PATTERN,
    DOMAIN,
    FILTER_MODE_ALL,
    FILTER_MODE_PATTERN,
    PLAY_TARGET_MEDIA_PLAYER,
    PLAY_TARGET_SCRIPT,
)

_LOGGER = logging.getLogger(__name__)


class YouTubePlaylistsConfigFlow(
    AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle a YouTube OAuth2 config flow."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title="YouTube",
            data=data,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> YouTubePlaylistsOptionsFlow:
        """Return the options flow for this integration."""
        return YouTubePlaylistsOptionsFlow()


class YouTubePlaylistsOptionsFlow(OptionsFlow):
    """Handle YouTube Playlists options."""

    def __init__(self) -> None:
        self._data: dict = {}

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Step 1: which playlists to import, and how videos should play."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if (
                user_input[CONF_PLAYLIST_FILTER_MODE] == FILTER_MODE_PATTERN
                and not user_input.get(CONF_PLAYLIST_PATTERN, "").strip()
            ):
                errors["playlist_pattern"] = "pattern_required"
            else:
                self._data.update(user_input)
                if self._data[CONF_PLAY_TARGET_MODE] == PLAY_TARGET_MEDIA_PLAYER:
                    return await self.async_step_media_player()
                return await self.async_step_script()

        current = {
            CONF_PLAYLIST_FILTER_MODE: FILTER_MODE_ALL,
            CONF_PLAYLIST_PATTERN: DEFAULT_PLAYLIST_PATTERN,
            CONF_PLAY_TARGET_MODE: PLAY_TARGET_SCRIPT,
        }
        current.update(self.config_entry.options)
        if user_input is not None:
            current.update(user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLAYLIST_FILTER_MODE,
                    default=current[CONF_PLAYLIST_FILTER_MODE],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=FILTER_MODE_ALL, label="All playlists"
                            ),
                            selector.SelectOptionDict(
                                value=FILTER_MODE_PATTERN,
                                label="Match a pattern / prefix",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key="playlist_filter_mode",
                    )
                ),
                vol.Optional(
                    CONF_PLAYLIST_PATTERN, default=current[CONF_PLAYLIST_PATTERN]
                ): selector.TextSelector(),
                vol.Required(
                    CONF_PLAY_TARGET_MODE, default=current[CONF_PLAY_TARGET_MODE]
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=PLAY_TARGET_SCRIPT,
                                label="Run a script when a video is clicked",
                            ),
                            selector.SelectOptionDict(
                                value=PLAY_TARGET_MEDIA_PLAYER,
                                label="Play directly on a media player entity",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key="play_target_mode",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )

    async def async_step_script(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Step 2a: pick the script to run (script mode only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_PLAY_SCRIPT):
                errors["play_script"] = "script_required"
            else:
                self._data.update(user_input)
                self._data.pop(CONF_PLAY_MEDIA_PLAYER, None)
                self._data.pop(CONF_PLAY_POWER_ON_ENTITY, None)
                self._data.pop(CONF_PLAY_VOLUME, None)
                return self.async_create_entry(data=self._data)

        current_script = self.config_entry.options.get(CONF_PLAY_SCRIPT)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLAY_SCRIPT, default=current_script
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="script")
                ),
            }
        )

        return self.async_show_form(
            step_id="script", data_schema=schema, errors=errors
        )

    async def async_step_media_player(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Step 2b: pick the media player and volume (media player mode only).

        Only Android TV entities are supported, since playback is
        launched via an ADB intent (requires the Android TV integration with
        ADB debugging enabled on the device).
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_PLAY_MEDIA_PLAYER):
                errors["play_media_player"] = "media_player_required"
            else:
                self._data.update(user_input)
                self._data.pop(CONF_PLAY_SCRIPT, None)
                return self.async_create_entry(data=self._data)

        current = {
            CONF_PLAY_MEDIA_PLAYER: self.config_entry.options.get(
                CONF_PLAY_MEDIA_PLAYER
            ),
            CONF_PLAY_POWER_ON_ENTITY: self.config_entry.options.get(
                CONF_PLAY_POWER_ON_ENTITY
            ),
            CONF_PLAY_VOLUME: self.config_entry.options.get(
                CONF_PLAY_VOLUME, DEFAULT_PLAY_VOLUME_PERCENT
            ),
        }
        if user_input is not None:
            current.update(user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLAY_MEDIA_PLAYER, default=current[CONF_PLAY_MEDIA_PLAYER]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="media_player")
                ),
                vol.Optional(
                    CONF_PLAY_POWER_ON_ENTITY,
                    default=current[CONF_PLAY_POWER_ON_ENTITY],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig()
                ),
                vol.Optional(
                    CONF_PLAY_VOLUME, default=current[CONF_PLAY_VOLUME]
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="media_player", data_schema=schema, errors=errors
        )
