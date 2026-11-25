from __future__ import annotations

"""Compatibilidade de atalhos V149 com enums do PySide6/Qt 6.

Algumas versões de PySide6 não permitem int(Qt.KeyboardModifier.*), mas
expõem o valor inteiro pelo atributo .value. Esta camada substitui apenas a
montagem dos atalhos V149 e mantém os mesmos comandos e combinações.
"""


def _enum_to_int(value) -> int:
    """Converte enums Qt e inteiros sem depender de __int__ do enum."""
    raw = getattr(value, "value", value)
    return int(raw)


def _install_shortcuts_compatible(page) -> None:
    """Versão compatível do instalador de atalhos da V149."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QAction, QKeySequence

    from monitor_noticias.ui.art_studio_v149 import _nudge_selected

    shortcuts = (
        ("Mover objeto para esquerda", Qt.Key.Key_Left, -1, 0),
        ("Mover objeto para direita", Qt.Key.Key_Right, 1, 0),
        ("Mover objeto para cima", Qt.Key.Key_Up, 0, -1),
        ("Mover objeto para baixo", Qt.Key.Key_Down, 0, 1),
        ("Mover objeto 10 px para esquerda", Qt.Key.Key_Left, -10, 0, Qt.KeyboardModifier.ShiftModifier),
        ("Mover objeto 10 px para direita", Qt.Key.Key_Right, 10, 0, Qt.KeyboardModifier.ShiftModifier),
        ("Mover objeto 10 px para cima", Qt.Key.Key_Up, 0, -10, Qt.KeyboardModifier.ShiftModifier),
        ("Mover objeto 10 px para baixo", Qt.Key.Key_Down, 0, 10, Qt.KeyboardModifier.ShiftModifier),
    )
    for spec in shortcuts:
        label, key, dx, dy, *modifiers = spec
        modifier_value = _enum_to_int(modifiers[0]) if modifiers else 0
        sequence = QKeySequence(_enum_to_int(key) | modifier_value)
        action = QAction(label, page)
        action.setShortcut(sequence)
        action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(
            lambda _checked=False, x=dx, y=dy: _nudge_selected(page, x, y)
        )
        page.addAction(action)

    duplicate_action = QAction("Duplicar objeto", page)
    duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
    duplicate_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    duplicate_action.triggered.connect(lambda _checked=False: page.duplicate_selected())
    page.addAction(duplicate_action)


def install_art_studio_v149_shortcut_compatibility() -> None:
    """Aplica o ajuste antes da criação da janela e da instalação da V149."""
    from monitor_noticias.ui import art_studio_v149

    if getattr(art_studio_v149, "_shortcut_enum_compat_installed", False):
        return
    art_studio_v149._install_shortcuts = _install_shortcuts_compatible
    art_studio_v149._shortcut_enum_compat_installed = True
