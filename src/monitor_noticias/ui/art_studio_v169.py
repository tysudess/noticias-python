from __future__ import annotations

"""V169 — encaixe magnético e guias inteligentes durante a movimentação.

O snap opera somente nos objetos já selecionados e visíveis/desbloqueados.
Não cria, remove, agrupa ou serializa itens. As linhas de alinhamento são
renderizadas em overlay transparente, fora da QGraphicsScene.
"""

import weakref

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QGraphicsTextItem,
)

from monitor_noticias.ui.art_studio_snap_engine_v169 import (
    DEFAULT_SNAP_CONFIG,
    compute_smart_snap,
    normalize_snap_config,
)
from monitor_noticias.ui.art_studio_guides_engine_v168 import composition_guide_positions
from monitor_noticias.ui.art_studio_v151 import _move_by_scene_delta, _movable_selection, _schedule_history


class _SnapGuidesOverlay(QWidget):
    """Overlay transitório das linhas inteligentes; nunca participa da exportação."""

    def __init__(self, page) -> None:
        viewport = page.view.viewport()
        super().__init__(viewport)
        self._page_ref = weakref.ref(page)
        self._view_ref = weakref.ref(page.view)
        self._x_guide: float | None = None
        self._y_guide: float | None = None
        self._enabled = False
        self.setObjectName("artStudioSmartSnapOverlayV169")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setGeometry(viewport.rect())
        viewport.installEventFilter(self)
        page.view.installEventFilter(self)
        self.hide()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        view = self._view_ref()
        if view is None:
            return False
        viewport = view.viewport()
        if watched is viewport and event.type() == QEvent.Type.Resize:
            self.setGeometry(viewport.rect())
        if event.type() in {
            QEvent.Type.Paint,
            QEvent.Type.Resize,
            QEvent.Type.Wheel,
            QEvent.Type.Show,
        }:
            self.update()
        return False

    def set_guides(self, x_guide=None, y_guide=None, *, enabled=True) -> None:
        self._x_guide = float(x_guide) if x_guide is not None else None
        self._y_guide = float(y_guide) if y_guide is not None else None
        self._enabled = bool(enabled) and (self._x_guide is not None or self._y_guide is not None)
        self.setVisible(self._enabled)
        if self._enabled:
            self.raise_()
        self.update()

    def clear(self) -> None:
        self._x_guide = None
        self._y_guide = None
        self._enabled = False
        self.hide()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._enabled:
            return
        page = self._page_ref()
        view = self._view_ref()
        if page is None or view is None or not page.isVisible():
            return
        scene_rect = page.scene.sceneRect()
        if scene_rect.isEmpty():
            return
        visible = view.mapToScene(self.rect()).boundingRect()
        clip = scene_rect.intersected(visible)
        if clip.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setClipRect(self.rect())
        if self._x_guide is not None:
            x = self._x_guide
            top = view.mapFromScene(QPointF(x, clip.top()))
            bottom = view.mapFromScene(QPointF(x, clip.bottom()))
            painter.setPen(QPen(QColor(47, 211, 201, 235), 1.5, Qt.PenStyle.SolidLine))
            painter.drawLine(top, bottom)
            painter.setBrush(QColor(47, 211, 201, 230))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(top), 3.0, 3.0)
            painter.drawEllipse(QPointF(bottom), 3.0, 3.0)
        if self._y_guide is not None:
            y = self._y_guide
            left = view.mapFromScene(QPointF(clip.left(), y))
            right = view.mapFromScene(QPointF(clip.right(), y))
            painter.setPen(QPen(QColor(47, 211, 201, 235), 1.5, Qt.PenStyle.SolidLine))
            painter.drawLine(left, right)
            painter.setBrush(QColor(47, 211, 201, 230))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(left), 3.0, 3.0)
            painter.drawEllipse(QPointF(right), 3.0, 3.0)
        painter.end()


class _SnapController(QObject):
    """Observa o arraste e corrige a seleção após a movimentação do QGraphicsView."""

    def __init__(self, page) -> None:
        viewport = page.view.viewport()
        super().__init__(viewport)
        self._page_ref = weakref.ref(page)
        self._overlay_ref = weakref.ref(page.v169_snap_overlay)
        self.config = normalize_snap_config(DEFAULT_SNAP_CONFIG)
        self._dragging = False
        self._release_pending = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._process_snap)
        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_overlay)
        viewport.installEventFilter(self)

    def set_config(self, value) -> None:
        self.config = normalize_snap_config(value)
        if not self.config["enabled"]:
            self._timer.stop()
            self._dragging = False
            self._clear_overlay()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if not self.config["enabled"]:
            return False
        event_type = event.type()
        if event_type == QEvent.Type.MouseMove:
            try:
                dragging = bool(event.buttons() & Qt.MouseButton.LeftButton)
            except (AttributeError, RuntimeError):
                dragging = False
            if dragging:
                self._dragging = True
                self._release_pending = False
                self._clear_timer.stop()
                self._timer.start(0)
        elif event_type == QEvent.Type.MouseButtonRelease:
            try:
                released_left = event.button() == Qt.MouseButton.LeftButton
            except (AttributeError, RuntimeError):
                released_left = False
            if released_left and self._dragging:
                self._release_pending = True
                self._timer.start(0)
                self._clear_timer.start(900)
        return False

    @staticmethod
    def _bounds_union(items) -> tuple[float, float, float, float] | None:
        rect = None
        for item in items:
            current = item.sceneBoundingRect()
            rect = QRectF(current) if rect is None else rect.united(current)
        if rect is None or rect.isEmpty():
            return None
        return rect.left(), rect.top(), rect.right(), rect.bottom()

    @staticmethod
    def _related(first, second) -> bool:
        try:
            return first is second or first.isAncestorOf(second) or second.isAncestorOf(first)
        except RuntimeError:
            return True

    def _is_text_being_edited(self, page) -> bool:
        try:
            focus = page.scene.focusItem()
            return bool(
                isinstance(focus, QGraphicsTextItem)
                and focus.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction
            )
        except RuntimeError:
            return False

    def _process_snap(self) -> None:
        page = self._page_ref()
        overlay = self._overlay_ref()
        if page is None or overlay is None or not self.config["enabled"]:
            return
        if self._is_text_being_edited(page):
            overlay.clear()
            if self._release_pending:
                self._dragging = False
                self._release_pending = False
            return

        moving, _skipped = _movable_selection(page)
        if not moving:
            overlay.clear()
            if self._release_pending:
                self._dragging = False
                self._release_pending = False
            return
        moving_bounds = self._bounds_union(moving)
        if moving_bounds is None:
            overlay.clear()
            if self._release_pending:
                self._dragging = False
                self._release_pending = False
            return

        targets = []
        try:
            all_roots = list(page._content_items())
        except Exception:
            all_roots = []
        for other in all_roots:
            if other in moving or not other.isVisible():
                continue
            if any(self._related(other, item) for item in moving):
                continue
            rect = other.sceneBoundingRect()
            if not rect.isEmpty():
                targets.append((rect.left(), rect.top(), rect.right(), rect.bottom()))

        scene_rect = page.scene.sceneRect()
        zoom = max(0.001, abs(float(page.view.transform().m11())))
        guide_state = getattr(page, "v168_guide_config", {}) or {}
        guide_positions = composition_guide_positions((scene_rect.width(), scene_rect.height()))
        extra_x_lines = []
        extra_y_lines = []
        if self.config["snap_to_composition_guides"]:
            if guide_state.get("thirds_enabled"):
                extra_x_lines.extend(
                    scene_rect.left() + value for value in guide_positions["vertical_thirds"]
                )
                extra_y_lines.extend(
                    scene_rect.top() + value for value in guide_positions["horizontal_thirds"]
                )
            if guide_state.get("center_enabled"):
                center_x, center_y = guide_positions["center"]
                extra_x_lines.append(scene_rect.left() + center_x)
                extra_y_lines.append(scene_rect.top() + center_y)
            if guide_state.get("safe_area_enabled"):
                safe_left, safe_top, safe_right, safe_bottom = guide_positions["safe_rect"]
                extra_x_lines.extend((scene_rect.left() + safe_left, scene_rect.left() + safe_right))
                extra_y_lines.extend((scene_rect.top() + safe_top, scene_rect.top() + safe_bottom))

        grid_step = None
        if self.config["snap_to_grid"]:
            grid_combo = getattr(page, "v168_grid_step", None)
            grid_step = grid_combo.currentData() if grid_combo is not None else 50

        result = compute_smart_snap(
            moving_bounds,
            targets,
            (scene_rect.left(), scene_rect.top(), scene_rect.right(), scene_rect.bottom()),
            zoom,
            self.config["threshold_px"],
            snap_to_objects=self.config["snap_to_objects"],
            snap_to_page=self.config["snap_to_page"],
            snap_to_grid=self.config["snap_to_grid"],
            grid_step=grid_step,
            grid_origin=(scene_rect.left(), scene_rect.top()),
            extra_x_lines=extra_x_lines,
            extra_y_lines=extra_y_lines,
        )
        dx = float(result["dx"])
        dy = float(result["dy"])
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            for item in moving:
                _move_by_scene_delta(item, dx, dy)
            if hasattr(page, "_v148_sync_handles"):
                page._v148_sync_handles()
            if hasattr(page, "_v148_update_dimensions"):
                page._v148_update_dimensions()
            page.scene.update()
            _schedule_history(page)

        overlay.set_guides(
            result["x_guide"],
            result["y_guide"],
            enabled=self.config["show_guides"],
        )
        if self._release_pending:
            if result["x_guide"] is not None or result["y_guide"] is not None:
                axes = " e ".join(
                    name for name, coordinate in (("vertical", result["x_guide"]), ("horizontal", result["y_guide"]))
                    if coordinate is not None
                )
                page.status_label.setText(f"Encaixe magnético aplicado · guia {axes}.")
            self._dragging = False
            self._release_pending = False

    def _clear_overlay(self) -> None:
        overlay = self._overlay_ref()
        if overlay is not None:
            overlay.clear()


def _read_config(page) -> dict:
    return normalize_snap_config({
        "enabled": page.v169_snap_enabled.isChecked(),
        "snap_to_objects": page.v169_snap_objects.isChecked(),
        "snap_to_page": page.v169_snap_page.isChecked(),
        "snap_to_grid": page.v169_snap_grid.isChecked(),
        "snap_to_composition_guides": page.v169_snap_composition_guides.isChecked(),
        "show_guides": page.v169_snap_guides.isChecked(),
        "threshold_px": page.v169_snap_threshold.currentData(),
    })


def _sync_config(page) -> None:
    controller = getattr(page, "v169_snap_controller", None)
    if controller is None:
        return
    config = _read_config(page)
    page.v169_snap_config = config
    controller.set_config(config)
    page.v169_snap_status.setText(
        "Encaixe desativado. Ative para alinhar automaticamente durante o arraste."
        if not config["enabled"] else
        f"Encaixe ativo · tolerância de {config['threshold_px']} px na tela."
    )


def _install_snap_tab(page) -> None:
    if getattr(page, "_v169_snap_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    if tabs.findChild(QWidget, "artStudioSnapTabPageV169") is not None:
        page._v169_snap_installed = True
        return

    tab = QWidget(tabs)
    tab.setObjectName("artStudioSnapTabPageV169")
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(10, 10, 10, 14)
    layout.setSpacing(8)

    title = QLabel("ENCAIXE INTELIGENTE", tab)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel(
        "Ao arrastar objetos, aproxime bordas e centros de outros elementos ou da página. "
        "O encaixe não cria camadas e respeita objetos bloqueados na seleção.",
        tab,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(hint)

    main_card = QFrame(tab)
    main_card.setObjectName("artStudioSnapMainCardV169")
    main_layout = QVBoxLayout(main_card)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(8)
    page.v169_snap_enabled = QCheckBox("Ativar encaixe magnético", main_card)
    page.v169_snap_enabled.setToolTip("Alinha os objetos selecionados durante o arraste, sem alterar escala ou rotação.")
    page.v169_snap_objects = QCheckBox("Encaixar em outros objetos", main_card)
    page.v169_snap_objects.setChecked(True)
    page.v169_snap_page = QCheckBox("Encaixar nas bordas e no centro da página", main_card)
    page.v169_snap_page.setChecked(True)
    page.v169_snap_grid = QCheckBox("Encaixar na grade da aba Guias", main_card)
    page.v169_snap_grid.setChecked(False)
    page.v169_snap_composition_guides = QCheckBox("Encaixar nas guias de terços, centro e margens", main_card)
    page.v169_snap_composition_guides.setChecked(True)
    page.v169_snap_guides = QCheckBox("Mostrar guias inteligentes", main_card)
    page.v169_snap_guides.setChecked(True)
    main_layout.addWidget(page.v169_snap_enabled)
    main_layout.addWidget(page.v169_snap_objects)
    main_layout.addWidget(page.v169_snap_page)
    main_layout.addWidget(page.v169_snap_grid)
    main_layout.addWidget(page.v169_snap_composition_guides)
    main_layout.addWidget(page.v169_snap_guides)
    layout.addWidget(main_card)

    threshold_card = QFrame(tab)
    threshold_card.setObjectName("artStudioSnapThresholdCardV169")
    form = QFormLayout(threshold_card)
    form.setContentsMargins(10, 10, 10, 10)
    form.setVerticalSpacing(8)
    page.v169_snap_threshold = QComboBox(threshold_card)
    for value in (4, 6, 8, 10, 12, 16, 20, 24):
        page.v169_snap_threshold.addItem(f"{value} px", value)
    page.v169_snap_threshold.setCurrentIndex(2)
    form.addRow("Sensibilidade do encaixe", page.v169_snap_threshold)
    layout.addWidget(threshold_card)

    page.v169_snap_status = QLabel(
        "Encaixe desativado. Ative para alinhar automaticamente durante o arraste.", tab
    )
    page.v169_snap_status.setObjectName("artStudioSectionHint")
    page.v169_snap_status.setWordWrap(True)
    layout.addWidget(page.v169_snap_status)

    page.v169_snap_overlay = _SnapGuidesOverlay(page)
    page.v169_snap_controller = _SnapController(page)
    page.v169_snap_controller.set_config(DEFAULT_SNAP_CONFIG)

    for control in (
        page.v169_snap_enabled,
        page.v169_snap_objects,
        page.v169_snap_page,
        page.v169_snap_grid,
        page.v169_snap_composition_guides,
        page.v169_snap_guides,
    ):
        control.toggled.connect(lambda *_args: _sync_config(page))
    page.v169_snap_threshold.currentIndexChanged.connect(lambda *_args: _sync_config(page))

    layout.addStretch(1)
    tabs.addTab(tab, "⌖  Encaixe")
    page.v169_snap_tab = tab
    page._v169_snap_installed = True
    _sync_config(page)


def enhance_art_studio_page_v169(page) -> None:
    if getattr(page, "_v169_installed", False):
        return
    _install_snap_tab(page)
    if getattr(page, "_v169_snap_installed", False):
        page._v169_installed = True
        page.status_label.setText(
            "V169: encaixe magnético por bordas e centros, alinhamento com a página e guias inteligentes durante o arraste."
        )


def install_art_studio_v169() -> None:
    """Instala o encaixe inteligente depois da grade de precisão V168."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v169_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v169(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v169(page)

    MainWindow.__init__ = init_with_v169
    MainWindow._v169_integration_installed = True
