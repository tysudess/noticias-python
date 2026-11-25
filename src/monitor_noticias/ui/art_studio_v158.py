from __future__ import annotations

"""V158 — tipografia expressiva e formatação segura de trechos de texto.

Adiciona realce de texto, tachado, sobrescrito/subscrito e predefinições
profissionais de tipografia ao editor existente. As alterações são aplicadas
via QTextCursor/QTextCharFormat, preservando os trechos formatados que não
foram selecionados. Cada operação entra no histórico e no autosave V157.
"""

from PySide6.QtGui import QColor, QBrush, QFont, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QColorDialog, QComboBox, QPushButton, QToolButton, QGraphicsTextItem
from PySide6.QtCore import Qt

from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave


_TEXT_PRESETS = {
    "Título": {"size": 64, "weight": QFont.Weight.Bold.value, "italic": False},
    "Subtítulo": {"size": 42, "weight": QFont.Weight.DemiBold.value, "italic": False},
    "Corpo": {"size": 28, "weight": QFont.Weight.Normal.value, "italic": False},
    "Legenda": {"size": 18, "weight": QFont.Weight.Normal.value, "italic": False},
    "Destaque": {"size": 34, "weight": QFont.Weight.Bold.value, "italic": True},
}


def _selected_text(page) -> QGraphicsTextItem | None:
    selected = list(page.scene.selectedItems())
    if len(selected) != 1 or not isinstance(selected[0], QGraphicsTextItem):
        return None
    return selected[0]


def _editable_text(page) -> QGraphicsTextItem | None:
    item = _selected_text(page)
    if item is None:
        page.status_label.setText("Selecione uma única caixa de texto para usar as ferramentas tipográficas.")
        return None
    if bool(item.data(LOCKED_KEY)) or not item.isVisible():
        page.status_label.setText("Desbloqueie e mostre a camada de texto antes de editá-la.")
        return None
    return item


def _commit_text_format(page, char_format: QTextCharFormat, message: str) -> bool:
    item = _editable_text(page)
    if item is None:
        return False

    cursor = item.textCursor()
    had_selection = cursor.hasSelection()
    if not had_selection:
        cursor.select(QTextCursor.SelectionType.Document)
    cursor.mergeCharFormat(char_format)
    item.setTextCursor(cursor)
    item.update()
    page.scene.update()

    history_timer = getattr(page, "_v145_history_timer", None)
    if history_timer is not None and not getattr(page, "_v145_history_suspended", False):
        history_timer.start()
    _schedule_autosave(page)
    page.status_label.setText(message)
    return True


def _choose_highlight(page) -> None:
    item = _editable_text(page)
    if item is None:
        return
    current = item.textCursor().charFormat().background().color()
    if not current.isValid() or current.alpha() == 0:
        current = QColor("#FFF0A6")
    color = QColorDialog.getColor(current, page, "Cor de realce do texto")
    if not color.isValid():
        return
    fmt = QTextCharFormat()
    fmt.setBackground(QBrush(color))
    _commit_text_format(page, fmt, f"Realce {color.name()} aplicado ao texto selecionado.")
    button = getattr(page, "v158_highlight_button", None)
    if button is not None:
        button.setStyleSheet(
            f"QToolButton {{background:{color.name()};color:#17212B;border:1px solid #D6B66D;border-radius:6px;padding:4px 8px;}}"
        )


def _clear_highlight(page) -> None:
    fmt = QTextCharFormat()
    # Limpa somente o fundo; negrito, itálico, cor e demais propriedades continuam intactos.
    fmt.clearProperty(QTextFormat.Property.BackgroundBrush)
    _commit_text_format(page, fmt, "Realce removido; as demais formatações foram preservadas.")
    button = getattr(page, "v158_highlight_button", None)
    if button is not None:
        button.setStyleSheet("")


def _set_strike(page, enabled: bool) -> None:
    fmt = QTextCharFormat()
    fmt.setFontStrikeOut(bool(enabled))
    _commit_text_format(
        page,
        fmt,
        "Tachado aplicado ao texto." if enabled else "Tachado removido do texto.",
    )


def _set_vertical_alignment(page, mode: str) -> None:
    mapping = {
        "normal": QTextCharFormat.VerticalAlignment.AlignNormal,
        "super": QTextCharFormat.VerticalAlignment.AlignSuperScript,
        "sub": QTextCharFormat.VerticalAlignment.AlignSubScript,
    }
    value = mapping.get(mode)
    if value is None:
        return
    fmt = QTextCharFormat()
    fmt.setVerticalAlignment(value)
    labels = {"normal": "posição normal", "super": "sobrescrito", "sub": "subscrito"}
    _commit_text_format(page, fmt, f"Formatação {labels[mode]} aplicada.")


def _apply_preset(page) -> None:
    combo = getattr(page, "v158_preset_combo", None)
    if combo is None:
        return
    preset_name = str(combo.currentData() or "")
    preset = _TEXT_PRESETS.get(preset_name)
    if preset is None:
        return
    fmt = QTextCharFormat()
    fmt.setFontFamily("Segoe UI")
    fmt.setFontPixelSize(float(preset["size"]))
    fmt.setFontWeight(int(preset["weight"]))
    fmt.setFontItalic(bool(preset["italic"]))
    _commit_text_format(
        page,
        fmt,
        f"Predefinição '{preset_name}' aplicada. O alinhamento e as cores existentes foram preservados.",
    )


def _sync_text_controls(page) -> None:
    item = _selected_text(page)
    controls = [
        getattr(page, "v158_strike_button", None),
        getattr(page, "v158_preset_combo", None),
        getattr(page, "v158_apply_preset_button", None),
        getattr(page, "v158_highlight_button", None),
        getattr(page, "v158_clear_highlight_button", None),
        getattr(page, "v158_super_button", None),
        getattr(page, "v158_sub_button", None),
        getattr(page, "v158_normal_button", None),
    ]
    enabled = bool(
        item is not None
        and item.isVisible()
        and not bool(item.data(LOCKED_KEY))
    )
    for control in controls:
        if control is not None:
            control.setEnabled(enabled)
    if item is not None and getattr(page, "v158_strike_button", None) is not None:
        button = page.v158_strike_button
        current = item.textCursor().charFormat().fontStrikeOut()
        button.blockSignals(True)
        button.setChecked(bool(current))
        button.blockSignals(False)


def _install_typography_controls(page) -> None:
    # Extende a barra de texto criada pela V147 sem recriá-la.
    toolbar = getattr(page, "v147_text_toolbar", None)
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None or getattr(page, "_v158_typography_installed", False):
        return

    page.v158_preset_combo = QComboBox(toolbar)
    page.v158_preset_combo.setObjectName("artStudioTextPresetV158")
    page.v158_preset_combo.setMinimumWidth(118)
    page.v158_preset_combo.setMaximumWidth(140)
    page.v158_preset_combo.setToolTip("Predefinições de tamanho e peso tipográfico")
    for name in _TEXT_PRESETS:
        page.v158_preset_combo.addItem(name, name)
    layout.addWidget(page.v158_preset_combo)

    page.v158_apply_preset_button = QPushButton("Aplicar")
    page.v158_apply_preset_button.setObjectName("artStudioApplyTextPresetV158")
    page.v158_apply_preset_button.setProperty("secondary", True)
    page.v158_apply_preset_button.setToolTip("Aplicar a predefinição ao trecho selecionado ou ao texto inteiro")
    layout.addWidget(page.v158_apply_preset_button)

    page.v158_highlight_button = QToolButton(toolbar)
    page.v158_highlight_button.setObjectName("artStudioTextHighlightV158")
    page.v158_highlight_button.setText("Realce")
    page.v158_highlight_button.setToolTip("Escolher cor de fundo para o trecho selecionado")
    page.v158_highlight_button.setCursor(Qt.CursorShape.PointingHandCursor)
    layout.addWidget(page.v158_highlight_button)

    page.v158_clear_highlight_button = QToolButton(toolbar)
    page.v158_clear_highlight_button.setObjectName("artStudioClearHighlightV158")
    page.v158_clear_highlight_button.setText("×")
    page.v158_clear_highlight_button.setToolTip("Remover somente o realce, preservando as demais formatações")
    layout.addWidget(page.v158_clear_highlight_button)

    page.v158_strike_button = QToolButton(toolbar)
    page.v158_strike_button.setObjectName("artStudioStrikeV158")
    page.v158_strike_button.setText("S̶")
    page.v158_strike_button.setCheckable(True)
    page.v158_strike_button.setToolTip("Tachado")
    layout.addWidget(page.v158_strike_button)

    page.v158_super_button = QToolButton(toolbar)
    page.v158_super_button.setObjectName("artStudioSuperscriptV158")
    page.v158_super_button.setText("x²")
    page.v158_super_button.setToolTip("Sobrescrito")
    layout.addWidget(page.v158_super_button)

    page.v158_sub_button = QToolButton(toolbar)
    page.v158_sub_button.setObjectName("artStudioSubscriptV158")
    page.v158_sub_button.setText("x₂")
    page.v158_sub_button.setToolTip("Subscrito")
    layout.addWidget(page.v158_sub_button)

    page.v158_normal_button = QToolButton(toolbar)
    page.v158_normal_button.setObjectName("artStudioNormalBaselineV158")
    page.v158_normal_button.setText("x")
    page.v158_normal_button.setToolTip("Voltar à linha normal")
    layout.addWidget(page.v158_normal_button)

    page.v158_apply_preset_button.clicked.connect(lambda: _apply_preset(page))
    page.v158_highlight_button.clicked.connect(lambda: _choose_highlight(page))
    page.v158_clear_highlight_button.clicked.connect(lambda: _clear_highlight(page))
    page.v158_strike_button.toggled.connect(lambda value: _set_strike(page, value))
    page.v158_super_button.clicked.connect(lambda: _set_vertical_alignment(page, "super"))
    page.v158_sub_button.clicked.connect(lambda: _set_vertical_alignment(page, "sub"))
    page.v158_normal_button.clicked.connect(lambda: _set_vertical_alignment(page, "normal"))

    page.scene.selectionChanged.connect(lambda: _sync_text_controls(page))
    page._v158_typography_installed = True
    _sync_text_controls(page)


def enhance_art_studio_page_v158(page) -> None:
    if getattr(page, "_v158_installed", False):
        return
    _install_typography_controls(page)
    if not getattr(page, "_v158_typography_installed", False):
        return
    page._v158_installed = True


def install_art_studio_v158() -> None:
    """Instala as ferramentas tipográficas depois da recuperação automática V157."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v158_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v158(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v158(page)

    MainWindow.__init__ = init_with_v158
    MainWindow._v158_integration_installed = True
