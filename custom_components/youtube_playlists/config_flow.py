"""Config flow for YouTube Playlists."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .const import DOMAIN

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
