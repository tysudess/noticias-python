from __future__ import annotations

from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.current import (
    is_linux,
    is_windows,
)


AUTH_KEYRING_SERVICE = (
    "CentralInteligenteDeMidia"
)

AUTH_KEYRING_ACCOUNT = (
    "auth-session-token"
)


class AuthTokenStore:
    """Token de sessão protegido pela plataforma.

    Windows:
        DPAPI CurrentUser.

    Ubuntu/Linux:
        Secret Service / keyring.

    Não existe fallback plaintext.
    """

    def __init__(
        self,
        paths: AppPaths,
    ) -> None:
        self.paths = paths
        self._store = (
            self._create_store()
        )

    def _create_store(
        self,
    ):
        if is_windows():
            from monitor_noticias.windows.dpapi import (
                DpapiTextStore,
            )

            return DpapiTextStore(
                self.paths.data
                / "auth"
                / "session_token.dpapi"
            )

        if is_linux():
            from monitor_noticias.platform.credentials import (
                LinuxKeyringTextStore,
            )

            return LinuxKeyringTextStore(
                service_name=
                    AUTH_KEYRING_SERVICE,
                account_name=
                    AUTH_KEYRING_ACCOUNT,
            )

        return None

    def load(
        self,
    ) -> str:
        if self._store is None:
            return ""

        try:
            if not self._store.exists():
                return ""

            return (
                self._store.load()
                or ""
            ).strip()

        except Exception:
            return ""

    def save(
        self,
        token: str,
    ) -> None:
        if self._store is None:
            raise RuntimeError(
                "Armazenamento seguro de sessão "
                "não disponível neste sistema."
            )

        self._store.save(
            token
        )

    def clear(
        self,
    ) -> None:
        if self._store is None:
            return

        try:
            self._store.delete()
        except Exception:
            pass
