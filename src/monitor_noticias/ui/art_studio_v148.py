from __future__ import annotations

"""V148 — redimensionamento, ajustes precisos e proteção de objetos.

A camada preserva os formatos .centralart de V143–V147 e usa somente Qt/Pillow
já presentes na Central. Objetos adicionados não substituem os que já existem.
"""

import logging
import uuid
from copy import deepcopy

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPen, QTransform
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY
from monitor_noticias.ui.art_studio_v147 import InlineTextItem

log = logging.getLogger(__name__)

RESIZE_HANDLE_KEY = 23
TRANSFORM_DATA_KEY = 24


def _item_id(item: QGraphicsItem) -> str:
    value = item.data(HISTORY_ID_KEY)
    if not value:
        value = uuid.uuid4().hex
        item.setData(HISTORY_ID_KEY, value)
    return str(value)


def _capture_existing_objects(page) -> list[dict]:
    """Snapshot dos objetos antes de adicionar algo; inclui grupos e HTML."""
    snapshots: list[dict] = []
    for item in list(page._content_items()):
        try:
            data = deepcopy(page._serialize_item(item))
        except Exception:
            log.exception("Não foi possível criar proteção para um objeto do Estúdio")
            continue
        data["history_id"] = _item_id(item)
        snapshots.append(data)
    return snapshots


def _restore_missing_objects(page, snapshots: list[dict]) -> int:
    present = {_item_id(item) for item in page._content_items()}
    restored = 0
    for data in snapshots:
        key = str(data.get("history_id") or "")
        if not key or key in present:
            continue
        try:
            item = page._build_item_from_data(data)
            item.setData(HISTORY_ID_KEY, key)
            page.scene.addItem(item)
            present.add(key)
            restored += 1
        except Exception:
            log.exception("Falha ao restaurar uma camada durante a inclusão de novo objeto")
    if restored:
        page._refresh_layers()
        page.status_label.setText(
            f"Novo objeto adicionado. {restored} camada(s) anterior(es) foram preservadas."
        )
    return restored


def _scene_delta_to_parent(item: QGraphicsItem, delta: QPointF) -> QPointF:
    parent = item.parentItem()
    if parent is None:
        return delta
    origin = parent.mapFromScene(QPointF(0, 0))
    target = parent.mapFromScene(delta)
    return target - origin


def _move_item_by_scene_delta(item: QGraphicsItem, delta: QPointF) -> None:
    if delta.isNull():
        return
    parent = item.parentItem()
    if parent is None:
        item.setPos(item.pos() + delta)
    else:
        origin = parent.mapFromScene(QPointF(0, 0))
        target = parent.mapFromScene(delta)
        item.setPos(item.pos() + (target - origin))


class _ResizeHandle(QGraphicsRectItem):
    """Alça de canto para imagem e alça lateral para largura do texto."""

    def __init__(self, target: QGraphicsItem, direction: tuple[int, int], page) -> None:
        super().__init__(QRectF(-6, -6, 12, 12), target)
        self._direction = direction
        self._page = page
        self._start_scene = QPointF()
        self._start_local = QPointF()
        self._start_scale = 1.0
        self._start_width = 0.0
        self._start_rect = QRectF()
        self._anchor_scene = QPointF()
        self.setData(RESIZE_HANDLE_KEY, True)
        # V146 omite filhos com esta marca ao serializar grupos.
        self.setData(FRAME_CHILD_KEY, True)
        self.setBrush(QBrush(QColor("#FFFFFF")))
        self.setPen(QPen(QColor("#1677E8"), 2))
        self.setZValue(10000)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        target = self.parentItem()
        if target is None or bool(target.data(LOCKED_KEY)):
            event.ignore()
            return
        self._start_scene = QPointF(event.scenePos())
        self._start_local = target.mapFromScene(self._start_scene)
        self._start_scale = float(target.scale())
        self._start_rect = QRectF(target.boundingRect())
        if isinstance(target, QGraphicsTextItem):
            self._start_width = float(target.textWidth())
            if self._start_width <= 0:
                self._start_width = float(target.boundingRect().width())
            anchor_x = self._start_width if self._direction[0] < 0 else 0.0
            self._anchor_scene = target.mapToScene(QPointF(anchor_x, 0))
        else:
            anchor_x = self._start_rect.right() if self._direction[0] < 0 else self._start_rect.left()
            anchor_y = self._start_rect.bottom() if self._direction[1] < 0 else self._start_rect.top()
            self._anchor_scene = target.mapToScene(QPointF(anchor_x, anchor_y))
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        target = self.parentItem()
        if target is None:
            event.ignore()
            return

        if isinstance(target, QGraphicsTextItem):
            current_local = target.mapFromScene(event.scenePos())
            delta_x = current_local.x() - self._start_local.x()
            new_width = max(40.0, min(12000.0, self._start_width + self._direction[0] * delta_x))
            anchor_x = new_width if self._direction[0] < 0 else 0.0
            target.setTextWidth(new_width)
            new_anchor = target.mapToScene(QPointF(anchor_x, 0))
            _move_item_by_scene_delta(target, self._anchor_scene - new_anchor)
        elif isinstance(target, QGraphicsPixmapItem):
            delta = QPointF(event.scenePos()) - self._start_scene
            scene_rect = target.mapRectToScene(self._start_rect)
            width = max(1.0, scene_rect.width())
            height = max(1.0, scene_rect.height())
            factor_x = 1.0 + self._direction[0] * delta.x() / width
            factor_y = 1.0 + self._direction[1] * delta.y() / height
            factor = max(0.05, min(8.0 / max(0.001, self._start_scale), factor_x, factor_y))
            # Para os cantos, usa o eixo que mais se afastou, mantendo proporção.
            factor = max(0.05, min(8.0 / max(0.001, self._start_scale), max(factor_x, factor_y)))
            anchor_x = self._start_rect.right() if self._direction[0] < 0 else self._start_rect.left()
            anchor_y = self._start_rect.bottom() if self._direction[1] < 0 else self._start_rect.top()
            target.setScale(self._start_scale * factor)
            new_anchor = target.mapToScene(QPointF(anchor_x, anchor_y))
            _move_item_by_scene_delta(target, self._anchor_scene - new_anchor)

        self._page._v148_sync_handles()
        self._page._v148_update_dimensions()
        self._page._v148_schedule_history()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._page._v148_sync_handles()
        self._page._v148_update_dimensions()
        self._page._v148_schedule_history()
        event.accept()


def _remove_handles(page) -> None:
    for handle in list(getattr(page, "_v148_handles", [])):
        try:
            if handle.scene() is page.scene:
                page.scene.removeItem(handle)
        except RuntimeError:
            pass
    page._v148_handles = []


def _position_handles(item: QGraphicsItem) -> None:
    rect = item.boundingRect()
    handles = [child for child in item.childItems() if child.data(RESIZE_HANDLE_KEY)]
    for handle in handles:
        dx, dy = handle.data(25)
        if isinstance(item, QGraphicsTextItem):
            handle.setPos(rect.left() if dx < 0 else rect.right(), rect.center().y())
        else:
            x = rect.left() if dx < 0 else rect.right()
            y = rect.top() if dy < 0 else rect.bottom()
            handle.setPos(x, y)


def _sync_resize_handles(page) -> None:
    _remove_handles(page)
    selected = list(page.scene.selectedItems())
    if len(selected) != 1:
        return
    item = selected[0]
    if not item.isVisible() or bool(item.data(LOCKED_KEY)):
        return
    if isinstance(item, InlineTextItem) and item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        return
    if isinstance(item, QGraphicsTextItem):
        directions = [(-1, 0), (1, 0)]
    elif isinstance(item, QGraphicsPixmapItem):
        directions = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    else:
        return
    for direction in directions:
        handle = _ResizeHandle(item, direction, page)
        handle.setData(25, direction)
        page._v148_handles.append(handle)
    _position_handles(item)


def _update_dimension_controls(page) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    image = isinstance(item, QGraphicsPixmapItem)
    text = isinstance(item, QGraphicsTextItem)
    page.v148_size_frame.setVisible(bool(image or text))
    page.v148_width_spin.setEnabled(bool(image or text) and not (item is not None and bool(item.data(LOCKED_KEY))))
    page.v148_height_spin.setVisible(bool(image))
    page.v148_height_label.setVisible(bool(image))
    page.v148_ratio_check.setVisible(bool(image))
    page.v148_flip_h_button.setVisible(bool(image))
    page.v148_flip_v_button.setVisible(bool(image))
    if not (image or text):
        return
    page.v148_width_spin.blockSignals(True)
    page.v148_height_spin.blockSignals(True)
    if image:
        transformed = item.transform().mapRect(item.boundingRect())
        width = max(1, round(transformed.width() * abs(item.scale())))
        height = max(1, round(transformed.height() * abs(item.scale())))
        page.v148_width_spin.setValue(width)
        page.v148_height_spin.setValue(height)
    else:
        width = item.textWidth()
        if width <= 0:
            width = item.boundingRect().width()
        page.v148_width_spin.setValue(max(1, round(width)))
    page.v148_width_spin.blockSignals(False)
    page.v148_height_spin.blockSignals(False)
    page.v148_apply_size_button.setEnabled(not bool(item.data(LOCKED_KEY)))


def _update_height_from_width(page, value: int) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    if not isinstance(item, QGraphicsPixmapItem) or not page.v148_ratio_check.isChecked():
        return
    pixmap = item.pixmap()
    if pixmap.width() <= 0:
        return
    height = max(1, round(value * pixmap.height() / pixmap.width()))
    page.v148_height_spin.blockSignals(True)
    page.v148_height_spin.setValue(height)
    page.v148_height_spin.blockSignals(False)


def _apply_dimensions(page) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    if item is None or bool(item.data(LOCKED_KEY)):
        return
    width = max(1, int(page.v148_width_spin.value()))
    if isinstance(item, QGraphicsTextItem):
        item.setTextWidth(float(width))
        page.status_label.setText(f"Largura da caixa de texto ajustada para {width} px.")
    elif isinstance(item, QGraphicsPixmapItem):
        pixmap = item.pixmap()
        if pixmap.width() <= 0 or pixmap.height() <= 0:
            return
        height = max(1, int(page.v148_height_spin.value()))
        if page.v148_ratio_check.isChecked():
            factor = width / float(pixmap.width())
            item.setTransform(QTransform())
            item.setScale(factor)
            height = max(1, round(pixmap.height() * factor))
            page.v148_height_spin.setValue(height)
        else:
            sx = width / float(pixmap.width())
            sy = height / float(pixmap.height())
            item.setScale(1.0)
            item.setTransform(QTransform.fromScale(sx, sy))
        item.setTransformOriginPoint(item.boundingRect().center())
        page.status_label.setText(f"Imagem redimensionada para {width} × {height} px.")
    else:
        return
    page._v148_sync_handles()
    page._v148_update_dimensions()
    page._v148_schedule_history()
    page.scene.update()


def _flip_image(page, horizontal: bool) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    if not isinstance(item, QGraphicsPixmapItem) or bool(item.data(LOCKED_KEY)):
        return
    from PySide6.QtGui import QTransform
    transform = QTransform().scale(-1.0, 1.0) if horizontal else QTransform().scale(1.0, -1.0)
    item.setPixmap(item.pixmap().transformed(transform, Qt.TransformationMode.SmoothTransformation))
    item.setTransformOriginPoint(item.boundingRect().center())
    page.status_label.setText("Imagem espelhada na horizontal." if horizontal else "Imagem espelhada na vertical.")
    page._v148_sync_handles()
    page._v148_update_dimensions()
    page._v148_schedule_history()


def _install_size_panel(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    frame = QFrame(content)
    frame.setObjectName("artStudioObjectSizePanel")
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(5)
    title = QLabel("AJUSTE DE TAMANHO")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(4)
    page.v148_width_spin = QSpinBox()
    page.v148_width_spin.setRange(24, 20000)
    page.v148_width_spin.setSuffix(" px")
    page.v148_height_spin = QSpinBox()
    page.v148_height_spin.setRange(24, 20000)
    page.v148_height_spin.setSuffix(" px")
    page.v148_height_label = QLabel("Altura")
    form.addRow("Largura", page.v148_width_spin)
    form.addRow(page.v148_height_label, page.v148_height_spin)
    box.addLayout(form)
    page.v148_ratio_check = QCheckBox("Manter proporção da imagem")
    page.v148_ratio_check.setChecked(True)
    box.addWidget(page.v148_ratio_check)
    page.v148_apply_size_button = QPushButton("Aplicar tamanho")
    page.v148_apply_size_button.setProperty("secondary", True)
    box.addWidget(page.v148_apply_size_button)
    flips = QHBoxLayout()
    page.v148_flip_h_button = QPushButton("Espelhar ↔")
    page.v148_flip_v_button = QPushButton("Espelhar ↕")
    for button in (page.v148_flip_h_button, page.v148_flip_v_button):
        button.setProperty("secondary", True)
        flips.addWidget(button)
    box.addLayout(flips)
    index = layout.indexOf(page.layers)
    layout.insertWidget(index + 1, frame)
    page.v148_size_frame = frame

    page.v148_width_spin.valueChanged.connect(lambda value: _update_height_from_width(page, value))
    page.v148_apply_size_button.clicked.connect(lambda: _apply_dimensions(page))
    page.v148_flip_h_button.clicked.connect(lambda: _flip_image(page, True))
    page.v148_flip_v_button.clicked.connect(lambda: _flip_image(page, False))
    page.v148_ratio_check.toggled.connect(lambda _checked: _update_height_from_width(page, page.v148_width_spin.value()))
    _update_dimension_controls(page)


def _install_rich_text_width_control(page) -> None:
    toolbar = getattr(page, "v147_text_toolbar", None)
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return
    label = QLabel("Caixa")
    page.v148_text_width_spin = QSpinBox()
    page.v148_text_width_spin.setRange(40, 12000)
    page.v148_text_width_spin.setSuffix(" px")
    page.v148_text_width_spin.setFixedWidth(92)
    layout.insertWidget(max(1, layout.count() - 1), label)
    layout.insertWidget(max(1, layout.count() - 1), page.v148_text_width_spin)

    def apply_width(value: int) -> None:
        selected = list(page.scene.selectedItems())
        item = selected[0] if len(selected) == 1 else None
        if isinstance(item, QGraphicsTextItem):
            item.setTextWidth(float(value))
            page._v148_sync_handles()
            page._v148_schedule_history()

    page.v148_text_width_spin.valueChanged.connect(apply_width)


def _sync_text_width_control(page) -> None:
    spin = getattr(page, "v148_text_width_spin", None)
    if spin is None:
        return
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    is_text = isinstance(item, QGraphicsTextItem)
    spin.setEnabled(is_text and not bool(item.data(LOCKED_KEY)))
    spin.blockSignals(True)
    if is_text:
        width = item.textWidth() if item.textWidth() > 0 else item.boundingRect().width()
        spin.setValue(max(40, round(width)))
    spin.blockSignals(False)


def _install_safe_creation(page) -> None:
    original_build = page._build_item_from_data

    def build_with_page_reference(data):
        item = original_build(data)
        if isinstance(item, InlineTextItem):
            item._v148_page = page
        return item

    page._build_item_from_data = build_with_page_reference
    original_make_movable = page._make_movable

    def add_without_replacing_existing(item, kind, name):
        before = _capture_existing_objects(page)
        original_make_movable(item, kind, name)
        _restore_missing_objects(page, before)
        selected = list(page.scene.selectedItems())
        if selected:
            for target in selected:
                if isinstance(target, InlineTextItem):
                    target._v148_page = page
        page._v148_sync_handles()
        page._v148_update_dimensions()

    page._make_movable = add_without_replacing_existing


def _install_transform_persistence(page) -> None:
    # O formato anterior salvava scale/rotation, mas não a transformação livre
    # usada quando o usuário desmarca "Manter proporção".
    if hasattr(page, "_v146_base_serialize"):
        original_serialize = page._v146_base_serialize

        def serialize_transform(item):
            data = original_serialize(item)
            transform = item.transform()
            data["v148_transform"] = [
                float(transform.m11()), float(transform.m12()),
                float(transform.m21()), float(transform.m22()),
                float(transform.dx()), float(transform.dy()),
            ]
            origin = item.transformOriginPoint()
            data["v148_transform_origin"] = [float(origin.x()), float(origin.y())]
            return data

        page._v146_base_serialize = serialize_transform

    if hasattr(page, "_v146_base_build"):
        original_build = page._v146_base_build

        def build_transform(data):
            item = original_build(data)
            values = data.get("v148_transform")
            if isinstance(values, list) and len(values) == 6:
                item.setTransform(QTransform(*(float(value) for value in values)))
            origin = data.get("v148_transform_origin")
            if isinstance(origin, list) and len(origin) == 2:
                item.setTransformOriginPoint(QPointF(float(origin[0]), float(origin[1])))
            return item

        page._v146_base_build = build_transform


def enhance_art_studio_page_v148(page) -> None:
    if getattr(page, "_v148_installed", False):
        return
    page._v148_installed = True
    page._v148_handles = []
    page._v148_schedule_history = lambda: _schedule_history(page)
    page._v148_sync_handles = lambda: _sync_resize_handles(page)
    page._v148_update_dimensions = lambda: _update_dimension_controls(page)

    _install_transform_persistence(page)
    _install_safe_creation(page)
    _install_size_panel(page)
    _install_rich_text_width_control(page)

    original_refresh = page._refresh_layers

    def refresh_with_resize_handles(*args, **kwargs):
        original_refresh(*args, **kwargs)
        QTimer.singleShot(0, page._v148_sync_handles)
        QTimer.singleShot(0, page._v148_update_dimensions)
        QTimer.singleShot(0, lambda: _sync_text_width_control(page))

    page._refresh_layers = refresh_with_resize_handles
    page.scene.selectionChanged.connect(page._v148_sync_handles)
    page.scene.selectionChanged.connect(page._v148_update_dimensions)
    page.scene.selectionChanged.connect(lambda: _sync_text_width_control(page))

    # Enquanto o usuário digita, as alças ficam ocultas; ao sair do campo,
    # reaparecem automaticamente para redimensionar a caixa de texto.
    original_begin = InlineTextItem.begin_inline_edit
    original_focus_out = InlineTextItem.focusOutEvent

    def begin_inline_edit(self, *, select_all: bool = False):
        for child in self.childItems():
            if child.data(RESIZE_HANDLE_KEY):
                child.hide()
        return original_begin(self, select_all=select_all)

    def focus_out(self, event):
        result = original_focus_out(self, event)
        page = getattr(self, "_v148_page", None)
        if page is not None:
            QTimer.singleShot(0, page._v148_sync_handles)
        return result

    InlineTextItem.begin_inline_edit = begin_inline_edit
    InlineTextItem.focusOutEvent = focus_out

    page.status_label.setText(
        "V148: redimensione imagens pelos cantos e ajuste a largura das caixas de texto pelas laterais. "
        "As novas imagens e textos são adicionados sem substituir as camadas existentes."
    )


def install_art_studio_v148() -> None:
    """Conecta a camada V148 à página já criada pelo instalador V143–V147."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v148_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v148(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v148(page)

    MainWindow.__init__ = init_with_v148
    MainWindow._v148_integration_installed = True
