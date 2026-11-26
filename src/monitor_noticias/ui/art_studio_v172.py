from __future__ import annotations

"""V172 — inspetor de transformação, alinhamento, distribuição e atalhos de precisão."""

import math
import weakref

from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import CANVAS_BG_KEY, ITEM_KIND_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.art_studio_v154 import _schedule_history
from monitor_noticias.ui.art_studio_transform_engine_v172 import (
    alignment_delta,
    clamp_opacity,
    distribution_offsets,
    has_locked_descendant,
    proportional_size,
    selected_roots,
)


_INSTALLED = False


def _visual_stylesheet(theme: str) -> str:
    dark = theme == "escuro"
    panel = "#10263A" if dark else "#FFFFFF"
    panel_alt = "#142F45" if dark else "#F7F9FC"
    border = "#304F66" if dark else "#D4DEE7"
    text = "#F0F4F7" if dark else "#17344A"
    muted = "#9CB0C0" if dark else "#6E8293"
    accent = "#D7B56D" if dark else "#A98239"
    signal = "#50C4C6" if dark else "#168E98"
    hover = "#203F57" if dark else "#EAF0F5"
    return f"""
    QFrame#artStudioTransformCardV172 {{ background:{panel}; border:1px solid {border}; border-radius:10px; }}
    QLabel#artStudioSelectionInfoV172 {{ background:{panel_alt}; color:{text}; border:1px solid {border}; border-radius:7px; padding:8px 9px; font-weight:800; }}
    QScrollArea#artStudioTransformScrollV172 {{ background:transparent; border:0; }}
    QSlider::groove:horizontal {{ height:5px; background:{border}; border-radius:2px; }}
    QSlider::sub-page:horizontal {{ background:{signal}; border-radius:2px; }}
    QSlider::handle:horizontal {{ width:14px; margin:-5px 0; background:{accent}; border:1px solid {panel}; border-radius:7px; }}
    QPushButton#artStudioApplyTransformV172 {{ background:{accent}; color:{'#14283A' if dark else '#FFFFFF'}; border:1px solid {accent}; font-weight:900; }}
    QPushButton#artStudioApplyTransformV172:hover {{ background:{signal}; border-color:{signal}; color:#FFFFFF; }}
    QPushButton[secondary="true"]:hover {{ border-color:{signal}; background:{hover}; }}
    QLabel#artStudioSectionHint {{ color:{muted}; }}
    """


def _wrap_v171_skin() -> None:
    try:
        from monitor_noticias.ui import art_studio_v161
    except Exception:
        return
    if getattr(art_studio_v161, "_v172_skin_extension_installed", False):
        return
    original = art_studio_v161._skin_stylesheet

    def stylesheet_with_v172(theme: str) -> str:
        return original(theme) + _visual_stylesheet(theme)

    art_studio_v161._skin_stylesheet = stylesheet_with_v172
    art_studio_v161._v172_skin_extension_installed = True


def _is_in_scene(item, page) -> bool:
    try:
        return item.scene() is page.scene
    except RuntimeError:
        return False


def _eligible_selection(page) -> list:
    try:
        raw = list(page.scene.selectedItems())
    except RuntimeError:
        return []
    roots = selected_roots(raw, lambda item: item.parentItem())
    result = []
    for item in roots:
        try:
            if (
                _is_in_scene(item, page)
                and item.isVisible()
                and not bool(item.data(LOCKED_KEY))
                and item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
                and not has_locked_descendant(
                    item,
                    children_of=lambda candidate: candidate.childItems(),
                    is_locked=lambda candidate: bool(candidate.data(LOCKED_KEY)),
                )
            ):
                result.append(item)
        except RuntimeError:
            continue
    return result


def _bounds(items) -> tuple[float, float, float, float] | None:
    rect = None
    for item in items:
        try:
            candidate = item.sceneBoundingRect()
            rect = candidate if rect is None else rect.united(candidate)
        except RuntimeError:
            continue
    if rect is None or rect.isEmpty():
        return None
    return float(rect.left()), float(rect.top()), float(rect.width()), float(rect.height())


def _preserve_scene_center(item) -> None:
    before = item.sceneBoundingRect().center()
    item.setTransformOriginPoint(item.boundingRect().center())
    after = item.sceneBoundingRect().center()
    _move_scene(item, before.x() - after.x(), before.y() - after.y())


def _move_scene(item, dx: float, dy: float) -> None:
    """Move um QGraphicsItem por vetor em coordenadas de cena, mesmo com pai."""
    delta = QPointF(float(dx), float(dy))
    parent = item.parentItem()
    if parent is None:
        item.setPos(item.pos() + delta)
        return
    origin = item.mapToScene(QPointF(0.0, 0.0))
    before = parent.mapFromScene(origin)
    after = parent.mapFromScene(origin + delta)
    item.setPos(item.pos() + (after - before))


def _matrix_values(item) -> list[float]:
    transform = item.transform()
    return [
        float(transform.m11()), float(transform.m12()), float(transform.m13()),
        float(transform.m21()), float(transform.m22()), float(transform.m23()),
        float(transform.m31()), float(transform.m32()), float(transform.m33()),
    ]


def _serialize_transform_tree(item, data: dict) -> None:
    """Preserva transformações locais não contempladas pelo formato legado."""
    from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY

    data["v172_local_transform"] = _matrix_values(item)
    origin = item.transformOriginPoint()
    data["v172_transform_origin"] = [float(origin.x()), float(origin.y())]
    children_data = data.get("children")
    if isinstance(children_data, list):
        children = [child for child in item.childItems() if not child.data(FRAME_CHILD_KEY)]
        for child, child_data in zip(children, children_data):
            if isinstance(child_data, dict):
                _serialize_transform_tree(child, child_data)


def _restore_transform_tree(item, data: dict) -> None:
    """Restaura matriz e pivô após o construtor legado recriar o objeto."""
    from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY

    matrix = data.get("v172_local_transform")
    if isinstance(matrix, (list, tuple)) and len(matrix) == 9:
        try:
            values = [float(value) for value in matrix]
            if all(math.isfinite(value) for value in values):
                item.setTransform(QTransform(*values), False)
        except (TypeError, ValueError, RuntimeError):
            pass
    origin = data.get("v172_transform_origin")
    if isinstance(origin, (list, tuple)) and len(origin) == 2:
        try:
            x, y = float(origin[0]), float(origin[1])
            if math.isfinite(x) and math.isfinite(y):
                item.setTransformOriginPoint(QPointF(x, y))
        except (TypeError, ValueError, RuntimeError):
            pass
    children_data = data.get("children")
    if isinstance(children_data, list):
        children = [child for child in item.childItems() if not child.data(FRAME_CHILD_KEY)]
        for child, child_data in zip(children, children_data):
            if isinstance(child_data, dict):
                _restore_transform_tree(child, child_data)


def _install_transform_serialization(page) -> None:
    if getattr(page, "_v172_transform_serialization_installed", False):
        return
    base_serialize = getattr(page, "_serialize_item", None)
    base_build = getattr(page, "_build_item_from_data", None)
    if not callable(base_serialize) or not callable(base_build):
        return

    def serialize_with_local_transform(item):
        data = base_serialize(item)
        if isinstance(data, dict):
            _serialize_transform_tree(item, data)
        return data

    def build_with_local_transform(data):
        item = base_build(data)
        if isinstance(data, dict):
            _restore_transform_tree(item, data)
        return item

    page._v172_base_serialize = base_serialize
    page._v172_base_build = base_build
    page._serialize_item = serialize_with_local_transform
    page._build_item_from_data = build_with_local_transform
    page._v172_transform_serialization_installed = True


def _touch_document(page, message: str) -> None:
    try:
        _schedule_history(page)
        _schedule_autosave(page)
    except (AttributeError, RuntimeError):
        pass
    if hasattr(page, "_refresh_layers"):
        page._refresh_layers()
    for name in ("_v148_sync_handles", "_v148_update_dimensions", "_v149_sync_controls"):
        callback = getattr(page, name, None)
        if callable(callback):
            try:
                callback()
            except RuntimeError:
                pass
    page.status_label.setText(message)


def _input_has_focus(page, widget: QWidget | None) -> bool:
    if widget is not None and isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
        return True
    if isinstance(widget, QComboBox) and widget.isEditable():
        return True
    try:
        from PySide6.QtWidgets import QGraphicsTextItem
        focused_item = page.scene.focusItem()
        if (
            isinstance(focused_item, QGraphicsTextItem)
            and focused_item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction
        ):
            return True
    except RuntimeError:
        return True
    return False


class _NudgeFilter(QObject):
    """Setas movem objetos em passos de 1/10 px somente com o canvas em foco."""

    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):  # noqa: N802 - assinatura Qt
        page = self._page_ref()
        if page is None or event.type() != QEvent.Type.KeyPress:
            return False
        if event.key() not in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            return False
        view = getattr(page, "view", None)
        viewport = view.viewport() if view is not None else None
        focus = page.focusWidget()
        if focus not in (view, viewport) or _input_has_focus(page, focus):
            return False
        items = _eligible_selection(page)
        if not items:
            return False
        step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0
        dx = -step if event.key() == Qt.Key.Key_Left else step if event.key() == Qt.Key.Key_Right else 0.0
        dy = -step if event.key() == Qt.Key.Key_Up else step if event.key() == Qt.Key.Key_Down else 0.0
        for item in items:
            _move_scene(item, dx, dy)
        _touch_document(page, f"{len(items)} objeto(s) movido(s) {step:g} px.")
        event.accept()
        return True


def _spin(parent, suffix=" px", minimum=-50000.0, maximum=50000.0, decimals=1):
    control = QDoubleSpinBox(parent)
    control.setRange(minimum, maximum)
    control.setDecimals(decimals)
    control.setSingleStep(1.0)
    control.setSuffix(suffix)
    control.setKeyboardTracking(False)
    control.setMinimumWidth(90)
    return control


def _card(parent, title: str):
    frame = QFrame(parent)
    frame.setObjectName("artStudioTransformCardV172")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 9, 10, 10)
    layout.setSpacing(7)
    label = QLabel(title.upper(), frame)
    label.setObjectName("artStudioSectionHeading")
    layout.addWidget(label)
    return frame, layout


def _sync_transform_controls(page) -> None:
    controls = getattr(page, "v172_transform_controls", None)
    if not controls:
        return
    items = _eligible_selection(page)
    bounds = _bounds(items)
    multiple = len(items) > 1
    page.v172_selection_info.setText(
        "Nenhum objeto selecionado" if not items else
        (f"{len(items)} objetos selecionados" if multiple else "1 objeto selecionado")
    )
    page.v172_position_x.setEnabled(bool(items))
    page.v172_position_y.setEnabled(bool(items))
    page.v172_rotation.setEnabled(bool(items))
    page.v172_opacity.setEnabled(bool(items))
    page.v172_width.setEnabled(len(items) == 1)
    page.v172_height.setEnabled(len(items) == 1)
    page.v172_keep_ratio.setEnabled(len(items) == 1)
    page.v172_apply_button.setEnabled(bool(items))
    page.v172_flip_h.setEnabled(bool(items))
    page.v172_flip_v.setEnabled(bool(items))
    page.v172_center_button.setEnabled(bool(items))
    page.v172_align_buttons_enabled(bool(items))
    page.v172_distribute_h.setEnabled(len(items) >= 3)
    page.v172_distribute_v.setEnabled(len(items) >= 3)
    if bounds is None:
        page.v172_dimensions_note.setText("Selecione objetos desbloqueados para editar as medidas.")
        return

    x, y, width, height = bounds
    values = (
        (page.v172_position_x, x),
        (page.v172_position_y, y),
    )
    for control, value in values:
        control.blockSignals(True)
        control.setValue(value)
        control.blockSignals(False)
    if len(items) == 1:
        item = items[0]
        rect = item.sceneBoundingRect()
        page.v172_width.blockSignals(True)
        page.v172_height.blockSignals(True)
        page.v172_width.setValue(max(1.0, rect.width()))
        page.v172_height.setValue(max(1.0, rect.height()))
        page.v172_width.blockSignals(False)
        page.v172_height.blockSignals(False)
        page.v172_rotation.blockSignals(True)
        page.v172_rotation.setValue(float(item.rotation()))
        page.v172_rotation.blockSignals(False)
        page.v172_opacity.blockSignals(True)
        page.v172_opacity.setValue(round(item.opacity() * 100))
        page.v172_opacity.blockSignals(False)
        page.v172_dimensions_note.setText(f"Dimensão atual · {rect.width():.0f} × {rect.height():.0f} px")
    else:
        page.v172_dimensions_note.setText(
            f"Seleção combinada · {width:.0f} × {height:.0f} px · tamanho individual disponível com um objeto"
        )
        page.v172_rotation.blockSignals(True)
        page.v172_rotation.setValue(0.0)
        page.v172_rotation.blockSignals(False)
        page.v172_opacity.blockSignals(True)
        page.v172_opacity.setValue(100)
        page.v172_opacity.blockSignals(False)


def _apply_transform(page) -> None:
    items = _eligible_selection(page)
    if not items:
        page.v172_dimensions_note.setText("Selecione um objeto desbloqueado para transformar.")
        return
    bounds = _bounds(items)
    if bounds is None:
        return
    x, y, _width, _height = bounds
    dx = float(page.v172_position_x.value()) - x
    dy = float(page.v172_position_y.value()) - y
    requested_rotation = float(page.v172_rotation.value())
    opacity = clamp_opacity(page.v172_opacity.value())

    # A seleção múltipla gira como uma composição ao redor do centro comum;
    # um objeto isolado recebe o ângulo absoluto informado no inspetor.
    if len(items) > 1 and abs(requested_rotation) > 1e-6:
        current = _bounds(items)
        origin_x = current[0] + current[2] / 2.0
        origin_y = current[1] + current[3] / 2.0
        angle = math.radians(requested_rotation)
        cosine, sine = math.cos(angle), math.sin(angle)
    else:
        origin_x = origin_y = 0.0
        cosine, sine = 1.0, 0.0

    for item in items:
        try:
            _preserve_scene_center(item)
            _move_scene(item, dx, dy)
            if len(items) == 1:
                current = item.sceneBoundingRect()
                target_width, target_height = proportional_size(
                    current.width(), current.height(),
                    page.v172_width.value(), page.v172_height.value(),
                    keep_ratio=page.v172_keep_ratio.isChecked(),
                    changed_axis=getattr(page, "_v172_last_size_axis", "width"),
                )
                sx = max(0.01, min(100.0, target_width / max(1.0, current.width())))
                sy = max(0.01, min(100.0, target_height / max(1.0, current.height())))
                center_before = item.mapToScene(item.boundingRect().center())
                item.setTransform(QTransform().scale(sx, sy), True)
                center_after = item.mapToScene(item.boundingRect().center())
                _move_scene(item, center_before.x() - center_after.x(), center_before.y() - center_after.y())
                item.setRotation(requested_rotation)
            elif abs(requested_rotation) > 1e-6:
                center = item.mapToScene(item.boundingRect().center())
                rel_x, rel_y = center.x() - (origin_x + dx), center.y() - (origin_y + dy)
                target_x = origin_x + dx + rel_x * cosine - rel_y * sine
                target_y = origin_y + dy + rel_x * sine + rel_y * cosine
                _move_scene(item, target_x - center.x(), target_y - center.y())
                item.setRotation(item.rotation() + requested_rotation)
            item.setOpacity(opacity)
        except RuntimeError:
            continue
    _sync_transform_controls(page)
    _touch_document(page, "Transformações aplicadas à seleção.")


def _flip_selection(page, horizontal: bool) -> None:
    items = _eligible_selection(page)
    if not items:
        return
    for item in items:
        try:
            _preserve_scene_center(item)
            center_before = item.mapToScene(item.boundingRect().center())
            transform = QTransform().scale(-1.0, 1.0) if horizontal else QTransform().scale(1.0, -1.0)
            item.setTransform(transform, True)
            center_after = item.mapToScene(item.boundingRect().center())
            _move_scene(item, center_before.x() - center_after.x(), center_before.y() - center_after.y())
        except RuntimeError:
            continue
    _touch_document(page, "Seleção espelhada horizontalmente." if horizontal else "Seleção espelhada verticalmente.")


def _align_to_page(page, mode: str) -> None:
    items = _eligible_selection(page)
    bounds = _bounds(items)
    if not items or bounds is None:
        return
    page_rect = page.scene.sceneRect()
    dx, dy = alignment_delta(
        bounds,
        (page_rect.left(), page_rect.top(), page_rect.width(), page_rect.height()),
        mode,
    )
    for item in items:
        _move_scene(item, dx, dy)
    _sync_transform_controls(page)
    _touch_document(page, f"Seleção alinhada à página ({mode}).")


def _distribute(page, axis: str) -> None:
    items = _eligible_selection(page)
    if len(items) < 3:
        page.status_label.setText("Selecione pelo menos três objetos para distribuir.")
        return
    rects = [item.sceneBoundingRect() for item in items]
    if axis == "horizontal":
        offsets = distribution_offsets((r.left(), r.right()) for r in rects)
        for item, dx in zip(items, offsets):
            if abs(dx) > 1e-6:
                _move_scene(item, dx, 0.0)
    else:
        offsets = distribution_offsets((r.top(), r.bottom()) for r in rects)
        for item, dy in zip(items, offsets):
            if abs(dy) > 1e-6:
                _move_scene(item, 0.0, dy)
    _sync_transform_controls(page)
    _touch_document(page, "Espaçamento entre objetos uniformizado.")


def _center_on_page(page) -> None:
    items = _eligible_selection(page)
    bounds = _bounds(items)
    if not items or bounds is None:
        return
    page_rect = page.scene.sceneRect()
    target_x = page_rect.left() + (page_rect.width() - bounds[2]) / 2.0
    target_y = page_rect.top() + (page_rect.height() - bounds[3]) / 2.0
    dx, dy = target_x - bounds[0], target_y - bounds[1]
    for item in items:
        _move_scene(item, dx, dy)
    _sync_transform_controls(page)
    _touch_document(page, "Seleção centralizada na página.")


def _size_edited(page, axis: str) -> None:
    page._v172_last_size_axis = axis
    if page.v172_keep_ratio.isChecked():
        items = _eligible_selection(page)
        if len(items) == 1:
            rect = items[0].sceneBoundingRect()
            ratio = rect.height() / max(1.0, rect.width())
            if axis == "width":
                page.v172_height.blockSignals(True)
                page.v172_height.setValue(page.v172_width.value() * ratio)
                page.v172_height.blockSignals(False)
            else:
                page.v172_width.blockSignals(True)
                page.v172_width.setValue(page.v172_height.value() / max(0.001, ratio))
                page.v172_width.blockSignals(False)


def _install_transform_tab(page) -> None:
    if getattr(page, "_v172_transform_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    if tabs.findChild(QWidget, "artStudioTransformTabV172") is not None:
        page._v172_transform_installed = True
        return

    tab = QWidget(tabs)
    tab.setObjectName("artStudioTransformTabV172")
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(2, 2, 2, 2)
    scroll = QScrollArea(tab)
    scroll.setObjectName("artStudioTransformScrollV172")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    content = QWidget(scroll)
    root = QVBoxLayout(content)
    root.setContentsMargins(8, 8, 8, 12)
    root.setSpacing(9)

    title = QLabel("TRANSFORMAR E POSICIONAR", content)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel("Ajuste medidas e posição com precisão, alinhe à página e distribua os elementos da composição.", content)
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    root.addWidget(title)
    root.addWidget(hint)

    page.v172_selection_info = QLabel("Nenhum objeto selecionado", content)
    page.v172_selection_info.setObjectName("artStudioSelectionInfoV172")
    root.addWidget(page.v172_selection_info)

    pos_card, pos_layout = _card(content, "Posição")
    pos_form = QFormLayout()
    pos_form.setSpacing(7)
    page.v172_position_x = _spin(pos_card)
    page.v172_position_y = _spin(pos_card)
    pos_form.addRow("Horizontal (X)", page.v172_position_x)
    pos_form.addRow("Vertical (Y)", page.v172_position_y)
    pos_layout.addLayout(pos_form)
    root.addWidget(pos_card)

    size_card, size_layout = _card(content, "Tamanho")
    size_form = QFormLayout()
    size_form.setSpacing(7)
    page.v172_width = _spin(size_card, minimum=1.0, maximum=50000.0)
    page.v172_height = _spin(size_card, minimum=1.0, maximum=50000.0)
    page.v172_keep_ratio = QCheckBox("Manter proporção", size_card)
    page.v172_keep_ratio.setChecked(True)
    size_form.addRow("Largura", page.v172_width)
    size_form.addRow("Altura", page.v172_height)
    size_layout.addLayout(size_form)
    size_layout.addWidget(page.v172_keep_ratio)
    page.v172_dimensions_note = QLabel("Selecione um objeto para editar as medidas.", size_card)
    page.v172_dimensions_note.setObjectName("artStudioSectionHint")
    page.v172_dimensions_note.setWordWrap(True)
    size_layout.addWidget(page.v172_dimensions_note)
    root.addWidget(size_card)

    appearance_card, appearance_layout = _card(content, "Aparência")
    appearance_form = QFormLayout()
    appearance_form.setSpacing(7)
    page.v172_rotation = _spin(appearance_card, suffix="°", minimum=-360.0, maximum=360.0)
    page.v172_opacity = QSlider(Qt.Orientation.Horizontal, appearance_card)
    page.v172_opacity.setRange(0, 100)
    page.v172_opacity.setValue(100)
    page.v172_opacity.setToolTip("Opacidade do objeto ou da seleção")
    appearance_form.addRow("Rotação", page.v172_rotation)
    appearance_form.addRow("Opacidade", page.v172_opacity)
    appearance_layout.addLayout(appearance_form)
    flip_row = QHBoxLayout()
    page.v172_flip_h = QPushButton("Espelhar H")
    page.v172_flip_v = QPushButton("Espelhar V")
    for button in (page.v172_flip_h, page.v172_flip_v):
        button.setProperty("secondary", True)
        flip_row.addWidget(button)
    appearance_layout.addLayout(flip_row)
    root.addWidget(appearance_card)

    apply_row = QHBoxLayout()
    page.v172_apply_button = QPushButton("Aplicar transformação")
    page.v172_apply_button.setObjectName("artStudioApplyTransformV172")
    page.v172_apply_button.setProperty("secondary", False)
    page.v172_center_button = QPushButton("Centralizar na página")
    page.v172_center_button.setProperty("secondary", True)
    apply_row.addWidget(page.v172_apply_button, 1)
    root.addLayout(apply_row)
    root.addWidget(page.v172_center_button)

    align_card, align_layout = _card(content, "Alinhar à página")
    align_rows = []
    align_specs = (
        (("Esquerda", "left"), ("Centro H", "center-h"), ("Direita", "right")),
        (("Topo", "top"), ("Centro V", "center-v"), ("Base", "bottom")),
    )
    page.v172_alignment_buttons = []
    for row_spec in align_specs:
        row = QHBoxLayout()
        for label, mode in row_spec:
            button = QPushButton(label, align_card)
            button.setProperty("secondary", True)
            button.clicked.connect(lambda _checked=False, value=mode: _align_to_page(page, value))
            row.addWidget(button)
            page.v172_alignment_buttons.append(button)
        align_layout.addLayout(row)
    root.addWidget(align_card)

    distribute_card, distribute_layout = _card(content, "Distribuir objetos")
    page.v172_distribute_h = QPushButton("Distribuir horizontalmente", distribute_card)
    page.v172_distribute_v = QPushButton("Distribuir verticalmente", distribute_card)
    for button in (page.v172_distribute_h, page.v172_distribute_v):
        button.setProperty("secondary", True)
        distribute_layout.addWidget(button)
    root.addWidget(distribute_card)

    root.addStretch(1)
    scroll.setWidget(content)
    outer.addWidget(scroll)
    tabs.addTab(tab, "⌗  Transformar")
    page.v172_transform_tab = tab

    page.v172_apply_button.clicked.connect(lambda: _apply_transform(page))
    page.v172_center_button.clicked.connect(lambda: _center_on_page(page))
    page.v172_flip_h.clicked.connect(lambda: _flip_selection(page, True))
    page.v172_flip_v.clicked.connect(lambda: _flip_selection(page, False))
    page.v172_distribute_h.clicked.connect(lambda: _distribute(page, "horizontal"))
    page.v172_distribute_v.clicked.connect(lambda: _distribute(page, "vertical"))
    page.v172_width.editingFinished.connect(lambda: _size_edited(page, "width"))
    page.v172_height.editingFinished.connect(lambda: _size_edited(page, "height"))
    page.scene.selectionChanged.connect(lambda: _sync_transform_controls(page))
    page.layers.itemSelectionChanged.connect(lambda: _sync_transform_controls(page))

    page.v172_transform_controls = [
        page.v172_position_x, page.v172_position_y, page.v172_width,
        page.v172_height, page.v172_rotation, page.v172_opacity,
        page.v172_keep_ratio, page.v172_apply_button,
        page.v172_center_button, page.v172_flip_h, page.v172_flip_v,
    ]
    page.v172_align_buttons_enabled = lambda enabled: [b.setEnabled(bool(enabled)) for b in page.v172_alignment_buttons]
    page._v172_last_size_axis = "width"
    page._v172_transform_installed = True
    _sync_transform_controls(page)


def enhance_art_studio_page_v172(page) -> None:
    if getattr(page, "_v172_installed", False):
        return
    _install_transform_serialization(page)
    _install_transform_tab(page)
    if not getattr(page, "_v172_transform_installed", False):
        return
    nudge_filter = _NudgeFilter(page)
    view = getattr(page, "view", None)
    if view is not None:
        view.installEventFilter(nudge_filter)
        view.viewport().installEventFilter(nudge_filter)
    page._v172_nudge_filter = nudge_filter
    page._v172_installed = True
    page.status_label.setText(
        "V172: transformação precisa, alinhamento à página, distribuição uniforme e movimento por setas."
    )


def install_art_studio_v172() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _wrap_v171_skin()
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v172_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v172(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v172(page)

    MainWindow.__init__ = init_with_v172
    MainWindow._v172_integration_installed = True
    _INSTALLED = True
