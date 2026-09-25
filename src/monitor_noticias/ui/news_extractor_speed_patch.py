from __future__ import annotations

import os
from contextlib import contextmanager


_PATCHED = False


@contextmanager
def _temporary_environment(values: dict[str, str]):
    previous: dict[str, str | None] = {}
    try:
        for key, value in values.items():
            previous[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def install_news_extractor_speed_patch() -> None:
    """Ajuste seguro para reduzir tempo morto no extrator de notícias.

    A melhoria é conservadora: não altera a lógica principal da extração,
    apenas informa ao runtime integrado que a execução deve priorizar modo
    rápido, com bloqueio de mídia e timeouts menores para esperas passivas.
    """

    global _PATCHED
    if _PATCHED:
        return

    try:
        from monitor_noticias.ui.news_extractor_page import (
            NewsExtractorPage,
        )
    except Exception:
        return

    original_extract = NewsExtractorPage.extract

    def patched_extract(self: NewsExtractorPage) -> None:
        env = {
            "CENTRAL_NEWS_FAST_MODE": "1",
            "CENTRAL_NEWS_BLOCK_IMAGES": "1",
            "CENTRAL_NEWS_BLOCK_MEDIA": "1",
            "CENTRAL_NEWS_NAV_TIMEOUT_MS": "18000",
            "CENTRAL_NEWS_IDLE_TIMEOUT_MS": "800",
        }

        status = getattr(self, "status", None)
        if status is not None and hasattr(status, "setText"):
            try:
                status.setText(
                    "Iniciando extração em modo rápido..."
                )
            except Exception:
                pass

        with _temporary_environment(env):
            original_extract(self)

    NewsExtractorPage.extract = patched_extract
    _PATCHED = True
