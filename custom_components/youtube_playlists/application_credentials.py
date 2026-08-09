"""Application credentials for YouTube Playlists."""
from __future__ import annotations

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2ImplementationWithPkce,
)

from .const import DOMAIN

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class YouTubeOAuth2Implementation(LocalOAuth2ImplementationWithPkce):
    """YouTube OAuth implementation."""

    @property
    def extra_authorize_data(self) -> dict:
        """Return extra authorization data."""
        return super().extra_authorize_data | {
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> YouTubeOAuth2Implementation:
    """Return the OAuth implementation."""
    return YouTubeOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        AUTHORIZE_URL,
        TOKEN_URL,
        credential.client_secret,
        code_verifier_length=128,
    )


async def async_get_authorization_server(
    hass: HomeAssistant,
) -> AuthorizationServer:
    """Return the authorization server."""
    return AuthorizationServer(
        authorize_url=AUTHORIZE_URL,
        token_url=TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return application credential description placeholders."""
    return {
        "console_url": "https://console.cloud.google.com/apis/credentials",
    }
