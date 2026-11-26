from __future__ import annotations

"""V167 — estúdio de tipografia profissional para textos do canvas.

Adiciona estilos tipográficos rápidos e controles precisos de família/peso,
entrelinha, espaçamento de caracteres e palavras, caixa, alinhamento, contorno
 e realce. A formatação é aplicada ao documento rico já usado pelo V147 e
continua sendo gravada no HTML dos projetos .centralart.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QKeySequence,
    QPen,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QFontComboBox,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_typography_engine_v167 import (
    normalize_typography_config,
    typography_preset,
)
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave

log = logging.getLogger(__name__)


_CAPITALIZATION = {
    "mixed": QFont.Capitalization.MixedCase,
    "upper": QFont.Capitalization.AllUppercase,
    "lower": QFont.Capitalization.AllLowercase,
    "small": QFont.Capitalization.SmallCaps,
    "capitalize": QFont.Capitalization.Capitalize,
}
_ALIGNMENT = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
    "justify": Qt.AlignmentFlag.AlignJustify,
}
_CAPITALIZATION_LABELS = {
    "Padrão": "mixed",
    "MAIÚSCULAS": "upper",
    "minúsculas": "lower",
    "Versalete": "small",
    "Iniciais Maiúsculas": "capitalize",
}
_ALIGNMENT_LABELS = {
    "Esquerda": "left",
    "Centro": "center",
    "Direita": "right",
    "Justificado": "justify",
}
_PRESET_LABELS = {
    "Manchete": "headline",
    "Subtítulo": "subtitle",
    "Texto corrido": "body",
    "Legenda": "caption",
    "Citação": "quote",
    "Realce": "highlight",
}


def _selected_editable_text(page) -> QGraphicsTextItem | None:
    selected = list(page.scene.selectedItems())
    if len(selected) != 1 or not isinstance(selected[0], QGraphicsTextItem):
        return None
    item = selected[0]
    try:
        if item.scene() is not page.scene or not item.isVisible() or bool(item.data(LOCKED_KEY)):
            return None
    except RuntimeError:
        return None
    return item


def _sync_typography_button(page) -> None:
    button = getattr(page, "v167_typography_button", None)
    if button is None:
        return
    enabled = _selected_editable_text(page) is not None
    button.setEnabled(enabled)
    button.setToolTip(
        "Abrir o estúdio de tipografia para o texto selecionado."
        if enabled else "Selecione uma única caixa de texto visível e desbloqueada."
    )


def _color_button(button, color: str, label: str) -> None:
    button.setText(label)
    button.setStyleSheet(
        "QPushButton {"
        f"background:{color}; color:{'#FFFFFF' if color.upper() in {'#102A43', '#17344A', '#315B78', '#000000'} else '#102A43'};"
        "border:1px solid #D6B66D; border-radius:6px; padding:5px 10px; min-height:28px;}"
    )


class _TypographyDialog(QDialog):
    """Janela de tipografia com alterações confirmadas somente em Aplicar."""

    def __init__(self, item: QGraphicsTextItem, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Estúdio de tipografia")
        self.setMinimumWidth(540)
        self.setModal(True)
        self._config = _config_from_item(item)
        self._result_config = dict(self._config)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QLabel("TIPOGRAFIA PROFISSIONAL", self)
        title.setObjectName("artStudioSectionHeading")
        intro = QLabel(
            "Escolha um estilo ou ajuste os detalhes. A alteração só será aplicada quando você confirmar.",
            self,
        )
        intro.setWordWrap(True)
        intro.setObjectName("artStudioSectionHint")
        root.addWidget(title)
        root.addWidget(intro)

        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox(self)
        for label, key in _PRESET_LABELS.items():
            self.preset_combo.addItem(label, key)
        self.load_preset_button = QPushButton("Carregar estilo", self)
        self.load_preset_button.setProperty("secondary", True)
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.load_preset_button)
        root.addLayout(preset_row)

        type_card = QFrame(self)
        type_card.setObjectName("artStudioTypographyCardV167")
        type_layout = QFormLayout(type_card)
        type_layout.setContentsMargins(10, 10, 10, 10)
        type_layout.setVerticalSpacing(7)

        self.font_combo = QFontComboBox(type_card)
        self.font_combo.setCurrentFont(QFont(self._config["font_family"]))
        self.font_size = QSpinBox(type_card)
        self.font_size.setRange(8, 600)
        self.font_size.setSuffix(" px")
        self.font_size.setValue(self._config["font_size"])

        self.weight_combo = QComboBox(type_card)
        for label, value in (
            ("Fino", 300), ("Regular", 400), ("Médio", 500),
            ("Seminegrito", 600), ("Negrito", 700),
            ("Extra negrito", 800), ("Preto", 900),
        ):
            self.weight_combo.addItem(label, value)
        weight_index = self.weight_combo.findData(self._config["weight"])
        self.weight_combo.setCurrentIndex(max(0, weight_index))

        self.italic = QCheckBox("Itálico", type_card)
        self.italic.setChecked(self._config["italic"])
        self.underline = QCheckBox("Sublinhado", type_card)
        self.underline.setChecked(self._config["underline"])
        style_row = QHBoxLayout()
        style_row.addWidget(self.italic)
        style_row.addWidget(self.underline)
        type_layout.addRow("Família tipográfica", self.font_combo)
        type_layout.addRow("Tamanho", self.font_size)
        type_layout.addRow("Peso", self.weight_combo)
        type_layout.addRow("Estilo", style_row)
        root.addWidget(type_card)

        spacing_card = QFrame(self)
        spacing_card.setObjectName("artStudioTypographySpacingCardV167")
        spacing_form = QFormLayout(spacing_card)
        spacing_form.setContentsMargins(10, 10, 10, 10)
        spacing_form.setVerticalSpacing(7)
        self.letter_spacing = self._double(-20, 80, 0.5, " px", self._config["letter_spacing"], spacing_card)
        self.word_spacing = self._double(-20, 150, 1, " px", self._config["word_spacing"], spacing_card)
        self.line_spacing = self._double(80, 300, 5, " %", self._config["line_spacing"], spacing_card)
        self.paragraph_spacing = self._double(0, 120, 2, " px", self._config["paragraph_spacing"], spacing_card)
        self.capitalization = QComboBox(spacing_card)
        for label in _CAPITALIZATION_LABELS:
            self.capitalization.addItem(label, _CAPITALIZATION_LABELS[label])
        self.capitalization.setCurrentIndex(max(0, self.capitalization.findData(self._config["capitalization"])))
        self.alignment = QComboBox(spacing_card)
        for label in _ALIGNMENT_LABELS:
            self.alignment.addItem(label, _ALIGNMENT_LABELS[label])
        self.alignment.setCurrentIndex(max(0, self.alignment.findData(self._config["alignment"])))
        spacing_form.addRow("Espaço entre letras", self.letter_spacing)
        spacing_form.addRow("Espaço entre palavras", self.word_spacing)
        spacing_form.addRow("Entrelinha", self.line_spacing)
        spacing_form.addRow("Espaço após parágrafo", self.paragraph_spacing)
        spacing_form.addRow("Transformação de caixa", self.capitalization)
        spacing_form.addRow("Alinhamento", self.alignment)
        root.addWidget(spacing_card)

        finish_card = QFrame(self)
        finish_card.setObjectName("artStudioTypographyFinishCardV167")
        finish_form = QFormLayout(finish_card)
        finish_form.setContentsMargins(10, 10, 10, 10)
        finish_form.setVerticalSpacing(7)

        self.text_color_enabled = QCheckBox("Aplicar cor da letra", finish_card)
        self.text_color_enabled.setChecked(self._config["use_text_color"])
        self.text_color_button = QPushButton(finish_card)
        self.text_color = self._config["text_color"]
        _color_button(self.text_color_button, self.text_color, "Escolher cor")
        text_color_row = QHBoxLayout()
        text_color_row.addWidget(self.text_color_enabled)
        text_color_row.addWidget(self.text_color_button)

        self.outline_width = self._double(0, 24, 0.5, " px", self._config["outline_width"], finish_card)
        self.outline_color_button = QPushButton(finish_card)
        self.outline_color = self._config["outline_color"]
        _color_button(self.outline_color_button, self.outline_color, "Contorno")

        self.highlight_enabled = QCheckBox("Realçar texto com fundo", finish_card)
        self.highlight_enabled.setChecked(self._config["highlight_enabled"])
        self.highlight_color_button = QPushButton(finish_card)
        self.highlight_color = self._config["highlight_color"]
        _color_button(self.highlight_color_button, self.highlight_color, "Realce")
        highlight_row = QHBoxLayout()
        highlight_row.addWidget(self.highlight_enabled)
        highlight_row.addWidget(self.highlight_color_button)

        finish_form.addRow("Cor principal", text_color_row)
        finish_form.addRow("Contorno da letra", self.outline_width)
        finish_form.addRow("Cor do contorno", self.outline_color_button)
        finish_form.addRow("Fundo do texto", highlight_row)
        root.addWidget(finish_card)

        self.load_preset_button.clicked.connect(self._load_preset)
        self.text_color_button.clicked.connect(lambda: self._choose_color("text"))
        self.outline_color_button.clicked.connect(lambda: self._choose_color("outline"))
        self.highlight_color_button.clicked.connect(lambda: self._choose_color("highlight"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar à seleção")
        buttons.accepted.connect(self._accept_config)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _double(low, high, step, suffix, value, parent):
        spin = QDoubleSpinBox(parent)
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setDecimals(1 if step < 1 else 0)
        spin.setSuffix(suffix)
        spin.setValue(float(value))
        return spin

    def _choose_color(self, key: str) -> None:
        current = {
            "text": self.text_color,
            "outline": self.outline_color,
            "highlight": self.highlight_color,
        }[key]
        selected = QColorDialog.getColor(QColor(current), self, "Escolher cor")
        if not selected.isValid():
            return
        color = selected.name(QColor.NameFormat.HexRgb).upper()
        if key == "text":
            self.text_color = color
            _color_button(self.text_color_button, color, "Escolher cor")
        elif key == "outline":
            self.outline_color = color
            _color_button(self.outline_color_button, color, "Contorno")
        else:
            self.highlight_color = color
            _color_button(self.highlight_color_button, color, "Realce")

    def _load_preset(self) -> None:
        key = str(self.preset_combo.currentData() or "body")
        config = typography_preset(key)
        self.font_combo.setCurrentFont(QFont(config["font_family"]))
        self.font_size.setValue(config["font_size"])
        weight_index = self.weight_combo.findData(config["weight"])
        self.weight_combo.setCurrentIndex(max(0, weight_index))
        self.italic.setChecked(config["italic"])
        self.underline.setChecked(config["underline"])
        self.letter_spacing.setValue(config["letter_spacing"])
        self.word_spacing.setValue(config["word_spacing"])
        self.line_spacing.setValue(config["line_spacing"])
        self.paragraph_spacing.setValue(config["paragraph_spacing"])
        self.capitalization.setCurrentIndex(max(0, self.capitalization.findData(config["capitalization"])))
        self.alignment.setCurrentIndex(max(0, self.alignment.findData(config["alignment"])))
        self.outline_width.setValue(config["outline_width"])
        self.outline_color = config["outline_color"]
        self.highlight_enabled.setChecked(config["highlight_enabled"])
        self.highlight_color = config["highlight_color"]
        self.text_color_enabled.setChecked(config["use_text_color"])
        self.text_color = config["text_color"]
        _color_button(self.outline_color_button, self.outline_color, "Contorno")
        _color_button(self.highlight_color_button, self.highlight_color, "Realce")
        _color_button(self.text_color_button, self.text_color, "Escolher cor")

    def _accept_config(self) -> None:
        font = self.font_combo.currentFont()
        self._result_config = normalize_typography_config({
            "font_family": font.family(),
            "font_size": self.font_size.value(),
            "weight": self.weight_combo.currentData(),
            "italic": self.italic.isChecked(),
            "underline": self.underline.isChecked(),
            "letter_spacing": self.letter_spacing.value(),
            "word_spacing": self.word_spacing.value(),
            "line_spacing": self.line_spacing.value(),
            "paragraph_spacing": self.paragraph_spacing.value(),
            "capitalization": self.capitalization.currentData(),
            "alignment": self.alignment.currentData(),
            "outline_width": self.outline_width.value(),
            "outline_color": self.outline_color,
            "highlight_enabled": self.highlight_enabled.isChecked(),
            "highlight_color": self.highlight_color,
            "use_text_color": self.text_color_enabled.isChecked(),
            "text_color": self.text_color,
        })
        self.accept()

    def result_config(self) -> dict:
        return dict(self._result_config)


def _config_from_item(item: QGraphicsTextItem) -> dict:
    font = item.font()
    char = item.textCursor().charFormat()
    block = item.textCursor().blockFormat()
    weight = int(char.fontWeight() or font.weight())
    capitalization = char.fontCapitalization()
    capitalization_lookup = {
        int(QFont.Capitalization.MixedCase): "mixed",
        int(QFont.Capitalization.AllUppercase): "upper",
        int(QFont.Capitalization.AllLowercase): "lower",
        int(QFont.Capitalization.SmallCaps): "small",
        int(QFont.Capitalization.Capitalize): "capitalize",
    }
    alignment = block.alignment()
    if alignment & Qt.AlignmentFlag.AlignHCenter:
        alignment_key = "center"
    elif alignment & Qt.AlignmentFlag.AlignRight:
        alignment_key = "right"
    elif alignment & Qt.AlignmentFlag.AlignJustify:
        alignment_key = "justify"
    else:
        alignment_key = "left"
    line_type = block.lineHeightType()
    proportional = line_type == QTextBlockFormat.LineHeightTypes.ProportionalHeight
    line_spacing = block.lineHeight() if proportional and block.lineHeight() > 0 else 110

    outline = char.textOutline()
    outline_enabled = outline.style() != Qt.PenStyle.NoPen and outline.widthF() > 0
    background = char.background()
    highlight_enabled = background.style() != Qt.BrushStyle.NoBrush
    foreground = char.foreground()
    use_text_color = foreground.style() != Qt.BrushStyle.NoBrush

    config = {
        "font_family": char.fontFamily() or font.family(),
        "font_size": char.fontPixelSize() or (font.pixelSize() if font.pixelSize() > 0 else 54),
        "weight": weight,
        "italic": font.italic(),
        "underline": font.underline(),
        "letter_spacing": char.fontLetterSpacing(),
        "word_spacing": char.fontWordSpacing(),
        "line_spacing": line_spacing,
        "paragraph_spacing": block.bottomMargin(),
        "capitalization": capitalization_lookup.get(int(capitalization), "mixed"),
        "alignment": alignment_key,
        "outline_width": outline.widthF() if outline_enabled else 0,
        "outline_color": outline.color().name(QColor.NameFormat.HexRgb) if outline_enabled else "#102A43",
        "highlight_enabled": highlight_enabled,
        "highlight_color": background.color().name(QColor.NameFormat.HexRgb) if highlight_enabled else "#F2D777",
        "use_text_color": use_text_color,
        "text_color": foreground.color().name(QColor.NameFormat.HexRgb) if use_text_color else "#102A43",
    }
    return normalize_typography_config(config)


def _apply_typography(page, item: QGraphicsTextItem, config_value: dict) -> bool:
    config = normalize_typography_config(config_value)
    try:
        cursor = item.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.Document)

        char_format = QTextCharFormat()
        char_format.setFontFamily(config["font_family"])
        char_format.setFontPixelSize(float(config["font_size"]))
        char_format.setFontWeight(config["weight"])
        char_format.setFontItalic(config["italic"])
        char_format.setFontUnderline(config["underline"])
        char_format.setFontLetterSpacingType(QFont.SpacingType.AbsoluteSpacing)
        char_format.setFontLetterSpacing(float(config["letter_spacing"]))
        char_format.setFontWordSpacing(float(config["word_spacing"]))
        char_format.setFontCapitalization(_CAPITALIZATION[config["capitalization"]])

        if config["outline_width"] > 0:
            char_format.setTextOutline(QPen(QColor(config["outline_color"]), config["outline_width"]))
        else:
            char_format.setTextOutline(QPen(Qt.PenStyle.NoPen))
        if config["highlight_enabled"]:
            char_format.setBackground(QBrush(QColor(config["highlight_color"])))
        else:
            char_format.setBackground(QBrush(Qt.BrushStyle.NoBrush))
        if config["use_text_color"]:
            char_format.setForeground(QBrush(QColor(config["text_color"])))

        cursor.mergeCharFormat(char_format)
        block_format = QTextBlockFormat()
        block_format.setLineHeight(
            float(config["line_spacing"]),
            QTextBlockFormat.LineHeightTypes.ProportionalHeight,
        )
        block_format.setBottomMargin(float(config["paragraph_spacing"]))
        block_format.setAlignment(_ALIGNMENT[config["alignment"]])
        cursor.mergeBlockFormat(block_format)
        item.setTextCursor(cursor)
        item.update()
        page.scene.update()
        if hasattr(page, "_refresh_layers"):
            page._refresh_layers(select_item=item)
        timer = getattr(page, "_v145_history_timer", None)
        if timer is not None and not getattr(page, "_v145_history_suspended", False):
            timer.start()
        _schedule_autosave(page)
        page.status_label.setText(
            "Tipografia aplicada ao texto selecionado. Entrelinha, espaçamentos e acabamentos foram atualizados."
        )
        return True
    except Exception as exc:
        log.exception("Falha ao aplicar tipografia avançada V167")
        page.status_label.setText(f"Não foi possível aplicar a tipografia: {exc}")
        return False


def _open_typography_dialog(page) -> None:
    item = _selected_editable_text(page)
    if item is None:
        page.status_label.setText("Selecione uma única caixa de texto visível e desbloqueada.")
        return
    dialog = _TypographyDialog(item, page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    _apply_typography(page, item, dialog.result_config())


def enhance_art_studio_page_v167(page) -> None:
    if getattr(page, "_v167_installed", False):
        return
    toolbar = getattr(page, "v147_text_toolbar", None)
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return

    page.v167_typography_button = QPushButton("Aa+ Tipografia", toolbar)
    page.v167_typography_button.setObjectName("artStudioTypographyButtonV167")
    page.v167_typography_button.setProperty("secondary", True)
    page.v167_typography_button.setToolTip("Famílias, estilos, espaçamentos, entrelinha, contorno e realce")
    page.v167_typography_button.clicked.connect(lambda: _open_typography_dialog(page))
    layout.addWidget(page.v167_typography_button)

    action = QAction("Abrir estúdio de tipografia", page)
    action.setShortcut(QKeySequence("Ctrl+Shift+T"))
    action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    action.triggered.connect(lambda _checked=False: _open_typography_dialog(page))
    page.addAction(action)
    page.scene.selectionChanged.connect(lambda: _sync_typography_button(page))
    page._v167_installed = True
    _sync_typography_button(page)
    page.status_label.setText(
        "V167: estúdio de tipografia com biblioteca de estilos, pesos, entrelinha, "
        "espaçamento de caracteres e palavras, caixa, alinhamento, contorno e realce."
    )


def install_art_studio_v167() -> None:
    """Instala a tipografia avançada após a V166."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v167_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v167(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v167(page)

    MainWindow.__init__ = init_with_v167
    MainWindow._v167_integration_installed = True
