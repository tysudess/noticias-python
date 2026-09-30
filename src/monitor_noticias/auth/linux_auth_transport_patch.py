from __future__ import annotations

import logging
import sys
import time

import requests

from monitor_noticias.networking.proxy import (
    corporate_tls_compatibility,
)
from monitor_noticias.auth.client import AuthApiClient, AuthApiError


log = logging.getLogger(
    "monitor_noticias.auth.linux_transport"
)

_INSTALLED = False


def install_linux_auth_transport_patch() -> None:
    """Instrumenta o transporte Linux sem criar uma requisição anterior ao login.

    V97 fazia um GET de aquecimento antes do POST real. Atrás do proxy
    corporativo esse GET podia consumir o próprio timeout e ainda relia o
    Secret Service diversas vezes. V98 remove esse aquecimento: a primeira
    operação de rede volta a ser o POST real de login/validate e a mesma
    ``requests.Session`` continua sendo reutilizada normalmente depois disso.

    O patch registra apenas metadados de transporte; nunca URL completa,
    usuário, senha, payload ou token.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    cls = AuthApiClient

    original_context = cls._request_context
    original_perform = cls._perform_request

    if not getattr(
        original_context,
        "_central_linux_auth_v98",
        False,
    ):
        def patched_context(self):
            started = time.monotonic()
            result = original_context(self)
            elapsed_ms = int(
                (time.monotonic() - started) * 1000
            )

            _session, cfg, _proxies, verify = result

            proxy_enabled = bool(
                cfg is not None and cfg.enabled
            )
            host = (
                str(cfg.host or "")
                if cfg is not None
                else ""
            )
            port = (
                int(cfg.port)
                if cfg is not None
                else 0
            )
            compat = bool(
                cfg is not None
                and corporate_tls_compatibility(cfg)
            )

            log.info(
                "AUTH contexto Linux: proxy=%s host=%s porta=%s "
                "tls_compat=%s verify=%s preparo_ms=%s "
                "timeout_connect=%.1fs timeout_read=%.1fs",
                proxy_enabled,
                host,
                port,
                compat,
                bool(verify),
                elapsed_ms,
                float(self.connect_timeout),
                float(self.read_timeout),
            )

            return result

        patched_context._central_linux_auth_v98 = True
        cls._request_context = patched_context

    if not getattr(
        original_perform,
        "_central_linux_auth_v98",
        False,
    ):
        def patched_perform(
            self,
            method: str,
            *,
            operation: str,
            **kwargs,
        ):
            started = time.monotonic()

            try:
                response = original_perform(
                    self,
                    method,
                    operation=operation,
                    **kwargs,
                )

                log.info(
                    "AUTH resposta Linux: operação=%s método=%s "
                    "status=%s redirects=%s final_host=%s total_ms=%s",
                    operation,
                    method,
                    int(response.status_code),
                    len(response.history),
                    str(response.url or "").split("/", 3)[2]
                    if "://" in str(response.url or "")
                    else "",
                    int((time.monotonic() - started) * 1000),
                )
                return response

            except requests.exceptions.ConnectTimeout as exc:
                log.warning(
                    "AUTH falha Linux: operação=%s etapa=connect_timeout "
                    "total_ms=%s",
                    operation,
                    int((time.monotonic() - started) * 1000),
                )
                if str(operation).startswith("test_"):
                    raise
                raise AuthApiError(
                    "Tempo limite ao estabelecer conexão com o proxy/servidor "
                    "de autenticação.",
                    code="NETWORK_TIMEOUT",
                ) from exc

            except requests.exceptions.ReadTimeout as exc:
                log.warning(
                    "AUTH falha Linux: operação=%s etapa=read_timeout "
                    "total_ms=%s",
                    operation,
                    int((time.monotonic() - started) * 1000),
                )
                if str(operation).startswith("test_"):
                    raise
                raise AuthApiError(
                    "A conexão com o proxy/servidor foi estabelecida, mas o "
                    "servidor de autenticação não respondeu dentro do prazo.",
                    code="NETWORK_TIMEOUT",
                ) from exc

            except requests.exceptions.ProxyError as exc:
                log.warning(
                    "AUTH falha Linux: operação=%s etapa=proxy tipo=%s "
                    "total_ms=%s",
                    operation,
                    exc.__class__.__name__,
                    int((time.monotonic() - started) * 1000),
                )
                raise

            except requests.exceptions.SSLError as exc:
                log.warning(
                    "AUTH falha Linux: operação=%s etapa=tls tipo=%s "
                    "total_ms=%s",
                    operation,
                    exc.__class__.__name__,
                    int((time.monotonic() - started) * 1000),
                )
                raise

            except requests.exceptions.RequestException as exc:
                log.warning(
                    "AUTH falha Linux: operação=%s etapa=request tipo=%s "
                    "total_ms=%s",
                    operation,
                    exc.__class__.__name__,
                    int((time.monotonic() - started) * 1000),
                )
                raise

        patched_perform._central_linux_auth_v98 = True
        cls._perform_request = patched_perform

    _INSTALLED = True
