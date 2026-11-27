from __future__ import annotations

"""Correção de desempenho da etapa V176 do Estúdio de Artes.

A V175 já aplica a folha de estilos completa ao editor. A folha usada nesse
momento já contém o complemento visual V176, pois os wrappers de tema são
instalados antes da criação da janela. Reaplicar page.setStyleSheet() durante
a V176 força o Qt a recalcular o estilo de toda a árvore de widgets pela
segunda vez. Aqui preservamos os ajustes locais da V176, mas eliminamos essa
reaplicação global redundante e medimos cada subetapa.
"""

import logging
import time
from functools import wraps

from PySide6.QtWidgets import QFrame, QLabel, QPushButton

log = logging.getLogger(__name__)
_INSTALLED = False


def _install_visual_refinements_without_theme_rebuild(page) -> None:
    """Executa os refinamentos locais sem reconstruir a folha de estilo global."""
    started = time.perf_counter()
    log.info("[ArtStudioV176] INÍCIO ajustes visuais locais (tema global preservado).")
    try:
        # Não chamar v176._apply_theme(page): a V175 já aplicou a folha
        # completa que contém o stylesheet acrescentado pela V176.
        toolbar = page.findChild(QFrame, "artStudioToolbar")
        if toolbar is not None:
            toolbar.setMinimumHeight(48)
            toolbar.setMaximumHeight(54)
            layout = toolbar.layout()
            if layout is not None:
                layout.setContentsMargins(8, 5, 8, 5)
                layout.setSpacing(5)

        for button in page.findChildren(QPushButton):
            if button.objectName() in {
                "artStudioApplyTransformV172",
                "artStudioDeleteLayersV170",
            }:
                button.setMinimumHeight(30)
                button.setMaximumHeight(34)

        workspace = page.findChild(QFrame, "artStudioWorkspace")
        if workspace is not None:
            workspace.setContentsMargins(5, 5, 5, 5)

        for heading in page.findChildren(QLabel, "artPanelTitle"):
            heading.setStyleSheet(
                "border-bottom:1px solid palette(mid); padding-bottom:7px;"
            )
    finally:
        elapsed = time.perf_counter() - started
        log.info(
            "[ArtStudioV176] FIM ajustes visuais locais em %.3fs.", elapsed
        )
        if elapsed >= 0.5:
            log.warning(
                "[ArtStudioV176] Ajustes visuais locais demoraram %.3fs.", elapsed
            )


def _timed(original, label: str):
    @wraps(original)
    def measured(page, *args, **kwargs):
        started = time.perf_counter()
        log.info("[ArtStudioV176] INÍCIO %s.", label)
        try:
            return original(page, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - started
            log.info("[ArtStudioV176] FIM %s em %.3fs.", label, elapsed)
            if elapsed >= 0.5:
                log.warning(
                    "[ArtStudioV176] %s demorou %.3fs.", label, elapsed
                )

    return measured


def install_art_studio_v176_performance_patch() -> None:
    """Instala a correção antes de a fila do editor executar a V176."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import art_studio_v176 as v176

    if getattr(v176, "_central_v176_performance_patch", False):
        _INSTALLED = True
        return

    v176._install_visual_refinements = _install_visual_refinements_without_theme_rebuild
    v176._install_page_overview = _timed(
        v176._install_page_overview, "visão geral de páginas"
    )
    v176._install_inspector_summary = _timed(
        v176._install_inspector_summary, "resumo contextual"
    )
    v176._central_v176_performance_patch = True
    _INSTALLED = True
    log.info(
        "[ArtStudioV176] Correção de desempenho instalada: tema global não será reaplicado."
    )
