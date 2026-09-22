from __future__ import annotations

from monitor_noticias.ui import url_tools
from monitor_noticias.ui.news_page import NewsPage


_PATCHED = False


def install_news_direct_link_patch() -> None:
    """Garante URL do veículo também no botão Extrair matéria.

    Abrir/Copiar/WhatsApp já chamam url_tools. O botão Extrair era o único
    caminho que emitia `news.link` cru diretamente para o Extrator.
    """

    global _PATCHED

    if _PATCHED:
        return

    original_init = (
        NewsPage.__init__
    )

    def patched_init(
        self,
        *args,
        **kwargs,
    ):
        original_init(
            self,
            *args,
            **kwargs,
        )

        # O __init__ original liga:
        # delegate.extract_requested -> NewsPage.extract_requested.emit
        #
        # Substituímos somente essa ligação para resolver Google News primeiro.
        try:
            self.delegate.extract_requested.disconnect()
        except Exception:
            pass

        def emit_resolved(
            url: str,
        ) -> None:
            resolved = (
                url_tools
                .resolve_article_url(
                    url
                )
            )

            self.extract_requested.emit(
                resolved
            )

        self.delegate.extract_requested.connect(
            emit_resolved
        )

        # Mantém referência para evitar coleta do callable em bindings
        # mais antigos do PySide.
        self._news_extract_resolved_slot = (
            emit_resolved
        )

    NewsPage.__init__ = (
        patched_init
    )

    _PATCHED = True
