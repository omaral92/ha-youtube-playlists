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
    CONF_NOTIFY_SCRIPT,
    CONF_PLAYLIST_FILTER_MODE,
    CONF_PLAYLIST_PATTERN,
    DEFAULT_PLAYLIST_PATTERN,
    DOMAIN,
    FILTER_MODE_ALL,
    FILTER_MODE_PATTERN,
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

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a script to run on new videos, and which playlists to import."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if (
                user_input.get(CONF_PLAYLIST_FILTER_MODE) == FILTER_MODE_PATTERN
                and not user_input.get(CONF_PLAYLIST_PATTERN, "").strip()
            ):
                errors["playlist_pattern"] = "pattern_required"
            else:
                return self.async_create_entry(data=user_input)

        current_script = self.config_entry.options.get(CONF_NOTIFY_SCRIPT)
        current_mode = self.config_entry.options.get(
            CONF_PLAYLIST_FILTER_MODE, FILTER_MODE_ALL
        )
        current_pattern = self.config_entry.options.get(
            CONF_PLAYLIST_PATTERN, DEFAULT_PLAYLIST_PATTERN
        )

        if user_input is not None:
            # Repopulate the form with what the user just submitted, on error.
            current_script = user_input.get(CONF_NOTIFY_SCRIPT, current_script)
            current_mode = user_input.get(CONF_PLAYLIST_FILTER_MODE, current_mode)
            current_pattern = user_input.get(CONF_PLAYLIST_PATTERN, current_pattern)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLAYLIST_FILTER_MODE, default=current_mode
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
                    CONF_PLAYLIST_PATTERN, default=current_pattern
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_NOTIFY_SCRIPT, default=current_script
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="script")
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
