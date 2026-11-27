from __future__ import annotations

"""V179 — renderização isolada das miniaturas do Estúdio de Artes.

A implementação anterior protegia a renderização da V175 com um bloqueio
 temporário, mas ainda escondia/restaurava objetos na cena ativa. Isso podia
emitir novos sinais ``scene.changed`` enquanto o editor acabava de ser aberto.

Agora as miniaturas usam a cena auxiliar da V176, construída a partir dos dados
serializados da página. A cena de edição não é alterada durante a prévia.
"""

import logging

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon


log = logging.getLogger(__name__)
_INSTALLED = False


def _render_page_thumbnail_isolated(
    page,
    page_index: int,
    preview_renderer=None,
    icon_factory=None,
    size_factory=None,
):
    """Atualiza uma miniatura sem modificar a cena gráfica em edição.

    ``preview_renderer`` e as fábricas opcionais permitem testar a lógica sem
    acionar widgets ou renderização reais. Em produção, a prévia V176 é usada.
    """
    if getattr(page, "_v179_thumbnail_rendering", False):
        return None

    tab_bar = getattr(page, "v150_tab_bar", None)
    pages = getattr(page, "_v150_pages", None)
    if tab_bar is None or not hasattr(tab_bar, "setTabIcon") or not isinstance(pages, list):
        return None

    active_index = int(getattr(page, "_v150_active_index", -1))
    if page_index != active_index or not 0 <= page_index < len(pages):
        return None

    entry = pages[page_index]
    page_id = str(entry.get("id") or page_index) if isinstance(entry, dict) else str(page_index)
    page._v179_thumbnail_rendering = True
    try:
        if preview_renderer is None:
            from monitor_noticias.ui.art_studio_v176 import _render_page_preview

            preview_renderer = _render_page_preview
        make_size = size_factory or QSize
        make_icon = icon_factory or QIcon

        # A V176 cria uma QGraphicsScene independente e não oculta itens da
        # página ativa. O tamanho preserva a proporção usada pela barra V175.
        pixmap = preview_renderer(page, entry, make_size(58, 42))
        cache = getattr(page, "_v175_thumbnail_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            page._v175_thumbnail_cache = cache
        cache[page_id] = make_icon(pixmap)

        for index, item in enumerate(pages):
            item_id = str(item.get("id") or index) if isinstance(item, dict) else str(index)
            icon = cache.get(item_id)
            tab_bar.setTabIcon(index, icon if icon is not None else make_icon())
        return cache[page_id]
    except Exception:
        # Uma prévia nunca pode encerrar a Central ou impedir a abertura do editor.
        log.exception("Falha ao gerar miniatura isolada da página %s", page_index)
        return None
    finally:
        page._v179_thumbnail_rendering = False


def install_art_studio_v179() -> None:
    """Aplica a renderização isolada antes da criação da MainWindow."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import art_studio_v175

    if getattr(art_studio_v175, "_v179_thumbnail_guard_installed", False):
        _INSTALLED = True
        return

    art_studio_v175._v179_thumbnail_original_renderer = art_studio_v175._render_page_thumbnail
    art_studio_v175._render_page_thumbnail = _render_page_thumbnail_isolated
    art_studio_v175._v179_thumbnail_guard_installed = True
    _INSTALLED = True
