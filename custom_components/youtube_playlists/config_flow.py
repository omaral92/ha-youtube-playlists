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

from .const import CONF_NOTIFY_SCRIPT, DOMAIN

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
        """Let the user pick a script to run when new videos are found."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_script = self.config_entry.options.get(CONF_NOTIFY_SCRIPT)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_SCRIPT, default=current_script
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="script")
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
