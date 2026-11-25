from __future__ import annotations

"""V149 — inspetor de posição, acabamento de formas e atalhos de precisão.

Esta camada amplia V143–V148 sem substituir os módulos anteriores. Mantém a
compatibilidade dos projetos .centralart e usa apenas componentes Qt existentes.
"""

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QBrush, QKeySequence, QPen
from PySide6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY

STROKE_DATA_KEY = 26


def _selected_item(page):
    selected = page.scene.selectedItems()
    return selected[0] if len(selected) == 1 else None


def _schedule_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()


def _panel_content(page):
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    return scroll.widget() if scroll is not None else None


def _shape_item(item) -> bool:
    return isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)) and not bool(
        item.data(LOCKED_KEY)
    )


def _sync_position_controls(page) -> None:
    item = _selected_item(page)
    enabled = item is not None and not bool(item.data(LOCKED_KEY))
    page.v149_x_spin.setEnabled(enabled)
    page.v149_y_spin.setEnabled(enabled)
    page.v149_apply_position_button.setEnabled(enabled)
    if item is None:
        return
    page.v149_x_spin.blockSignals(True)
    page.v149_y_spin.blockSignals(True)
    page.v149_x_spin.setValue(float(item.pos().x()))
    page.v149_y_spin.setValue(float(item.pos().y()))
    page.v149_x_spin.blockSignals(False)
    page.v149_y_spin.blockSignals(False)


def _apply_position(page) -> None:
    item = _selected_item(page)
    if item is None or bool(item.data(LOCKED_KEY)):
        return
    item.setPos(float(page.v149_x_spin.value()), float(page.v149_y_spin.value()))
    page.status_label.setText(
        f"Posição aplicada: X {page.v149_x_spin.value():.0f} px · "
        f"Y {page.v149_y_spin.value():.0f} px."
    )
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    _schedule_history(page)
    page.scene.update()


def _sync_shape_controls(page) -> None:
    item = _selected_item(page)
    enabled = _shape_item(item)
    page.v149_fill_button.setEnabled(enabled)
    page.v149_outline_button.setEnabled(enabled)
    page.v149_outline_width_spin.setEnabled(enabled)
    if not enabled:
        page.v149_fill_button.setText("Preenchimento")
        page.v149_outline_button.setText("Contorno")
        return
    fill = item.brush().color()
    pen = item.pen()
    page.v149_fill_button.setText(f"Preenchimento · {fill.name().upper()}")
    page.v149_outline_button.setText(
        "Sem contorno" if pen.style() == Qt.PenStyle.NoPen
        else f"Contorno · {pen.color().name().upper()}"
    )
    page.v149_outline_width_spin.blockSignals(True)
    page.v149_outline_width_spin.setValue(
        0 if pen.style() == Qt.PenStyle.NoPen else max(1, round(pen.widthF()))
    )
    page.v149_outline_width_spin.blockSignals(False)


def _choose_fill(page) -> None:
    item = _selected_item(page)
    if not _shape_item(item):
        return
    current = item.brush().color()
    color = QColorDialog.getColor(current, page, "Cor de preenchimento")
    if not color.isValid():
        return
    item.setBrush(QBrush(color))
    _sync_shape_controls(page)
    _schedule_history(page)
    page.scene.update()


def _choose_outline(page) -> None:
    item = _selected_item(page)
    if not _shape_item(item):
        return
    current_pen = item.pen()
    current = current_pen.color() if current_pen.style() != Qt.PenStyle.NoPen else QColor("#D6B66D")
    color = QColorDialog.getColor(current, page, "Cor do contorno")
    if not color.isValid():
        return
    width = max(1, int(page.v149_outline_width_spin.value()))
    item.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    _sync_shape_controls(page)
    _schedule_history(page)
    page.scene.update()


def _apply_outline_width(page, value: int) -> None:
    item = _selected_item(page)
    if not _shape_item(item):
        return
    if int(value) <= 0:
        item.setPen(QPen(Qt.PenStyle.NoPen))
    else:
        pen = item.pen()
        color = pen.color() if pen.style() != Qt.PenStyle.NoPen else QColor("#D6B66D")
        item.setPen(QPen(color, int(value), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    _sync_shape_controls(page)
    _schedule_history(page)
    page.scene.update()


def _nudge_selected(page, dx: float, dy: float) -> bool:
    selected = list(page.scene.selectedItems())
    if not selected:
        return False
    # Não intercepta setas enquanto o cursor está dentro de um texto em edição.
    focus_item = page.scene.focusItem()
    if isinstance(focus_item, QGraphicsTextItem) and focus_item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        return False
    selected = [item for item in selected if not bool(item.data(LOCKED_KEY))]
    selected = [
        item for item in selected
        if not any(item is not parent and parent.isAncestorOf(item) for parent in selected)
    ]
    if not selected:
        return False
    for item in selected:
        parent = item.parentItem()
        if parent is None:
            item.moveBy(dx, dy)
        else:
            origin = parent.mapFromScene(QPointF(0, 0))
            target = parent.mapFromScene(QPointF(dx, dy))
            item.moveBy(target.x() - origin.x(), target.y() - origin.y())
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    _sync_position_controls(page)
    _schedule_history(page)
    page.scene.update()
    return True


def _install_position_panel(page) -> None:
    content = _panel_content(page)
    layout = content.layout() if content is not None else None
    if layout is None:
        return
    frame = QFrame(content)
    frame.setObjectName("artStudioPositionPanel")
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(5)
    title = QLabel("POSIÇÃO DO OBJETO")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(4)
    page.v149_x_spin = QDoubleSpinBox()
    page.v149_y_spin = QDoubleSpinBox()
    for spin in (page.v149_x_spin, page.v149_y_spin):
        spin.setRange(-20000.0, 20000.0)
        spin.setDecimals(1)
        spin.setSuffix(" px")
        spin.setSingleStep(1.0)
    form.addRow("Horizontal (X)", page.v149_x_spin)
    form.addRow("Vertical (Y)", page.v149_y_spin)
    box.addLayout(form)
    page.v149_apply_position_button = QPushButton("Aplicar posição")
    page.v149_apply_position_button.setProperty("secondary", True)
    box.addWidget(page.v149_apply_position_button)
    page.v149_apply_position_button.clicked.connect(lambda: _apply_position(page))
    index = layout.indexOf(getattr(page, "v148_size_frame", None))
    layout.insertWidget(index + 1 if index >= 0 else 0, frame)


def _install_shape_style_panel(page) -> None:
    content = _panel_content(page)
    layout = content.layout() if content is not None else None
    if layout is None:
        return
    frame = QFrame(content)
    frame.setObjectName("artStudioShapeStylePanel")
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(5)
    title = QLabel("APARÊNCIA DA FORMA")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    page.v149_fill_button = QPushButton("Preenchimento")
    page.v149_outline_button = QPushButton("Contorno")
    for button in (page.v149_fill_button, page.v149_outline_button):
        button.setProperty("secondary", True)
    page.v149_outline_width_spin = QSpinBox()
    page.v149_outline_width_spin.setRange(0, 48)
    page.v149_outline_width_spin.setSuffix(" px")
    page.v149_outline_width_spin.setToolTip("Use 0 para remover o contorno")
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.addRow("Espessura", page.v149_outline_width_spin)
    box.addWidget(page.v149_fill_button)
    box.addWidget(page.v149_outline_button)
    box.addLayout(form)
    page.v149_fill_button.clicked.connect(lambda: _choose_fill(page))
    page.v149_outline_button.clicked.connect(lambda: _choose_outline(page))
    page.v149_outline_width_spin.valueChanged.connect(lambda value: _apply_outline_width(page, value))
    index = layout.indexOf(getattr(page, "v148_size_frame", None))
    layout.insertWidget(index + 2 if index >= 0 else layout.count(), frame)
    page.v149_shape_style_frame = frame


def _install_shortcuts(page) -> None:
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
        sequence = QKeySequence(int(key) | (int(modifiers[0]) if modifiers else 0))
        action = QAction(label, page)
        action.setShortcut(sequence)
        action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(lambda _checked=False, x=dx, y=dy: _nudge_selected(page, x, y))
        page.addAction(action)

    duplicate_action = QAction("Duplicar objeto", page)
    duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
    duplicate_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    duplicate_action.triggered.connect(lambda: page.duplicate_selected())
    page.addAction(duplicate_action)


def _install_selection_observers(page) -> None:
    page.scene.selectionChanged.connect(lambda: _sync_position_controls(page))
    page.scene.selectionChanged.connect(lambda: _sync_shape_controls(page))
    page.layers.currentItemChanged.connect(lambda *_args: _sync_position_controls(page))
    page.layers.currentItemChanged.connect(lambda *_args: _sync_shape_controls(page))


def _install_shape_style_persistence(page) -> None:
    # O serializador-base do V146 é utilizado também para objetos dentro de grupos.
    base_serialize = page._v146_base_serialize
    def serialize_with_outline(item):
        data = base_serialize(item)
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            pen = item.pen()
            data["v149_outline"] = {
                "enabled": pen.style() != Qt.PenStyle.NoPen,
                "color": pen.color().name(QColor.NameFormat.HexArgb),
                "width": float(pen.widthF()),
            }
        return data
    page._v146_base_serialize = serialize_with_outline

    base_build = page._v146_base_build
    def build_with_outline(data):
        item = base_build(data)
        outline = data.get("v149_outline")
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)) and isinstance(outline, dict):
            if not bool(outline.get("enabled", False)):
                item.setPen(QPen(Qt.PenStyle.NoPen))
            else:
                color = QColor(str(outline.get("color", "#FFD6B66D")))
                width = max(0.5, min(48.0, float(outline.get("width", 2.0))))
                item.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        return item
    page._v146_base_build = build_with_outline


def enhance_art_studio_page_v149(page) -> None:
    if getattr(page, "_v149_installed", False):
        return
    page._v149_installed = True
    _install_shape_style_persistence(page)
    _install_position_panel(page)
    _install_shape_style_panel(page)
    _install_shortcuts(page)
    _install_selection_observers(page)

    page.v149_sync_controls = lambda: (_sync_position_controls(page), _sync_shape_controls(page))
    page.status_label.setText(
        "V149: ajuste X/Y em pixels, aplique preenchimento e contorno às formas, "
        "use as setas para mover objetos (Shift = 10 px) e Ctrl+D para duplicar."
    )


def install_art_studio_v149() -> None:
    """Instala a camada V149 depois da criação do Estúdio V148."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v149_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v149(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v149(page)

    MainWindow.__init__ = init_with_v149
    MainWindow._v149_integration_installed = True
