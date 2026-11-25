from __future__ import annotations

"""V153 — redimensionamento confiável, preservação de camadas e sidebar compacta.

A camada corrige o ciclo de vida das alças V148 (que eram recriadas durante o
arraste), aplica redimensionamento mantendo transformações existentes, impede
que novas inserções cubram desnecessariamente objetos anteriores e adiciona
modo compacto à navegação lateral. Não altera o formato .centralart.
"""

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from monitor_noticias.ui import art_studio_v148 as _v148
from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem


# ---------------------------------------------------------------------------
# Redimensionamento: usar a transformação da cena capturada no início do gesto
# e nunca destruir/recriar as alças enquanto o botão do mouse está pressionado.
# ---------------------------------------------------------------------------
def _move_by_scene_delta(item: QGraphicsItem, delta: QPointF) -> None:
    if delta.isNull():
        return
    parent = item.parentItem()
    if parent is None:
        item.setPos(item.pos() + delta)
        return
    origin = parent.mapFromScene(QPointF(0.0, 0.0))
    target = parent.mapFromScene(QPointF(delta.x(), delta.y()))
    item.setPos(item.pos() + (target - origin))


def _resize_handle_press(self, event) -> None:
    target = self.parentItem()
    if target is None or bool(target.data(LOCKED_KEY)):
        event.ignore()
        return
    if isinstance(target, QGraphicsTextItem) and target.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        event.ignore()
        return

    self._v153_resizing = True
    self._start_scene = QPointF(event.scenePos())
    inverse, invertible = target.sceneTransform().inverted()
    if not invertible:
        self._v153_resizing = False
        event.ignore()
        return
    self._v153_start_inverse = inverse
    self._start_local = inverse.map(self._start_scene)
    self._start_scale = float(target.scale())
    self._start_rect = QRectF(target.boundingRect())

    if isinstance(target, QGraphicsTextItem):
        width = float(target.textWidth())
        if width <= 0:
            width = float(target.boundingRect().width())
        self._start_width = max(40.0, width)
        self._v153_anchor_local = QPointF(
            self._start_width if self._direction[0] < 0 else 0.0,
            target.boundingRect().center().y(),
        )
    elif isinstance(target, QGraphicsPixmapItem):
        self._v153_anchor_local = QPointF(
            self._start_rect.right() if self._direction[0] < 0 else self._start_rect.left(),
            self._start_rect.bottom() if self._direction[1] < 0 else self._start_rect.top(),
        )
    else:
        self._v153_resizing = False
        event.ignore()
        return

    self._anchor_scene = target.mapToScene(self._v153_anchor_local)
    event.accept()


def _resize_handle_move(self, event) -> None:
    target = self.parentItem()
    if target is None or not getattr(self, "_v153_resizing", False):
        event.ignore()
        return

    current_local = self._v153_start_inverse.map(QPointF(event.scenePos()))
    delta_local = current_local - self._start_local

    if isinstance(target, QGraphicsTextItem):
        direction_x = int(self._direction[0]) or 1
        new_width = max(40.0, min(12000.0, self._start_width + direction_x * delta_local.x()))
        target.setTextWidth(new_width)
        rect = target.boundingRect()
        anchor_x = new_width if direction_x < 0 else 0.0
        new_anchor = target.mapToScene(QPointF(anchor_x, rect.center().y()))
        _move_by_scene_delta(target, self._anchor_scene - new_anchor)
    elif isinstance(target, QGraphicsPixmapItem):
        width = max(1.0, self._start_rect.width())
        height = max(1.0, self._start_rect.height())
        factor_x = 1.0 + int(self._direction[0]) * delta_local.x() / width
        factor_y = 1.0 + int(self._direction[1]) * delta_local.y() / height
        # O eixo com maior deslocamento relativo controla a escala proporcional.
        factor = factor_x if abs(factor_x - 1.0) >= abs(factor_y - 1.0) else factor_y
        max_factor = 8.0 / max(0.001, abs(self._start_scale))
        factor = max(0.05, min(max_factor, factor))
        target.setScale(self._start_scale * factor)
        new_anchor = target.mapToScene(self._v153_anchor_local)
        _move_by_scene_delta(target, self._anchor_scene - new_anchor)
    else:
        event.ignore()
        return

    # A sincronização completa remove a alça que está recebendo o evento e
    # interrompe o arraste. Apenas reposiciona as alças já existentes.
    try:
        _v148._position_handles(target)
    except RuntimeError:
        pass
    page = self._page
    if hasattr(page, "_v148_update_dimensions"):
        page._v148_update_dimensions()
    if hasattr(page, "_v148_schedule_history"):
        page._v148_schedule_history()
    page.scene.update()
    event.accept()


def _resize_handle_release(self, event) -> None:
    self._v153_resizing = False
    page = self._page
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v148_update_dimensions"):
        page._v148_update_dimensions()
    if hasattr(page, "_v148_schedule_history"):
        page._v148_schedule_history()
    event.accept()


def _sync_dimension_controls(page) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    is_image = isinstance(item, QGraphicsPixmapItem)
    is_text = isinstance(item, QGraphicsTextItem)
    frame = getattr(page, "v148_size_frame", None)
    if frame is not None:
        frame.setVisible(bool(is_image or is_text))

    unlocked = item is not None and not bool(item.data(LOCKED_KEY))
    page.v148_width_spin.setEnabled(bool((is_image or is_text) and unlocked))
    page.v148_apply_size_button.setEnabled(bool((is_image or is_text) and unlocked))
    page.v148_height_spin.setVisible(bool(is_image))
    page.v148_height_label.setVisible(bool(is_image))
    page.v148_ratio_check.setVisible(bool(is_image))
    page.v148_flip_h_button.setVisible(bool(is_image))
    page.v148_flip_v_button.setVisible(bool(is_image))
    if not (is_image or is_text):
        return

    page.v148_width_spin.blockSignals(True)
    page.v148_height_spin.blockSignals(True)
    if is_image:
        mapped = item.transform().mapRect(item.boundingRect())
        width = max(1, round(mapped.width() * abs(item.scale())))
        height = max(1, round(mapped.height() * abs(item.scale())))
        page.v148_width_spin.setValue(width)
        page.v148_height_spin.setValue(height)
    else:
        width = float(item.textWidth())
        if width <= 0:
            width = float(item.boundingRect().width())
        page.v148_width_spin.setValue(max(24, round(width)))
    page.v148_width_spin.blockSignals(False)
    page.v148_height_spin.blockSignals(False)

    rich_width = getattr(page, "v148_text_width_spin", None)
    if rich_width is not None:
        rich_width.blockSignals(True)
        rich_width.setEnabled(bool(is_text and unlocked))
        if is_text:
            width = float(item.textWidth())
            if width <= 0:
                width = float(item.boundingRect().width())
            rich_width.setValue(max(40, round(width)))
        rich_width.blockSignals(False)


def _update_height_from_width(page, value: int) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    if not isinstance(item, QGraphicsPixmapItem) or not page.v148_ratio_check.isChecked():
        return
    mapped = item.transform().mapRect(item.boundingRect())
    current_width = max(1.0, mapped.width() * abs(item.scale()))
    current_height = max(1.0, mapped.height() * abs(item.scale()))
    height = max(1, round(int(value) * current_height / current_width))
    page.v148_height_spin.blockSignals(True)
    page.v148_height_spin.setValue(height)
    page.v148_height_spin.blockSignals(False)


def _set_text_width_centered(page, item: QGraphicsTextItem, width: float) -> None:
    center_before = item.mapToScene(item.boundingRect().center())
    item.setTextWidth(max(40.0, min(12000.0, float(width))))
    center_after = item.mapToScene(item.boundingRect().center())
    _move_by_scene_delta(item, center_before - center_after)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    _sync_dimension_controls(page)
    if hasattr(page, "_v148_schedule_history"):
        page._v148_schedule_history()
    page.scene.update()


def _apply_dimensions(page) -> None:
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    if item is None or bool(item.data(LOCKED_KEY)):
        return

    width = max(24, int(page.v148_width_spin.value()))
    if isinstance(item, QGraphicsTextItem):
        _set_text_width_centered(page, item, width)
        page.status_label.setText(f"Caixa de texto ajustada para {width} px, preservando o centro.")
        return

    if not isinstance(item, QGraphicsPixmapItem):
        return

    mapped = item.transform().mapRect(item.boundingRect())
    current_width = max(1.0, mapped.width() * abs(item.scale()))
    current_height = max(1.0, mapped.height() * abs(item.scale()))
    center_before = item.mapToScene(item.boundingRect().center())

    if page.v148_ratio_check.isChecked():
        factor = width / current_width
        item.setScale(item.scale() * factor)
        height = max(1, round(current_height * factor))
        page.v148_height_spin.blockSignals(True)
        page.v148_height_spin.setValue(height)
        page.v148_height_spin.blockSignals(False)
    else:
        height = max(24, int(page.v148_height_spin.value()))
        sx = width / current_width
        sy = height / current_height
        transform = item.transform()
        # Escala as colunas da matriz local; preserva espelhamento, cisalhamento
        # e demais transformações já aplicadas (inclusive pelas versões V152).
        adjusted = QTransform(
            transform.m11() * sx,
            transform.m12() * sx,
            transform.m13() * sx,
            transform.m21() * sy,
            transform.m22() * sy,
            transform.m23() * sy,
            transform.m31(),
            transform.m32(),
            transform.m33(),
        )
        item.setTransform(adjusted, False)

    center_after = item.mapToScene(item.boundingRect().center())
    _move_by_scene_delta(item, center_before - center_after)
    _sync_dimension_controls(page)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v148_schedule_history"):
        page._v148_schedule_history()
    page.status_label.setText(f"Imagem redimensionada para {width} × {height} px.")
    page.scene.update()


def _patch_resize_engine(page) -> None:
    handle_class = _v148._ResizeHandle
    if not getattr(handle_class, "_v153_patched", False):
        handle_class.mousePressEvent = _resize_handle_press
        handle_class.mouseMoveEvent = _resize_handle_move
        handle_class.mouseReleaseEvent = _resize_handle_release
        original_init = handle_class.__init__

        def init_with_fixed_handle_size(self, target, direction, owner_page):
            original_init(self, target, direction, owner_page)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        handle_class.__init__ = init_with_fixed_handle_size
        handle_class._v153_patched = True

    # Os sinais do V148 resolvem estes nomes globais no momento do clique.
    _v148._apply_dimensions = _apply_dimensions
    _v148._update_dimension_controls = _sync_dimension_controls
    _v148._update_height_from_width = _update_height_from_width

    # O controle de largura da barra de texto também deve preservar o centro.
    rich_width = getattr(page, "v148_text_width_spin", None)
    if rich_width is not None and not getattr(page, "_v153_text_width_rebound", False):
        try:
            rich_width.valueChanged.disconnect()
        except (RuntimeError, TypeError):
            pass
        rich_width.valueChanged.connect(
            lambda value: _set_text_width_centered(page, _selected_text(page), value)
            if _selected_text(page) is not None else None
        )
        page._v153_text_width_rebound = True


def _selected_text(page):
    selected = list(page.scene.selectedItems())
    item = selected[0] if len(selected) == 1 else None
    return item if isinstance(item, QGraphicsTextItem) else None


# ---------------------------------------------------------------------------
# Novos objetos: preservar objetos existentes e procurar uma área livre para
# inserir a nova camada, evitando que a imagem/texto recém-criado cubra a arte.
# ---------------------------------------------------------------------------
def _history_id(item: QGraphicsItem) -> str:
    value = item.data(HISTORY_ID_KEY)
    if not value:
        import uuid
        value = uuid.uuid4().hex
        item.setData(HISTORY_ID_KEY, value)
    return str(value)


def _object_items(page) -> list[QGraphicsItem]:
    try:
        return [item for item in page._content_items() if item.parentItem() is None]
    except Exception:
        return []


def _restore_previous_objects(page, previous: list[tuple[QGraphicsItem, str]]) -> int:
    present_ids = {_history_id(item) for item in _object_items(page)}
    restored = 0
    for item, identity in previous:
        try:
            if identity in present_ids:
                continue
            if item.scene() is None:
                page.scene.addItem(item)
                item.setData(HISTORY_ID_KEY, identity)
                present_ids.add(identity)
                restored += 1
        except RuntimeError:
            continue
    if restored:
        page._refresh_layers()
    return restored


def _overlap_area(rect: QRectF, other: QRectF) -> float:
    intersection = rect.intersected(other)
    if intersection.isEmpty():
        return 0.0
    return max(0.0, intersection.width()) * max(0.0, intersection.height())


def _place_in_free_area(page, item: QGraphicsItem, previous: list[tuple[QGraphicsItem, str]]) -> bool:
    if item.scene() is not page.scene or item.parentItem() is not None:
        return False
    old_bounds = item.sceneBoundingRect()
    item_width = max(1.0, old_bounds.width())
    item_height = max(1.0, old_bounds.height())
    canvas = page.scene.sceneRect()
    if canvas.width() <= 0 or canvas.height() <= 0:
        return False

    old_x, old_y = old_bounds.left(), old_bounds.top()
    max_x = max(canvas.left() + 8.0, canvas.right() - item_width - 8.0)
    max_y = max(canvas.top() + 8.0, canvas.bottom() - item_height - 8.0)
    x_values = {old_x, canvas.left() + 12.0, (canvas.left() + max_x) / 2.0, max_x}
    y_values = {old_y, canvas.top() + 12.0, (canvas.top() + max_y) / 2.0, max_y}
    # Amostragem 4×4: suficiente para encontrar uma região livre sem deslocar
    # o objeto de modo arbitrário para longe do centro inicial.
    for step in range(1, 4):
        x_values.add(canvas.left() + 12.0 + (max_x - canvas.left() - 12.0) * step / 4.0)
        y_values.add(canvas.top() + 12.0 + (max_y - canvas.top() - 12.0) * step / 4.0)

    existing_rects: list[QRectF] = []
    for existing, _identity in previous:
        try:
            if existing is item or existing.scene() is not page.scene or not existing.isVisible():
                continue
            existing_rects.append(existing.sceneBoundingRect())
        except RuntimeError:
            continue

    best_score = math.inf
    best_delta = QPointF(0.0, 0.0)
    area = max(1.0, item_width * item_height)
    for x in x_values:
        for y in y_values:
            candidate = QRectF(float(x), float(y), item_width, item_height)
            outside = area - _overlap_area(candidate, canvas)
            overlap = sum(_overlap_area(candidate, rect) for rect in existing_rects)
            distance = math.hypot(float(x) - old_x, float(y) - old_y)
            score = outside * 1000.0 + overlap * 100.0 + distance * 0.05
            if score < best_score:
                best_score = score
                best_delta = QPointF(float(x) - old_x, float(y) - old_y)

    if best_delta.isNull():
        return False
    if best_score >= area * 100.0 * 0.01 and not existing_rects:
        return False
    _move_by_scene_delta(item, best_delta)
    return True


def _wrap_safe_creation(page) -> None:
    if getattr(page, "_v153_creation_wrapped", False):
        return
    original_make_movable = page._make_movable

    def make_movable_preserving_existing(item, kind, name):
        previous_items: list[tuple[QGraphicsItem, str]] = []
        for existing in _object_items(page):
            if existing is item:
                continue
            try:
                previous_items.append((existing, _history_id(existing)))
            except RuntimeError:
                continue

        result = original_make_movable(item, kind, name)
        restored = _restore_previous_objects(page, previous_items)
        moved = _place_in_free_area(page, item, previous_items)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        if hasattr(page, "_v148_update_dimensions"):
            page._v148_update_dimensions()
        if hasattr(page, "_v148_schedule_history"):
            page._v148_schedule_history()

        if restored:
            page.status_label.setText(
                f"Novo objeto adicionado. {restored} camada(s) anterior(es) preservada(s)."
            )
        elif moved:
            page.status_label.setText(
                "Novo objeto posicionado em uma área mais livre para manter os elementos anteriores visíveis."
            )
        return result

    page._make_movable = make_movable_preserving_existing
    page._v153_creation_wrapped = True


# ---------------------------------------------------------------------------
# Barra lateral compacta — conserva ícones, navegação e tooltips.
# ---------------------------------------------------------------------------
def _sidebar_layout(sidebar):
    layout = sidebar.layout()
    return layout if isinstance(layout, QVBoxLayout) else None


def _set_sidebar_compact(window, compact: bool) -> None:
    sidebar = getattr(window, "sidebar", None)
    if sidebar is None:
        return
    compact = bool(compact)
    window._v153_sidebar_compact = compact
    sidebar.setFixedWidth(82 if compact else 236)

    brand = sidebar.findChild(QFrame, "sidebarBrandWrap")
    if brand is not None and brand.layout() is not None:
        brand_layout = brand.layout()
        brand_layout.setContentsMargins(2 if compact else 6, 3, 2 if compact else 5, 7)
        brand_layout.setSpacing(2 if compact else 5)

    logo = sidebar.findChild(QLabel, "sidebarLogo")
    if logo is not None:
        logo.setFixedSize(28 if compact else 40, 28 if compact else 40)

    for object_name in ("sidebarBrandTitle", "sidebarBrandSub", "sidebarStatusTitle", "sidebarStatusText", "sidebarGroupLabel"):
        for label in sidebar.findChildren(QLabel, object_name):
            label.setVisible(not compact)

    for item in sidebar.findChildren(SidebarNavItem, "sidebarNavItem"):
        item.text.setVisible(not compact)
        item.current_mark.setVisible(not compact)
        row = item.layout()
        if row is not None:
            row.setContentsMargins(5 if compact else 8, 0, 5 if compact else 10, 0)
            row.setSpacing(0 if compact else 8)
        item.icon_wrap.setFixedSize(32 if compact else 28, 32 if compact else 28)
        item.setToolTip(item.accessibleName())

    status = sidebar.findChild(QFrame, "sidebarStatusCard")
    if status is not None:
        status.setMinimumHeight(42 if compact else 58)
        if status.layout() is not None:
            status.layout().setContentsMargins(4 if compact else 10, 5 if compact else 7, 4 if compact else 9, 5 if compact else 7)
            status.layout().setSpacing(2 if compact else 8)
    status_icon = sidebar.findChild(QLabel, "sidebarStatusIcon")
    if status_icon is not None:
        status_icon.setFixedSize(28 if compact else 20, 28 if compact else 20)

    toggle = getattr(window, "v153_sidebar_toggle", None)
    if toggle is not None:
        toggle.setText("›" if compact else "‹")
        toggle.setToolTip("Expandir barra lateral" if compact else "Recolher barra lateral")
    sidebar.updateGeometry()
    sidebar.update()


def _install_sidebar_compact(window) -> None:
    sidebar = getattr(window, "sidebar", None)
    layout = _sidebar_layout(sidebar) if sidebar is not None else None
    if layout is None or getattr(window, "_v153_sidebar_installed", False):
        return

    brand = sidebar.findChild(QFrame, "sidebarBrandWrap")
    brand_layout = brand.layout() if brand is not None else None
    if brand_layout is None:
        return

    toggle = QToolButton(brand)
    toggle.setObjectName("sidebarCompactToggle")
    toggle.setText("‹")
    toggle.setToolTip("Recolher barra lateral")
    toggle.setAccessibleName("Recolher ou expandir barra lateral")
    toggle.setFixedSize(20, 26)
    toggle.setCursor(Qt.CursorShape.PointingHandCursor)
    toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    toggle.setStyleSheet(
        "QToolButton#sidebarCompactToggle {background:#123B58;color:#E7C978;border:1px solid #31536C;border-radius:7px;font-size:18px;font-weight:800;}"
        "QToolButton#sidebarCompactToggle:hover {background:#1B4C6D;}"
    )
    brand_layout.insertWidget(0, toggle, 0, Qt.AlignmentFlag.AlignVCenter)
    window.v153_sidebar_toggle = toggle
    toggle.clicked.connect(lambda: _set_sidebar_compact(window, not getattr(window, "_v153_sidebar_compact", False)))
    window._v153_sidebar_installed = True
    _set_sidebar_compact(window, False)


def enhance_art_studio_page_v153(page) -> None:
    if getattr(page, "_v153_installed", False):
        return
    page._v153_installed = True
    _patch_resize_engine(page)
    _wrap_safe_creation(page)
    _sync_dimension_controls(page)
    page.status_label.setText(
        "V153: redimensionamento corrigido para texto e imagem; inserções preservam e evitam cobrir camadas; "
        "a barra lateral pode ser recolhida para mostrar somente os ícones."
    )


def install_art_studio_v153() -> None:
    """Instala V153 depois de V152, mantendo o restante da Central intacto."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v153_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v153(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v153(page)
        _install_sidebar_compact(self)

    MainWindow.__init__ = init_with_v153
    MainWindow._v153_integration_installed = True
