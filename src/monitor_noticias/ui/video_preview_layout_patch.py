from __future__ import annotations

import weakref

from PySide6.QtCore import QTimer


PREVIEW_MIN_HEIGHT = 360
PREVIEW_MAX_HEIGHT = 660


def preview_height_for_width(width: int) -> int:
    """Altura responsiva 16:9, limitada para caber em telas menores."""
    try:
        safe_width = max(1, int(width))
    except (TypeError, ValueError):
        safe_width = 1
    target = int(round(safe_width * 9 / 16))
    return max(PREVIEW_MIN_HEIGHT, min(PREVIEW_MAX_HEIGHT, target))


_PATCHED = False


def install_video_preview_layout_patch() -> None:
    """Amplia a prévia do editor e mantém a proporção 16:9 ao redimensionar."""
    global _PATCHED
    if _PATCHED:
        return

    from monitor_noticias.ui.video_editor_reference_page import (
        ReferenceAdvancedVideoEditorWidget,
    )

    cls = ReferenceAdvancedVideoEditorWidget
    original_style = cls._apply_reference_style
    original_resize = cls.resizeEvent

    def update_preview_height(widget) -> None:
        video = getattr(widget, "video", None)
        if video is None:
            return

        width = int(video.width())
        if width <= 1:
            # Antes da primeira exibição, estima a área de vídeo pela largura
            # do editor; o primeiro resize real recalcula a proporção.
            width = max(640, int(widget.width() * 0.72))

        height = preview_height_for_width(width)
        if (
            video.minimumHeight() != height
            or video.maximumHeight() != height
        ):
            video.setMinimumHeight(height)
            video.setMaximumHeight(height)

        # Atualiza o frame já carregado depois de o layout recalcular a altura.
        refresh = getattr(widget, "_refresh_video_pixmap", None)
        if callable(refresh):
            refresh()

    def apply_large_preview(widget) -> None:
        original_style(widget)
        video = getattr(widget, "video", None)
        if video is not None:
            # Remove os limites antigos (235–305 px) impostos pelo tema anterior.
            video.setMinimumHeight(PREVIEW_MIN_HEIGHT)
            video.setMaximumHeight(PREVIEW_MAX_HEIGHT)
        update_preview_height(widget)

    def resize_with_large_preview(widget, event) -> None:
        original_resize(widget, event)
        reference = weakref.ref(widget)

        def deferred_update(ref=reference):
            current = ref()
            if current is not None:
                update_preview_height(current)

        # Espera o Qt recalcular as larguras dos filhos antes de aplicar 16:9.
        QTimer.singleShot(0, deferred_update)

    cls._apply_reference_style = apply_large_preview
    cls.resizeEvent = resize_with_large_preview
    _PATCHED = True
