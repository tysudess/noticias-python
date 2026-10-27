from __future__ import annotations

from .client import AuthApiClient, AuthApiError
from .config import AUTH_API_URL, auth_server_configured
from .device import DeviceIdentity, current_device_identity
from .models import AuthSession, AuthUser
from .runtime import AuthRuntime
from .storage import AuthTokenStore
from .reliability_v123 import install_auth_reliability_patch

# A política de resiliência é instalada depois de carregar as classes públicas,
# mantendo a mudança isolada e compatível com o bootstrap atual.
install_auth_reliability_patch()

__all__ = [
    "AUTH_API_URL",
    "AuthApiClient",
    "AuthApiError",
    "AuthRuntime",
    "AuthSession",
    "AuthTokenStore",
    "AuthUser",
    "DeviceIdentity",
    "auth_server_configured",
    "current_device_identity",
]
