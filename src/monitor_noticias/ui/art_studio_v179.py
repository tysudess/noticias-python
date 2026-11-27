from __future__ import annotations

"""V179 — renderização isolada e segura das miniaturas do Estúdio de Artes.

As miniaturas usam a cena auxiliar da V176 e nunca alteram a cena que está
sendo editada. Callbacks Qt adiados também verificam se o objeto C++ ainda
existe antes de acessar widgets, evitando falhas durante o fechamento.
"""

import logging
from typing import Callable

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon


log = logging.getLogger(__name__)
_INSTALLED = False


def _is_valid_qobject(value) -> bool:
    """Retorna False quando o wrapper Python aponta para um QObject destruído."""
    if value is None:
        return False
    try:
        import shiboken6

        return bool(shiboken6.isValid(value))
    except (ImportError, AttributeError, TypeError):
        # O fallback mantém os testes sem Qt e instalações alternativas úteis.
        try:
            object_name = getattr(value, "objectName", None)
            if callable(object_name):
                object_name()
            return True
        except RuntimeError:
            return False


def _guard_theme_refresh_callback(
    callback: Callable,
    validity_check: Callable | None = None,
) -> Callable:
    """Evita que QTimer/eventFilter aplique tema em páginas já destruídas."""
    check = validity_check or _is_valid_qobject

    def guarded(page_ref, *args, **kwargs):
        try:
            page = page_ref()
        except Exception:
            return None
        if page is None:
            return None
        try:
            if not check(page):
                return None
        except Exception:
            return None
        return callback(page_ref, *args, **kwargs)

    return guarded


def _install_theme_refresh_lifetime_guards() -> None:
    """Protege os callbacks adiados das camadas visuais V175–V177."""
    from monitor_noticias.ui import art_studio_v175, art_studio_v176, art_studio_v177

    for module in (art_studio_v175, art_studio_v176, art_studio_v177):
        if getattr(module, "_v179_theme_refresh_lifetime_guard", False):
            continue
        callback = getattr(module, "_apply_theme_from_ref", None)
        if callable(callback):
            module._apply_theme_from_ref = _guard_theme_refresh_callback(callback)
            module._v179_theme_refresh_lifetime_guard = True


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
    if not _is_valid_qobject(page):
        return None
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
        # Se o wrapper Qt tiver sido invalidado durante a prévia, não tentar
        # gravar novamente um atributo no objeto C++ destruído.
        if _is_valid_qobject(page):
            page._v179_thumbnail_rendering = False


def install_art_studio_v179() -> None:
    """Aplica a renderização isolada e as proteções Qt antes da MainWindow."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import art_studio_v175

    if not getattr(art_studio_v175, "_v179_thumbnail_guard_installed", False):
        art_studio_v175._v179_thumbnail_original_renderer = art_studio_v175._render_page_thumbnail
        art_studio_v175._render_page_thumbnail = _render_page_thumbnail_isolated
        art_studio_v175._v179_thumbnail_guard_installed = True

    _install_theme_refresh_lifetime_guards()
    _INSTALLED = True
