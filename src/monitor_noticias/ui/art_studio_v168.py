from __future__ import annotations

"""V168 — grade, guias de composição e margens seguras sobre o canvas.

As guias são desenhadas em um widget transparente sobre o viewport do canvas.
Elas não são itens da QGraphicsScene, não entram na lista de camadas e nunca
são incluídas no arquivo .centralart. O overlay não recebe eventos do mouse.
"""

import weakref

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
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
)

from monitor_noticias.ui.art_studio_guides_engine_v168 import (
    composition_guide_positions,
    normalize_guide_config,
    visible_grid_positions,
)


class _GuidesOverlay(QWidget):
    """Camada de desenho transparente, sem captura de mouse ou persistência."""

    def __init__(self, page) -> None:
        viewport = page.view.viewport()
        super().__init__(viewport)
        self._page_ref = weakref.ref(page)
        self._view_ref = weakref.ref(page.view)
        self.config = normalize_guide_config({})
        self.setObjectName("artStudioGuidesOverlayV168")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setGeometry(viewport.rect())
        viewport.installEventFilter(self)
        page.view.installEventFilter(self)
        self.hide()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        event_type = event.type()
        view = self._view_ref()
        if view is None:
            return False
        viewport = view.viewport()
        if watched is viewport and event_type == QEvent.Type.Resize:
            self.setGeometry(viewport.rect())
        if watched is viewport and event_type in {QEvent.Type.Paint, QEvent.Type.Resize}:
            self.update()
        elif watched is view and event_type in {
            QEvent.Type.Paint,
            QEvent.Type.Resize,
            QEvent.Type.Wheel,
            QEvent.Type.Show,
        }:
            self.update()
        return False

    def set_config(self, value) -> None:
        self.config = normalize_guide_config(value)
        active = any((
            self.config["grid_enabled"],
            self.config["thirds_enabled"],
            self.config["center_enabled"],
            self.config["safe_area_enabled"],
        ))
        self.setVisible(active)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        page = self._page_ref()
        view = self._view_ref()
        if page is None or view is None or not page.isVisible():
            return

        scene_rect = page.scene.sceneRect()
        if scene_rect.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setClipRect(self.rect())
        viewport_visible = view.mapToScene(self.rect()).boundingRect()
        relative_bounds = (
            viewport_visible.left() - scene_rect.left(),
            viewport_visible.top() - scene_rect.top(),
            viewport_visible.right() - scene_rect.left(),
            viewport_visible.bottom() - scene_rect.top(),
        )
        zoom = max(0.001, abs(float(view.transform().m11())))
        canvas_size = (scene_rect.width(), scene_rect.height())

        if self.config["grid_enabled"]:
            grid = visible_grid_positions(
                canvas_size,
                relative_bounds,
                self.config["grid_step"],
                zoom,
            )
            painter.setPen(QPen(QColor(214, 182, 109, 62), 1, Qt.PenStyle.DotLine))
            for x in grid["vertical"]:
                scene_x = scene_rect.left() + x
                top = view.mapFromScene(QPointF(scene_x, viewport_visible.top()))
                bottom = view.mapFromScene(QPointF(scene_x, viewport_visible.bottom()))
                painter.drawLine(top, bottom)
            for y in grid["horizontal"]:
                scene_y = scene_rect.top() + y
                left = view.mapFromScene(QPointF(viewport_visible.left(), scene_y))
                right = view.mapFromScene(QPointF(viewport_visible.right(), scene_y))
                painter.drawLine(left, right)

        guides = composition_guide_positions(canvas_size)
        if self.config["thirds_enabled"]:
            painter.setPen(QPen(QColor(75, 185, 190, 155), 1, Qt.PenStyle.DashLine))
            for x in guides["vertical_thirds"]:
                sx = scene_rect.left() + x
                painter.drawLine(
                    view.mapFromScene(QPointF(sx, viewport_visible.top())),
                    view.mapFromScene(QPointF(sx, viewport_visible.bottom())),
                )
            for y in guides["horizontal_thirds"]:
                sy = scene_rect.top() + y
                painter.drawLine(
                    view.mapFromScene(QPointF(viewport_visible.left(), sy)),
                    view.mapFromScene(QPointF(viewport_visible.right(), sy)),
                )

        if self.config["center_enabled"]:
            center_x, center_y = guides["center"]
            painter.setPen(QPen(QColor(255, 255, 255, 190), 1, Qt.PenStyle.DashLine))
            sx = scene_rect.left() + center_x
            sy = scene_rect.top() + center_y
            painter.drawLine(
                view.mapFromScene(QPointF(sx, viewport_visible.top())),
                view.mapFromScene(QPointF(sx, viewport_visible.bottom())),
            )
            painter.drawLine(
                view.mapFromScene(QPointF(viewport_visible.left(), sy)),
                view.mapFromScene(QPointF(viewport_visible.right(), sy)),
            )

        if self.config["safe_area_enabled"]:
            left, top, right, bottom = guides["safe_rect"]
            safe_rect = QRectF(
                scene_rect.left() + left,
                scene_rect.top() + top,
                right - left,
                bottom - top,
            )
            top_left = view.mapFromScene(safe_rect.topLeft())
            bottom_right = view.mapFromScene(safe_rect.bottomRight())
            painter.setPen(QPen(QColor(255, 255, 255, 190), 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(top_left, bottom_right))

        painter.end()


def _read_config(page) -> dict:
    return normalize_guide_config({
        "grid_enabled": page.v168_grid_enabled.isChecked(),
        "grid_step": page.v168_grid_step.currentData(),
        "thirds_enabled": page.v168_thirds_enabled.isChecked(),
        "center_enabled": page.v168_center_enabled.isChecked(),
        "safe_area_enabled": page.v168_safe_enabled.isChecked(),
    })


def _sync_guides(page) -> None:
    overlay = getattr(page, "v168_guides_overlay", None)
    if overlay is None:
        return
    config = _read_config(page)
    page.v168_guide_config = config
    overlay.set_config(config)
    active = sum(bool(config[key]) for key in (
        "grid_enabled", "thirds_enabled", "center_enabled", "safe_area_enabled"
    ))
    page.v168_guides_status.setText(
        "Guias desativadas · não aparecem na arte exportada."
        if not active else f"{active} recurso(s) visual(is) ativo(s) · ignorados na exportação."
    )


def _clear_guides(page) -> None:
    for control in (
        page.v168_grid_enabled,
        page.v168_thirds_enabled,
        page.v168_center_enabled,
        page.v168_safe_enabled,
    ):
        control.setChecked(False)
    _sync_guides(page)


def _install_guides_tab(page) -> None:
    if getattr(page, "_v168_guides_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    if tabs.findChild(QWidget, "artStudioGuidesTabPageV168") is not None:
        page._v168_guides_installed = True
        return

    tab = QWidget(tabs)
    tab.setObjectName("artStudioGuidesTabPageV168")
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(10, 10, 10, 14)
    layout.setSpacing(8)

    title = QLabel("GUIAS E PRECISÃO", tab)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel(
        "Use referências visuais para alinhar textos, imagens e componentes. "
        "As guias ficam sobre o canvas, não viram camadas e não aparecem na arte exportada.",
        tab,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(hint)

    grid_card = QFrame(tab)
    grid_card.setObjectName("artStudioGuidesCardV168")
    grid_form = QFormLayout(grid_card)
    grid_form.setContentsMargins(10, 10, 10, 10)
    grid_form.setVerticalSpacing(8)
    page.v168_grid_enabled = QCheckBox("Mostrar grade", grid_card)
    page.v168_grid_step = QComboBox(grid_card)
    for step in (10, 20, 50, 100, 200):
        page.v168_grid_step.addItem(f"{step} px", step)
    page.v168_grid_step.setCurrentIndex(2)
    grid_form.addRow(page.v168_grid_enabled)
    grid_form.addRow("Espaçamento da grade", page.v168_grid_step)
    layout.addWidget(grid_card)

    composition_card = QFrame(tab)
    composition_card.setObjectName("artStudioCompositionGuidesCardV168")
    composition_layout = QVBoxLayout(composition_card)
    composition_layout.setContentsMargins(10, 10, 10, 10)
    composition_layout.setSpacing(8)
    comp_title = QLabel("COMPOSIÇÃO", composition_card)
    comp_title.setObjectName("artStudioSectionHeading")
    page.v168_thirds_enabled = QCheckBox("Divisões em terços", composition_card)
    page.v168_center_enabled = QCheckBox("Linha central horizontal e vertical", composition_card)
    composition_layout.addWidget(comp_title)
    composition_layout.addWidget(page.v168_thirds_enabled)
    composition_layout.addWidget(page.v168_center_enabled)
    layout.addWidget(composition_card)

    safe_card = QFrame(tab)
    safe_layout = QVBoxLayout(safe_card)
    safe_layout.setContentsMargins(10, 10, 10, 10)
    safe_layout.setSpacing(8)
    safe_title = QLabel("MARGENS SEGURAS", safe_card)
    safe_title.setObjectName("artStudioSectionHeading")
    page.v168_safe_enabled = QCheckBox("Mostrar margem interna de 5%", safe_card)
    safe_hint = QLabel(
        "Ajuda a manter títulos, logotipos e informações importantes afastados das bordas.",
        safe_card,
    )
    safe_hint.setObjectName("artStudioSectionHint")
    safe_hint.setWordWrap(True)
    safe_layout.addWidget(safe_title)
    safe_layout.addWidget(page.v168_safe_enabled)
    safe_layout.addWidget(safe_hint)
    layout.addWidget(safe_card)

    page.v168_guides_status = QLabel("Guias desativadas · não aparecem na arte exportada.", tab)
    page.v168_guides_status.setObjectName("artStudioSectionHint")
    page.v168_guides_status.setWordWrap(True)
    layout.addWidget(page.v168_guides_status)

    page.v168_clear_button = QPushButton("Ocultar todas as guias", tab)
    page.v168_clear_button.setProperty("secondary", True)
    page.v168_clear_button.clicked.connect(lambda: _clear_guides(page))
    layout.addWidget(page.v168_clear_button)
    layout.addStretch(1)

    page.v168_guides_overlay = _GuidesOverlay(page)
    for control in (
        page.v168_grid_enabled,
        page.v168_grid_step,
        page.v168_thirds_enabled,
        page.v168_center_enabled,
        page.v168_safe_enabled,
    ):
        signal = getattr(control, "toggled", None)
        if signal is not None:
            signal.connect(lambda *_args: _sync_guides(page))
        else:
            control.currentIndexChanged.connect(lambda *_args: _sync_guides(page))
    tabs.addTab(tab, "▦  Guias")
    page.v168_guides_tab = tab
    page._v168_guides_installed = True
    _sync_guides(page)


def enhance_art_studio_page_v168(page) -> None:
    if getattr(page, "_v168_installed", False):
        return
    _install_guides_tab(page)
    if getattr(page, "_v168_guides_installed", False):
        page._v168_installed = True
        page.status_label.setText(
            "V168: grade de precisão, divisões em terços, linha central e margens seguras no canvas."
        )


def install_art_studio_v168() -> None:
    """Instala as guias visuais depois do estúdio tipográfico V167."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v168_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v168(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v168(page)

    MainWindow.__init__ = init_with_v168
    MainWindow._v168_integration_installed = True
