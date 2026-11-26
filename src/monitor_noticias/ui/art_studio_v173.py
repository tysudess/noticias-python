from __future__ import annotations

"""V173 — alças diretas de transformação, rotação no canvas e estilo de formas."""

import math
import weakref

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPen, QTransform
from PySide6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY
from monitor_noticias.ui.art_studio_v148 import RESIZE_HANDLE_KEY, _move_item_by_scene_delta
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.art_studio_v154 import _schedule_history
from monitor_noticias.ui.art_studio_canvas_engine_v173 import (
    normalize_stroke_style,
    normalize_stroke_width,
    resized_rect,
    rotation_delta,
    snap_rotation,
    uniform_scale_factor,
)


_HANDLE_ROLE = 17301
_DIRECTION_ROLE = 17302
_KIND_ROLE = 17303
_MIN_SHAPE_SIZE = 16.0
_INSTALLED = False


def _inside_scene(item, page) -> bool:
    try:
        return item.scene() is page.scene
    except RuntimeError:
        return False


def _has_locked_child(item) -> bool:
    stack = list(item.childItems())
    while stack:
        child = stack.pop()
        if child.data(FRAME_CHILD_KEY):
            continue
        try:
            if bool(child.data(LOCKED_KEY)):
                return True
            stack.extend(child.childItems())
        except RuntimeError:
            continue
    return False


def _target_is_editable(item, page) -> bool:
    try:
        if (
            not _inside_scene(item, page)
            or not item.isVisible()
            or bool(item.data(LOCKED_KEY))
            or bool(item.data(FRAME_CHILD_KEY))
            or item.data(ITEM_KIND_KEY) == "canvas-background"
        ):
            return False
        if isinstance(item, QGraphicsItemGroup) and _has_locked_child(item):
            return False
        if isinstance(item, QGraphicsTextItem):
            if item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
                return False
        return isinstance(
            item,
            (QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsRectItem,
             QGraphicsEllipseItem, QGraphicsItemGroup),
        )
    except RuntimeError:
        return False


def _move_scene(item: QGraphicsItem, delta: QPointF) -> None:
    if delta.isNull():
        return
    parent = item.parentItem()
    if parent is None:
        item.setPos(item.pos() + delta)
        return
    origin = parent.mapFromScene(QPointF(0.0, 0.0))
    target = parent.mapFromScene(delta)
    item.setPos(item.pos() + target - origin)


def _preserve_anchor(item: QGraphicsItem, anchor_local: QPointF, anchor_scene: QPointF) -> None:
    current = item.mapToScene(anchor_local)
    _move_scene(item, anchor_scene - current)


def _custom_handles(item):
    return [child for child in item.childItems() if child.data(_HANDLE_ROLE)]


def _position_custom_handles(item) -> None:
    rect = item.rect() if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)) else item.boundingRect()
    for handle in _custom_handles(item):
        kind = handle.data(_KIND_ROLE)
        direction = handle.data(_DIRECTION_ROLE)
        if kind == "rotate":
            handle.setPos(rect.center().x(), rect.top() - 30.0)
            continue
        if kind == "rotate-line":
            handle.setPos(rect.center().x(), rect.top())
            handle.setLine(0.0, 0.0, 0.0, -23.0)
            continue
        dx, dy = direction
        x = rect.left() if dx < 0 else rect.right() if dx > 0 else rect.center().x()
        y = rect.top() if dy < 0 else rect.bottom() if dy > 0 else rect.center().y()
        handle.setPos(x, y)


class _DirectResizeHandle(QGraphicsRectItem):
    def __init__(self, target: QGraphicsItem, direction: tuple[int, int], page):
        super().__init__(QPointF(-5.5, -5.5).x(), QPointF(-5.5, -5.5).y(), 11.0, 11.0, target)
        self._page_ref = weakref.ref(page)
        self._direction = direction
        self._start_rect = target.rect() if isinstance(target, (QGraphicsRectItem, QGraphicsEllipseItem)) else target.boundingRect()
        self._start_inverse = QTransform()
        self._anchor_local = QPointF()
        self._anchor_scene = QPointF()
        self._start_scale = float(target.scale())
        self._start_width = 0.0
        self.setData(_HANDLE_ROLE, True)
        self.setData(_DIRECTION_ROLE, direction)
        self.setData(_KIND_ROLE, "resize")
        self.setData(RESIZE_HANDLE_KEY, True)
        self.setData(FRAME_CHILD_KEY, True)
        self.setBrush(QBrush(QColor("#FFFFFF")))
        self.setPen(QPen(QColor("#168E98"), 1.6))
        self.setZValue(20000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if direction[0] and direction[1] else Qt.CursorShape.SizeHorCursor if direction[0] else Qt.CursorShape.SizeVerCursor)

    def mousePressEvent(self, event) -> None:
        target = self.parentItem()
        if target is None:
            event.ignore()
            return
        transform = target.sceneTransform()
        inverse, invertible = transform.inverted()
        if not invertible:
            event.ignore()
            return
        self._start_inverse = inverse
        self._start_rect = target.rect() if isinstance(target, (QGraphicsRectItem, QGraphicsEllipseItem)) else target.boundingRect()
        self._start_scale = float(target.scale())
        dx, dy = self._direction
        if isinstance(target, QGraphicsTextItem):
            self._start_width = target.textWidth()
            if self._start_width <= 0:
                self._start_width = self._start_rect.width()
            self._anchor_local = QPointF(self._start_width if dx < 0 else 0.0, 0.0)
        else:
            ax = self._start_rect.right() if dx < 0 else self._start_rect.left() if dx > 0 else self._start_rect.center().x()
            ay = self._start_rect.bottom() if dy < 0 else self._start_rect.top() if dy > 0 else self._start_rect.center().y()
            self._anchor_local = QPointF(ax, ay)
        self._anchor_scene = target.mapToScene(self._anchor_local)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        target = self.parentItem()
        page = self._page_ref()
        if target is None or page is None or not _target_is_editable(target, page):
            event.ignore()
            return
        local = self._start_inverse.map(event.scenePos())
        dx, dy = self._direction

        if isinstance(target, QGraphicsTextItem):
            width = self._start_rect.width()
            pointer_delta = local.x() - (self._start_rect.left() if dx < 0 else self._start_rect.right())
            new_width = self._start_width - pointer_delta if dx < 0 else self._start_width + pointer_delta
            target.setTextWidth(max(40.0, min(12000.0, new_width)))
            _preserve_anchor(target, self._anchor_local, self._anchor_scene)
        elif isinstance(target, (QGraphicsRectItem, QGraphicsEllipseItem)):
            rect = self._start_rect
            new_rect = resized_rect(
                (rect.left(), rect.top(), rect.width(), rect.height()),
                (local.x(), local.y()),
                self._direction,
                minimum=_MIN_SHAPE_SIZE,
                keep_ratio=False,
            )
            target.setRect(*new_rect)
            _preserve_anchor(target, self._anchor_local, self._anchor_scene)
        else:
            # Imagens e grupos mantêm proporção ao serem redimensionados pelo canto.
            if not (dx and dy):
                event.ignore()
                return
            factor = uniform_scale_factor(
                (self._start_rect.left(), self._start_rect.top(), self._start_rect.width(), self._start_rect.height()),
                (local.x(), local.y()),
                self._direction,
                minimum_factor=0.05,
                maximum_factor=8.0 / max(0.001, self._start_scale),
            )
            target.setScale(self._start_scale * factor)
            _preserve_anchor(target, self._anchor_local, self._anchor_scene)

        _position_custom_handles(target)
        page._v148_update_dimensions()
        page.scene.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        page = self._page_ref()
        if page is not None:
            _schedule_history(page)
            _schedule_autosave(page)
            _position_custom_handles(self.parentItem())
            page.status_label.setText("Tamanho do objeto ajustado diretamente no canvas.")
        event.accept()


class _RotationHandle(QGraphicsEllipseItem):
    def __init__(self, target: QGraphicsItem, page):
        super().__init__(-6.5, -6.5, 13.0, 13.0, target)
        self._page_ref = weakref.ref(page)
        self.setData(_HANDLE_ROLE, True)
        self.setData(_KIND_ROLE, "rotate")
        self.setData(RESIZE_HANDLE_KEY, True)
        self.setData(FRAME_CHILD_KEY, True)
        self.setBrush(QBrush(QColor("#D6B66D")))
        self.setPen(QPen(QColor("#14283A"), 1.5))
        self.setZValue(20001)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._center_local = QPointF()
        self._center_scene = QPointF()
        self._start_rotation = 0.0
        self._start_vector = QPointF()

    def mousePressEvent(self, event) -> None:
        target = self.parentItem()
        if target is None:
            event.ignore()
            return
        self._center_local = target.boundingRect().center()
        self._center_scene = target.mapToScene(self._center_local)
        # Fixa o pivô no centro visual, compensando a alteração de origem.
        before = QPointF(self._center_scene)
        target.setTransformOriginPoint(self._center_local)
        _preserve_anchor(target, self._center_local, before)
        self._center_scene = target.mapToScene(self._center_local)
        self._start_rotation = float(target.rotation())
        self._start_vector = event.scenePos() - self._center_scene
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        target = self.parentItem()
        page = self._page_ref()
        if target is None or page is None or not _target_is_editable(target, page):
            event.ignore()
            return
        current_vector = event.scenePos() - self._center_scene
        delta = rotation_delta((self._start_vector.x(), self._start_vector.y()), (current_vector.x(), current_vector.y()))
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta = snap_rotation(delta, 15.0)
        center = QPointF(self._center_scene)
        target.setRotation(self._start_rotation + delta)
        _preserve_anchor(target, self._center_local, center)
        _position_custom_handles(target)
        page.scene.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        page = self._page_ref()
        if page is not None:
            _schedule_history(page)
            _schedule_autosave(page)
            QTimer.singleShot(0, page._v148_sync_handles)
            page.status_label.setText("Rotação ajustada diretamente no canvas. Use Shift para incrementos de 15°.")
        event.accept()


def _remove_custom_handles(page) -> None:
    for handle in list(getattr(page, "_v173_handles", [])):
        try:
            if handle.scene() is page.scene:
                page.scene.removeItem(handle)
        except RuntimeError:
            pass
    page._v173_handles = []


def _install_canvas_handles(page) -> None:
    if getattr(page, "_v173_canvas_handles_installed", False):
        return
    original_sync = page._v148_sync_handles

    def sync_extended_handles():
        # Reutiliza a lógica estável V148 e então amplia para formas e grupos.
        original_sync()
        _remove_custom_handles(page)
        selected = list(page.scene.selectedItems())
        if len(selected) != 1:
            return
        item = selected[0]
        if not _target_is_editable(item, page):
            return
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            directions = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
        elif isinstance(item, QGraphicsItemGroup):
            directions = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        else:
            directions = []
        for direction in directions:
            handle = _DirectResizeHandle(item, direction, page)
            page._v173_handles.append(handle)
        if isinstance(item, (QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsItemGroup)):
            stem = QGraphicsLineItem(0.0, 0.0, 0.0, -23.0, item)
            stem.setData(_HANDLE_ROLE, True)
            stem.setData(_KIND_ROLE, "rotate-line")
            stem.setData(FRAME_CHILD_KEY, True)
            stem.setData(RESIZE_HANDLE_KEY, True)
            stem.setPen(QPen(QColor("#50C4C6"), 1.4, Qt.PenStyle.DashLine))
            stem.setZValue(19999)
            stem.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            stem.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            page._v173_handles.append(stem)
            rotate = _RotationHandle(item, page)
            page._v173_handles.append(rotate)
        _position_custom_handles(item)

    page._v148_sync_handles = sync_extended_handles
    page._v173_sync_handles = sync_extended_handles
    page.scene.selectionChanged.connect(sync_extended_handles)
    page._v173_canvas_handles_installed = True
    QTimer.singleShot(0, sync_extended_handles)


def _shape_item(page):
    selected = [item for item in page.scene.selectedItems() if not item.data(FRAME_CHILD_KEY)]
    if len(selected) != 1:
        return None
    item = selected[0]
    if not isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
        return None
    if not _target_is_editable(item, page):
        return None
    return item


def _shape_style_config(item) -> dict:
    pen = item.pen()
    style = "solid"
    if pen.style() == Qt.PenStyle.DashLine:
        style = "dash"
    elif pen.style() == Qt.PenStyle.DotLine:
        style = "dot"
    return {
        "fill": item.brush().color(),
        "stroke": pen.color(),
        "stroke_width": normalize_stroke_width(pen.widthF()),
        "stroke_style": style,
        "stroke_enabled": pen.style() != Qt.PenStyle.NoPen and pen.widthF() > 0,
    }


def _apply_shape_style(page) -> None:
    item = _shape_item(page)
    if item is None:
        page.v173_shape_hint.setText("Selecione um retângulo ou elipse desbloqueado no canvas.")
        return
    fill = page.v173_fill_color
    stroke = page.v173_stroke_color
    pen = QPen(stroke)
    pen.setWidthF(normalize_stroke_width(page.v173_stroke_width.value()))
    pen.setStyle({"solid": Qt.PenStyle.SolidLine, "dash": Qt.PenStyle.DashLine, "dot": Qt.PenStyle.DotLine}[normalize_stroke_style(page.v173_stroke_style.currentData())])
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    if not page.v173_stroke_enabled.isChecked() or pen.widthF() <= 0:
        pen.setStyle(Qt.PenStyle.NoPen)
    item.setBrush(QBrush(fill))
    item.setPen(pen)
    _install_shape_serialization(page)
    page._refresh_layers()
    _schedule_history(page)
    _schedule_autosave(page)
    page.scene.update()
    page.v173_shape_hint.setText("Preenchimento e contorno aplicados à forma selecionada.")
    page.status_label.setText("Estilo da forma atualizado.")


def _choose_shape_color(page, target: str) -> None:
    item = _shape_item(page)
    current = page.v173_fill_color if target == "fill" else page.v173_stroke_color
    title = "Escolher preenchimento" if target == "fill" else "Escolher contorno"
    color = QColorDialog.getColor(current, page, title, QColorDialog.ColorDialogOption.ShowAlphaChannel)
    if not color.isValid():
        return
    if target == "fill":
        page.v173_fill_color = color
        page.v173_fill_button.setText("Cor do preenchimento")
        page.v173_fill_button.setStyleSheet(f"background:{color.name(QColor.NameFormat.HexArgb)}; color:{'#14283A' if color.lightness() > 145 else '#FFFFFF'};")
    else:
        page.v173_stroke_color = color
        page.v173_stroke_button.setText("Cor do contorno")
        page.v173_stroke_button.setStyleSheet(f"background:{color.name(QColor.NameFormat.HexArgb)}; color:{'#14283A' if color.lightness() > 145 else '#FFFFFF'};")
    if item is not None:
        _apply_shape_style(page)


def _sync_shape_controls(page) -> None:
    item = _shape_item(page)
    controls = (
        page.v173_fill_button, page.v173_stroke_button, page.v173_stroke_enabled,
        page.v173_stroke_width, page.v173_stroke_style, page.v173_apply_shape_button,
    )
    for control in controls:
        control.setEnabled(item is not None)
    if item is None:
        page.v173_shape_hint.setText("As opções de forma aparecem ao selecionar um retângulo ou elipse.")
        return
    config = _shape_style_config(item)
    page.v173_fill_color = QColor(config["fill"])
    page.v173_stroke_color = QColor(config["stroke"])
    page.v173_stroke_width.blockSignals(True)
    page.v173_stroke_width.setValue(config["stroke_width"])
    page.v173_stroke_width.blockSignals(False)
    page.v173_stroke_enabled.blockSignals(True)
    page.v173_stroke_enabled.setChecked(config["stroke_enabled"])
    page.v173_stroke_enabled.blockSignals(False)
    page.v173_stroke_style.blockSignals(True)
    page.v173_stroke_style.setCurrentIndex(max(0, page.v173_stroke_style.findData(config["stroke_style"])))
    page.v173_stroke_style.blockSignals(False)
    page.v173_fill_button.setStyleSheet(f"background:{page.v173_fill_color.name(QColor.NameFormat.HexArgb)}; color:{'#14283A' if page.v173_fill_color.lightness() > 145 else '#FFFFFF'};")
    page.v173_stroke_button.setStyleSheet(f"background:{page.v173_stroke_color.name(QColor.NameFormat.HexArgb)}; color:{'#14283A' if page.v173_stroke_color.lightness() > 145 else '#FFFFFF'};")
    page.v173_shape_hint.setText("Edite preenchimento, contorno e espessura sem rasterizar a forma.")


def _install_shape_serialization(page) -> None:
    if getattr(page, "_v173_shape_serialization_installed", False):
        return
    base_serialize = getattr(page, "_v146_base_serialize", None)
    base_build = getattr(page, "_v146_base_build", None)
    if not callable(base_serialize) or not callable(base_build):
        return

    def serialize_shape(item):
        data = base_serialize(item)
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            pen = item.pen()
            style = "solid" if pen.style() == Qt.PenStyle.SolidLine else "dash" if pen.style() == Qt.PenStyle.DashLine else "dot" if pen.style() == Qt.PenStyle.DotLine else "none"
            data["v173_shape_stroke"] = {
                "color": pen.color().name(QColor.NameFormat.HexArgb),
                "width": normalize_stroke_width(pen.widthF()),
                "style": style,
            }
        return data

    def build_shape(data):
        item = base_build(data)
        config = data.get("v173_shape_stroke") if isinstance(data, dict) else None
        if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)) and isinstance(config, dict):
            color = QColor(str(config.get("color", "#FF17344A")))
            width = normalize_stroke_width(config.get("width", 1.0))
            style_name = normalize_stroke_style(config.get("style", "solid"))
            pen = QPen(color)
            pen.setWidthF(width)
            pen.setStyle({"solid": Qt.PenStyle.SolidLine, "dash": Qt.PenStyle.DashLine, "dot": Qt.PenStyle.DotLine}[style_name] if width > 0 else Qt.PenStyle.NoPen)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            item.setPen(pen)
        return item

    page._v173_base_serialize = base_serialize
    page._v173_base_build = base_build
    page._v146_base_serialize = serialize_shape
    page._v146_base_build = build_shape
    page._v173_shape_serialization_installed = True


def _install_shape_tab(page) -> None:
    if getattr(page, "_v173_shape_tab_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    if tabs.findChild(QWidget, "artStudioShapeTabV173") is not None:
        page._v173_shape_tab_installed = True
        return

    tab = QWidget(tabs)
    tab.setObjectName("artStudioShapeTabV173")
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(3, 3, 3, 3)
    scroll = QScrollArea(tab)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    content = QWidget(scroll)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(9, 9, 9, 12)
    layout.setSpacing(9)

    title = QLabel("ESTILO DA FORMA", content)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel("Edite formas vetoriais diretamente, preservando contornos e transparência.", content)
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(hint)

    panel = QFrame(content)
    panel.setObjectName("artStudioTransformCardV172")
    form = QFormLayout(panel)
    form.setContentsMargins(11, 11, 11, 11)
    form.setVerticalSpacing(9)
    page.v173_fill_button = QPushButton("Cor do preenchimento", panel)
    page.v173_stroke_button = QPushButton("Cor do contorno", panel)
    page.v173_stroke_enabled = QCheckBox("Ativar contorno", panel)
    page.v173_stroke_width = QDoubleSpinBox(panel)
    page.v173_stroke_width.setRange(0.0, 48.0)
    page.v173_stroke_width.setDecimals(1)
    page.v173_stroke_width.setSuffix(" px")
    page.v173_stroke_width.setKeyboardTracking(False)
    page.v173_stroke_style = QComboBox(panel)
    page.v173_stroke_style.addItem("Contínuo", "solid")
    page.v173_stroke_style.addItem("Tracejado", "dash")
    page.v173_stroke_style.addItem("Pontilhado", "dot")
    form.addRow("Preenchimento", page.v173_fill_button)
    form.addRow("Contorno", page.v173_stroke_button)
    form.addRow("Espessura", page.v173_stroke_width)
    form.addRow("Estilo", page.v173_stroke_style)
    form.addRow(page.v173_stroke_enabled)
    layout.addWidget(panel)
    page.v173_apply_shape_button = QPushButton("Aplicar estilo da forma", content)
    page.v173_apply_shape_button.setProperty("secondary", True)
    layout.addWidget(page.v173_apply_shape_button)
    page.v173_shape_hint = QLabel("As opções de forma aparecem ao selecionar um retângulo ou elipse.", content)
    page.v173_shape_hint.setObjectName("artStudioSectionHint")
    page.v173_shape_hint.setWordWrap(True)
    layout.addWidget(page.v173_shape_hint)
    layout.addStretch(1)
    scroll.setWidget(content)
    outer.addWidget(scroll)
    tabs.addTab(tab, "◧  Forma")

    page.v173_fill_color = QColor("#1677E8")
    page.v173_stroke_color = QColor("#17344A")
    page.v173_fill_button.clicked.connect(lambda: _choose_shape_color(page, "fill"))
    page.v173_stroke_button.clicked.connect(lambda: _choose_shape_color(page, "stroke"))
    page.v173_apply_shape_button.clicked.connect(lambda: _apply_shape_style(page))
    for control in (page.v173_stroke_enabled, page.v173_stroke_width, page.v173_stroke_style):
        signal = control.toggled if isinstance(control, QCheckBox) else control.valueChanged if isinstance(control, QDoubleSpinBox) else control.currentIndexChanged
        signal.connect(lambda *_args: _apply_shape_style(page) if _shape_item(page) else None)
    page.scene.selectionChanged.connect(lambda: _sync_shape_controls(page))
    page.v173_shape_tab = tab
    page._v173_shape_tab_installed = True
    _sync_shape_controls(page)


def enhance_art_studio_page_v173(page) -> None:
    if getattr(page, "_v173_installed", False):
        return
    _install_shape_serialization(page)
    _install_canvas_handles(page)
    _install_shape_tab(page)
    page._v173_installed = True
    page.status_label.setText(
        "V173: alças vetoriais para formas e grupos, rotação direta no canvas e preenchimento/contorno editáveis."
    )


def install_art_studio_v173() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v173_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v173(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v173(page)

    MainWindow.__init__ = init_with_v173
    MainWindow._v173_integration_installed = True
    _INSTALLED = True
