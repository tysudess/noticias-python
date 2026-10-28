from __future__ import annotations

import logging
import time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.current import (
    is_linux,
    is_windows,
)


log = logging.getLogger(__name__)

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

        started = time.monotonic()

        try:
            # Os stores atuais retornam texto vazio quando não há segredo.
            # No Linux, exists() já chama load() no Secret Service; chamar
            # exists() aqui e depois load() duplicava a viagem D-Bus.
            return (
                self._store.load()
                or ""
            ).strip()

        except Exception as exc:
            # Registra apenas a classe da exceção; a mensagem pode conter
            # caminhos, dados internos ou detalhes do backend de credenciais.
            log.warning(
                "Autenticação: falha ao ler token do cofre seguro (%s).",
                type(exc).__name__,
            )
            return ""

        finally:
            elapsed_ms = int(
                (time.monotonic() - started) * 1000
            )

            if elapsed_ms >= 250:
                if is_windows():
                    backend = "DPAPI CurrentUser"
                elif is_linux():
                    backend = "Secret Service / Keyring"
                else:
                    backend = "Indisponível"

                # Registra apenas a duração e o backend: nunca o token.
                log.warning(
                    "Autenticação: leitura do token no cofre seguro demorou "
                    "%s ms (%s).",
                    elapsed_ms,
                    backend,
                )

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
