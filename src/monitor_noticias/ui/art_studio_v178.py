from __future__ import annotations

"""V178 — compatibilidade da barra contextual da V175.

Corrige a ordem de criação dos botões: a V175 tentava obter
page.v175_context_toolbar antes de atribuir esse atributo. A V178 usa o
widget pai do próprio layout, que já existe durante a montagem da barra.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton


_INSTALLED = False


def install_art_studio_v178() -> None:
    """Instala a correção antes da criação da MainWindow."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import art_studio_v175

    if getattr(art_studio_v175, "_v178_context_toolbar_parent_fixed", False):
        _INSTALLED = True
        return

    def add_context_button(
        page,
        layout,
        label: str,
        key: str,
        *,
        danger: bool = False,
    ):
        # O layout foi criado com QHBoxLayout(frame), portanto seu parentWidget
        # já é o frame correto. Não dependemos de um atributo da página ainda
        # não definido pela V175.
        parent = layout.parentWidget() or page
        button = QToolButton(parent)
        button.setObjectName(
            "artStudioContextDangerV175"
            if danger
            else "artStudioContextActionV175"
        )
        button.setText(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.clicked.connect(
            lambda _checked=False, action=key:
                art_studio_v175._context_action(page, action)
        )
        layout.addWidget(button)
        return button

    art_studio_v175._add_context_button = add_context_button
    art_studio_v175._v178_context_toolbar_parent_fixed = True
    _INSTALLED = True
