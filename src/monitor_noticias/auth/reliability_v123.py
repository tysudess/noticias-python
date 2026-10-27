from __future__ import annotations

"""Correções V123 para falhas transitórias e mensagens seguras de autenticação.

A instalação é idempotente. Não altera o transporte, os timeouts, o proxy,
a validação TLS, as permissões ou as regras do servidor de autenticação.
"""

import requests

from .client import AuthApiClient, AuthApiError
from .runtime import AuthRuntime


# Somente códigos que indicam que a sessão salva deixou de ser válida.
# Códigos de rede, proxy, TLS, indisponibilidade e respostas desconhecidas
# não devem apagar credenciais de sessão persistidas.
_DEFINITIVE_SESSION_FAILURES = frozenset({
    "SESSION_INVALID",
    "SESSION_REVOKED",
    "SESSION_EXPIRED",
    "USER_NOT_FOUND",
    "USER_BLOCKED",
    "USER_EXPIRED",
    "DEVICE_BLOCKED",
    "DEVICE_LIMIT",
    "INVALID_CREDENTIALS",
})

_INSTALLED = False


def _safe_response_excerpt(_response) -> str:
    """Não exibe corpos HTTP arbitrários, que podem conter dados sensíveis."""
    return ""


def _safe_network_error(
    self,
    exc: requests.exceptions.RequestException,
) -> AuthApiError:
    """Converte falhas de rede em mensagem estável sem ecoar URLs/credenciais."""
    error_type = type(exc).__name__
    return AuthApiError(
        "Falha de rede ao acessar o servidor de autenticação "
        f"({error_type}). Verifique a conexão e o Proxy Geral.",
        code="NETWORK_ERROR",
    )


def _validate_saved(self):
    token = self.saved_token()
    if not token:
        return None

    try:
        session = self.client.validate(token)
    except AuthApiError as exc:
        if str(exc.code or "").strip().upper() in _DEFINITIVE_SESSION_FAILURES:
            self.token_store.clear()
        # Em timeout, falha de proxy/TLS, HTTP transitório ou código
        # desconhecido, mantém o token para permitir uma nova tentativa.
        self.session = None
        return None

    self.session = session
    return session


def install_auth_reliability_patch() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    AuthApiClient._safe_response_excerpt = staticmethod(_safe_response_excerpt)
    AuthApiClient._network_error = _safe_network_error
    AuthRuntime.validate_saved = _validate_saved
    _INSTALLED = True
