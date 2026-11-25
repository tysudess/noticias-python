from __future__ import annotations

"""V147 — edição de texto no canvas e reorganização responsiva do Estúdio.

A camada estende V143–V146 sem reescrever os módulos anteriores. Todo o
conteúdo continua usando QGraphicsScene e os projetos .centralart existentes.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QFontComboBox,
    QGraphicsItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY, ITEM_NAME_KEY


class InlineTextItem(QGraphicsTextItem):
    """Texto que entra em edição no próprio canvas com duplo clique."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)

    def begin_inline_edit(self, *, select_all: bool = False) -> None:
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        cursor = self.textCursor()
        if select_all:
            cursor.select(QTextCursor.SelectionType.Document)
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.begin_inline_edit()
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().focusOutEvent(event)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)


def _promote_text_item(item):
    """Converte texto carregado de projetos antigos sem perder seus atributos."""
    if not isinstance(item, QGraphicsTextItem) or isinstance(item, InlineTextItem):
        return item

    replacement = InlineTextItem()
    replacement.setHtml(item.toHtml())
    replacement.setFont(item.font())
    replacement.setDefaultTextColor(item.defaultTextColor())
    replacement.setTextWidth(item.textWidth())
    replacement.setFlags(item.flags())
    replacement.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
    replacement.setTransform(item.transform())
    replacement.setTransformOriginPoint(item.transformOriginPoint())
    replacement.setPos(item.pos())
    replacement.setRotation(item.rotation())
    replacement.setScale(item.scale())
    replacement.setOpacity(item.opacity())
    replacement.setZValue(item.zValue())
    replacement.setVisible(item.isVisible())
    for key in range(0, 32):
        value = item.data(key)
        if value is not None:
            replacement.setData(key, value)
    return replacement


def _selected_text_item(page):
    selected = page.scene.selectedItems()
    item = selected[0] if selected else None
    return item if isinstance(item, QGraphicsTextItem) else None


def _schedule_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()


def _install_inline_text(page) -> None:
    # Templates também passam pelo mesmo caminho e ganham edição inline.
    original_make_movable = page._make_movable

    def make_movable_inline(item, kind, name):
        if kind == "text":
            item = _promote_text_item(item)
        original_make_movable(item, kind, name)

    page._make_movable = make_movable_inline

    # Projetos .centralart anteriores continuam abrindo; os textos antigos
    # passam a ter duplo clique para edição depois de reconstruídos.
    if hasattr(page, "_v146_base_build"):
        original_base_build = page._v146_base_build

        def base_build_inline(data):
            item = original_base_build(data)
            rich_html = data.get("html")
            if isinstance(item, QGraphicsTextItem) and rich_html:
                item.setHtml(str(rich_html))
            return _promote_text_item(item)

        page._v146_base_build = base_build_inline

    # V146 serializa os objetos de texto por meio do serializador-base. Guardar
    # também o HTML permite persistir estilos diferentes dentro do mesmo texto.
    if hasattr(page, "_v146_base_serialize"):
        original_base_serialize = page._v146_base_serialize

        def serialize_rich_text(item):
            data = original_base_serialize(item)
            if isinstance(item, QGraphicsTextItem):
                data["html"] = item.toHtml()
            return data

        page._v146_base_serialize = serialize_rich_text

    original_build = page._build_item_from_data

    def build_inline(data):
        return _promote_text_item(original_build(data))

    page._build_item_from_data = build_inline

    def add_text_inline():
        item = InlineTextItem("Digite seu texto")
        font = QFont("Segoe UI")
        font.setPixelSize(54)
        font.setBold(True)
        item.setFont(font)
        item.setDefaultTextColor(QColor("#102A43"))
        item.setTextWidth(min(page._width * 0.82, 620.0))
        bounds = item.boundingRect()
        item.setPos(
            (page._width - bounds.width()) / 2,
            (page._height - bounds.height()) / 2,
        )
        page._make_movable(item, "text", "Texto")
        item.begin_inline_edit(select_all=True)
        page.status_label.setText(
            "Digite diretamente no canvas. Clique fora do texto para concluir a edição."
        )
        _show_text_toolbar(page, item)
        _schedule_history(page)

    def begin_selected_text_edit():
        item = _selected_text_item(page)
        if item is None:
            return
        if isinstance(item, InlineTextItem):
            item.begin_inline_edit()
        else:
            item.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
            item.setFocus(Qt.FocusReason.MouseFocusReason)
            cursor = item.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            item.setTextCursor(cursor)
        page.status_label.setText("Edição de texto ativada diretamente no canvas.")
        _show_text_toolbar(page, item)

    for button, callback in (
        (page.add_text_button, add_text_inline),
        (page.edit_text_button, begin_selected_text_edit),
    ):
        try:
            button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        button.clicked.connect(callback)

    page.add_text_button.setText("T  Texto")
    page.edit_text_button.setText("Editar no canvas")
    page._v147_add_text = add_text_inline
    page._v147_begin_text_edit = begin_selected_text_edit


def _apply_text_format(page, *, font=None, bold=None, italic=None, underline=None, color=None) -> None:
    item = _selected_text_item(page)
    if item is None:
        return

    current_font = QFont(item.font())
    if font is not None:
        current_font.setFamily(font.family())
    if bold is not None:
        current_font.setBold(bool(bold))
    if italic is not None:
        current_font.setItalic(bool(italic))
    if underline is not None:
        current_font.setUnderline(bool(underline))
    size = page.v147_font_size.value()
    current_font.setPixelSize(max(8, int(size)))

    cursor = item.textCursor()
    has_text_selection = cursor.hasSelection()
    if not has_text_selection:
        cursor.select(QTextCursor.SelectionType.Document)
    char_format = QTextCharFormat()
    char_format.setFont(current_font)
    if color is not None:
        char_format.setForeground(color)
    cursor.mergeCharFormat(char_format)
    item.setTextCursor(cursor)
    if not has_text_selection:
        item.setFont(current_font)
        if color is not None:
            item.setDefaultTextColor(color)
    lines = item.toPlainText().strip().splitlines()
    item.setData(ITEM_NAME_KEY, lines[0][:40] if lines else "Texto")
    page._refresh_layers(select_item=item)
    page.status_label.setText("Formatação do texto atualizada no canvas.")
    _schedule_history(page)


def _apply_text_size(page, value: int) -> None:
    _apply_text_format(page)


def _apply_alignment(page, mode: str) -> None:
    item = _selected_text_item(page)
    if item is None:
        return
    alignment = {
        "Esquerda": Qt.AlignmentFlag.AlignLeft,
        "Centro": Qt.AlignmentFlag.AlignHCenter,
        "Direita": Qt.AlignmentFlag.AlignRight,
        "Justificado": Qt.AlignmentFlag.AlignJustify,
    }.get(mode, Qt.AlignmentFlag.AlignLeft)
    cursor = item.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    block = QTextBlockFormat()
    block.setAlignment(alignment)
    cursor.mergeBlockFormat(block)
    item.setTextCursor(cursor)
    _schedule_history(page)


def _show_text_toolbar(page, item=None) -> None:
    item = item if isinstance(item, QGraphicsTextItem) else _selected_text_item(page)
    toolbar = getattr(page, "v147_text_toolbar", None)
    if toolbar is None:
        return
    if item is None:
        toolbar.hide()
        return
    toolbar.show()
    font = item.font()
    page.v147_font_combo.blockSignals(True)
    page.v147_font_combo.setCurrentFont(font)
    page.v147_font_combo.blockSignals(False)
    page.v147_font_size.blockSignals(True)
    page.v147_font_size.setValue(max(8, font.pixelSize() if font.pixelSize() > 0 else 54))
    page.v147_font_size.blockSignals(False)
    for button, checked in (
        (page.v147_bold_button, font.bold()),
        (page.v147_italic_button, font.italic()),
        (page.v147_underline_button, font.underline()),
    ):
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)
    page.v147_color_button.setStyleSheet(
        f"background:{item.defaultTextColor().name()}; border:1px solid #D6B66D; border-radius:6px;"
    )


def _install_text_toolbar(page) -> None:
    center = page.findChild(QFrame, "artStudioWorkspace")
    layout = center.layout() if center is not None else None
    if layout is None:
        return

    toolbar = QFrame(center)
    toolbar.setObjectName("artStudioInlineTextToolbar")
    toolbar.setStyleSheet(
        "QFrame#artStudioInlineTextToolbar {background:#12273A;border:1px solid #37536B;border-radius:10px;}"
        "QToolButton,QPushButton,QComboBox,QSpinBox {min-height:30px;padding:2px 7px;}"
        "QToolButton:checked {background:#D6B66D;color:#102A43;border:1px solid #E3C77F;}"
    )
    row = QHBoxLayout(toolbar)
    row.setContentsMargins(8, 6, 8, 6)
    row.setSpacing(6)

    title = QLabel("TEXTO")
    title.setObjectName("artSmallLabel")
    row.addWidget(title)

    page.v147_font_combo = QFontComboBox()
    page.v147_font_combo.setMinimumWidth(145)
    page.v147_font_combo.setMaximumWidth(190)
    page.v147_font_size = QSpinBox()
    page.v147_font_size.setRange(8, 500)
    page.v147_font_size.setValue(54)
    page.v147_font_size.setSuffix(" px")
    page.v147_font_size.setFixedWidth(82)

    page.v147_bold_button = QToolButton()
    page.v147_bold_button.setText("B")
    page.v147_bold_button.setCheckable(True)
    page.v147_bold_button.setToolTip("Negrito")
    page.v147_bold_button.setStyleSheet("font-weight:900;")
    page.v147_italic_button = QToolButton()
    page.v147_italic_button.setText("I")
    page.v147_italic_button.setCheckable(True)
    page.v147_italic_button.setToolTip("Itálico")
    page.v147_italic_button.setStyleSheet("font-style:italic;")
    page.v147_underline_button = QToolButton()
    page.v147_underline_button.setText("U")
    page.v147_underline_button.setCheckable(True)
    page.v147_underline_button.setToolTip("Sublinhado")
    page.v147_underline_button.setStyleSheet("text-decoration:underline;")

    page.v147_color_button = QPushButton("Cor")
    page.v147_color_button.setFixedWidth(48)
    page.v147_color_button.setToolTip("Cor do texto")
    page.v147_align_combo = QComboBox()
    page.v147_align_combo.addItems(["Esquerda", "Centro", "Direita", "Justificado"])
    page.v147_align_combo.setToolTip("Alinhamento do texto")

    for widget in (
        page.v147_font_combo,
        page.v147_font_size,
        page.v147_bold_button,
        page.v147_italic_button,
        page.v147_underline_button,
        page.v147_color_button,
        page.v147_align_combo,
    ):
        row.addWidget(widget)

    page.v147_font_combo.currentFontChanged.connect(
        lambda value: _apply_text_format(page, font=value)
    )
    page.v147_font_size.valueChanged.connect(lambda value: _apply_text_size(page, value))
    page.v147_bold_button.toggled.connect(lambda value: _apply_text_format(page, bold=value))
    page.v147_italic_button.toggled.connect(lambda value: _apply_text_format(page, italic=value))
    page.v147_underline_button.toggled.connect(lambda value: _apply_text_format(page, underline=value))
    page.v147_color_button.clicked.connect(lambda: _choose_text_color(page))
    page.v147_align_combo.currentTextChanged.connect(lambda value: _apply_alignment(page, value))

    layout.insertWidget(0, toolbar)
    toolbar.hide()
    page.v147_text_toolbar = toolbar


def _choose_text_color(page) -> None:
    item = _selected_text_item(page)
    if item is None:
        return
    color = QColorDialog.getColor(item.defaultTextColor(), page, "Cor do texto")
    if color.isValid():
        _apply_text_format(page, color=color)
        _show_text_toolbar(page, item)


def _install_scrollable_layers_panel(page) -> None:
    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next(
        (label.parentWidget() for label in labels if label.text() == "CAMADAS E OBJETOS"),
        None,
    )
    layout = panel.layout() if panel is not None else None
    if layout is None or panel.property("v147Scrollable"):
        return

    # Mantém o título fixo e transfere todos os controles existentes para uma
    # área rolável. Assim V145, V146 e as propriedades não disputam altura.
    title_item = layout.takeAt(0)
    title = title_item.widget() if title_item is not None else None
    if title_item is not None:
        del title_item

    content = QWidget()
    content.setObjectName("artStudioLayersContent")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(4, 5, 4, 8)
    content_layout.setSpacing(7)

    while layout.count():
        entry = layout.takeAt(0)
        widget = entry.widget()
        child_layout = entry.layout()
        if widget is not None:
            content_layout.addWidget(widget)
        elif child_layout is not None:
            content_layout.addLayout(child_layout)
        else:
            content_layout.addItem(entry)

    layers = getattr(page, "layers", None)
    if layers is not None:
        layers.setMinimumHeight(92)
        layers.setMaximumHeight(150)
        layers.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    for button in content.findChildren(QPushButton):
        button.setMinimumHeight(max(32, button.minimumHeight()))
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    scroll = QScrollArea(panel)
    scroll.setObjectName("artStudioLayersScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(content)
    scroll.setStyleSheet(
        "QScrollArea#artStudioLayersScroll {background:transparent;border:0;}"
        "QScrollBar:vertical {width:7px;background:transparent;margin:2px;}"
        "QScrollBar::handle:vertical {background:#45647D;border-radius:3px;min-height:28px;}"
    )

    if title is not None:
        layout.addWidget(title)
    layout.addWidget(scroll, 1)
    panel.setFixedWidth(300)
    panel.setProperty("v147Scrollable", True)
    panel.setToolTip("Role o painel para acessar todas as propriedades, camadas e ferramentas.")


def _install_selection_observer(page) -> None:
    original_selection_changed = page._selection_changed

    def selection_changed_v147():
        original_selection_changed()
        _show_text_toolbar(page)

    page._selection_changed = selection_changed_v147
    # A conexão original já está registrada no scene; conectamos também um
    # observador porque o sinal guarda a referência ao método antigo.
    page.scene.selectionChanged.connect(lambda: _show_text_toolbar(page))


def enhance_art_studio_page_v147(page) -> None:
    """Ativa edição inline, barra de formatação e painel de camadas rolável."""
    if getattr(page, "_v147_installed", False):
        return
    page._v147_installed = True

    _install_inline_text(page)
    _install_text_toolbar(page)
    _install_scrollable_layers_panel(page)
    _install_selection_observer(page)

    page._v147_show_text_toolbar = lambda item=None: _show_text_toolbar(page, item)
    page.status_label.setText(
        "V147: edite textos com duplo clique no canvas. A barra de formatação aparece ao selecionar um texto; "
        "role o painel direito para acessar todas as ferramentas."
    )
