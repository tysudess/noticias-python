from __future__ import annotations

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import ProxySettings

from .client import AuthApiClient, AuthApiError
from .config import AUTH_API_URL
from .device import current_device_identity
from .models import AuthSession
from .storage import AuthTokenStore


class AuthRuntime:
    """Orquestra autenticação, token seguro e Proxy Geral."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

        self.prefs = SharedPreferences(
            paths.data / "prefs" / "monitor_prefs.properties"
        )

        self.proxy_settings = ProxySettings(
            self.prefs,
            data_dir=paths.data,
        )

        self.device = current_device_identity(paths)
        self.token_store = AuthTokenStore(paths)

        self.client = AuthApiClient(
            AUTH_API_URL,
            self.device,
            proxy_settings=self.proxy_settings,
        )

        self.session: AuthSession | None = None

    def saved_token(self) -> str:
        return self.token_store.load()

    def validate_saved(self) -> AuthSession | None:
        token = self.saved_token()

        if not token:
            return None

        try:
            session = self.client.validate(token)
        except AuthApiError:
            self.token_store.clear()
            return None

        self.session = session
        return session

    def login(
        self,
        username: str,
        password: str,
        *,
        remember: bool,
    ) -> AuthSession:
        session = self.client.login(username, password)

        if remember:
            self.token_store.save(session.token)
        else:
            self.token_store.clear()

        self.session = session
        return session

    def validate_current(self) -> AuthSession:
        if self.session is None:
            raise AuthApiError(
                "Nenhuma sessão autenticada.",
                code="SESSION_MISSING",
            )

        session = self.client.validate(self.session.token)
        self.session = session
        return session

    def logout(self) -> None:
        token = (
            self.session.token
            if self.session is not None
            else self.saved_token()
        )

        try:
            if token:
                self.client.logout(token)
        finally:
            self.token_store.clear()
            self.session = None
