from __future__ import annotations

"""V124: tratamento consistente de falhas ao validar a sessão salva."""

from .reliability_v123 import _DEFINITIVE_SESSION_FAILURES


def handle_saved_session_failure(runtime, code: str) -> bool:
    """Limpa a sessão salva apenas quando o servidor confirma falha definitiva.

    Retorna True quando o código indica que a sessão não pode mais ser usada.
    Falhas transitórias ou desconhecidas preservam o token para nova tentativa.
    """
    normalized = str(code or "").strip().upper()
    definitive = normalized in _DEFINITIVE_SESSION_FAILURES

    if definitive:
        runtime.token_store.clear()

    runtime.session = None
    return definitive
