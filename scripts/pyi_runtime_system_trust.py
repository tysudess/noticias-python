from __future__ import annotations

# Executado pelo PyInstaller antes do código principal.
# O objetivo é habilitar o trust store do sistema antes de qualquer biblioteca
# de rede criar SSLContext/Session.
try:
    from monitor_noticias.platform.tls import (
        install_system_trust_store,
    )

    install_system_trust_store()
except Exception:
    # A aplicação repetirá a tentativa com logging já configurado.
    pass
