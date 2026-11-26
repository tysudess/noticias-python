from __future__ import annotations

"""V179 — evita recursão de miniaturas e bloqueio da interface.

A V175 oculta/restaura guias e alças durante a renderização das miniaturas.
Essas operações fazem QGraphicsScene.changed ser emitido de forma enfileirada,
depois que a V175 já havia baixado seu sinalizador de renderização. O handler
agenda outra miniatura e pode manter o event loop ocupado indefinidamente.

A V179 mantém o sinalizador ativo por um curto intervalo após a renderização,
tempo suficiente para consumir o sinal Qt pendente. As miniaturas continuam
sendo atualizadas quando o usuário modifica o canvas.
"""

import weakref

from PySide6.QtCore import QTimer


_INSTALLED = False


def _guard_thumbnail_renderer(original_renderer, single_shot=None):
    schedule_single_shot = single_shot or QTimer.singleShot
    """Mantém o bloqueio ativo até os sinais scene.changed já enfileirados passarem."""

    def render_with_scene_change_guard(page, page_index: int):
        if getattr(page, "_v179_thumbnail_rendering", False):
            return None

        page._v179_thumbnail_rendering = True
        try:
            return original_renderer(page, page_index)
        finally:
            # A V175 zera esta flag ao sair, mas QGraphicsScene.changed pode
            # chegar somente no próximo ciclo do event loop.
            page._v175_rendering_thumbnail = True
            page_ref = weakref.ref(page)

            def release_guard():
                live_page = page_ref()
                if live_page is None:
                    return
                live_page._v175_rendering_thumbnail = False
                live_page._v179_thumbnail_rendering = False

            schedule_single_shot(120, release_guard)

    return render_with_scene_change_guard


def install_art_studio_v179() -> None:
    """Aplica a proteção antes da criação da MainWindow."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import art_studio_v175

    if getattr(art_studio_v175, "_v179_thumbnail_guard_installed", False):
        _INSTALLED = True
        return

    original = art_studio_v175._render_page_thumbnail
    art_studio_v175._render_page_thumbnail = _guard_thumbnail_renderer(original)
    art_studio_v175._v179_thumbnail_guard_installed = True
    _INSTALLED = True
