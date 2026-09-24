from __future__ import annotations

import logging
import threading


log = logging.getLogger(__name__)

_LOCK = threading.Lock()
_INSTALLED = False
_LAST_ERROR = ""


def install_system_trust_store() -> tuple[bool, str]:
    """Faz Python/Requests usar o repositório de CAs confiáveis do SO.

    Isso é especialmente importante em redes corporativas com inspeção
    HTTPS, onde o certificado raiz da organização normalmente está no
    Windows Certificate Store ou no trust store do Linux, mas não no
    bundle interno do ``certifi``.

    A função é idempotente e pode ser chamada tanto pelo runtime hook do
    PyInstaller quanto pela inicialização normal da aplicação.
    """

    global _INSTALLED
    global _LAST_ERROR

    with _LOCK:
        if _INSTALLED:
            return True, "Trust store do sistema já está ativo."

        try:
            import truststore

            truststore.inject_into_ssl()

            _INSTALLED = True
            _LAST_ERROR = ""

            log.info(
                "TLS configurado para usar o trust store nativo do sistema."
            )

            return True, "Trust store nativo do sistema ativado."

        except Exception as exc:
            _LAST_ERROR = (
                str(exc)
                or exc.__class__.__name__
            )

            log.exception(
                "Não foi possível ativar o trust store nativo do sistema."
            )

            return (
                False,
                "Não foi possível ativar os certificados do sistema: "
                + _LAST_ERROR,
            )


def system_trust_store_active() -> bool:
    return bool(_INSTALLED)


def system_trust_store_error() -> str:
    return _LAST_ERROR
