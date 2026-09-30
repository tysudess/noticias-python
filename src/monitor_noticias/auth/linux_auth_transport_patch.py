from __future__ import annotations

import logging
import sys
import threading
import time

import requests

from monitor_noticias.auth.client import AuthApiClient
from monitor_noticias.networking.proxy import (
    corporate_tls_compatibility,
)


log = logging.getLogger(
    "monitor_noticias.auth.linux_transport"
)

_INSTALLED = False


def _is_linux_corporate_proxy(
    client: AuthApiClient,
) -> bool:
    if not sys.platform.startswith("linux"):
        return False

    settings = getattr(
        client,
        "proxy_settings",
        None,
    )

    if settings is None:
        return False

    try:
        cfg = settings.load()
    except Exception:
        return False

    return bool(
        cfg.enabled
        and cfg.ready
        and corporate_tls_compatibility(cfg)
    )


def _warm_auth_server_once(
    client: AuthApiClient,
) -> None:
    """Aquece o Apps Script antes do primeiro POST no Ubuntu corporativo.

    A chamada é curta e best-effort. Ela usa a MESMA requests.Session do
    cliente, portanto, quando o GET responde, o CONNECT/TLS do proxy e o
    processo do Apps Script já ficam preparados para o POST de validate/login.

    Isso não valida credenciais e nunca envia usuário, senha ou token.
    """

    if not _is_linux_corporate_proxy(
        client
    ):
        return

    lock = getattr(
        client,
        "_linux_warm_lock",
        None,
    )

    if lock is None:
        lock = threading.Lock()
        client._linux_warm_lock = lock

    with lock:
        if getattr(
            client,
            "_linux_auth_warm_attempted",
            False,
        ):
            return

        # Marca antes da rede para garantir no máximo uma tentativa por
        # instância do cliente, inclusive se o proxy estiver indisponível.
        client._linux_auth_warm_attempted = True

        try:
            (
                session,
                cfg,
                proxies,
                verify,
            ) = client._request_context()

            headers = client._headers()
            headers["Connection"] = "keep-alive"

            started = time.monotonic()

            response = session.get(
                client.api_url,
                timeout=(2.5, 4.0),
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                headers=headers,
            )

            elapsed = int(
                (time.monotonic() - started)
                * 1000
            )

            if 200 <= response.status_code <= 399:
                log.info(
                    "AUTH Ubuntu warm-up concluído: %sms",
                    elapsed,
                )
            else:
                log.warning(
                    "AUTH Ubuntu warm-up respondeu HTTP %s em %sms.",
                    response.status_code,
                    elapsed,
                )

        except requests.exceptions.Timeout:
            log.warning(
                "AUTH Ubuntu warm-up excedeu o limite curto; "
                "seguindo para a autenticação normal."
            )
        except requests.exceptions.RequestException as exc:
            log.warning(
                "AUTH Ubuntu warm-up não concluiu: %s",
                exc.__class__.__name__,
            )
        except Exception as exc:
            log.warning(
                "AUTH Ubuntu warm-up ignorado: %s",
                exc.__class__.__name__,
            )


def install_linux_auth_transport_patch() -> None:
    """Instala warm-up somente em Ubuntu/Linux + proxy corporativo."""

    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    original_login = AuthApiClient.login
    original_validate = AuthApiClient.validate

    def login(
        self: AuthApiClient,
        username: str,
        password: str,
    ):
        _warm_auth_server_once(self)
        return original_login(
            self,
            username,
            password,
        )

    def validate(
        self: AuthApiClient,
        token: str,
    ):
        _warm_auth_server_once(self)
        return original_validate(
            self,
            token,
        )

    login._central_linux_auth_v97 = True
    validate._central_linux_auth_v97 = True

    AuthApiClient.login = login
    AuthApiClient.validate = validate

    _INSTALLED = True
