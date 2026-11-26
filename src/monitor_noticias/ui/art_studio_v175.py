from __future__ import annotations

"""V175 — bancada premium e ferramentas contextuais do Central Studio.

A camada adiciona recolhimento independente dos painéis, prévias leves das
páginas e uma barra contextual sobre o canvas. Não recria a cena, não substitui
os serializadores e utiliza os comandos já existentes no editor.
"""

import weakref

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPalette,
    QPushButton,
    QSplitter,
    QTabBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import CANVAS_BG_KEY, ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_transform_engine_v172 import selected_roots
from monitor_noticias.ui.art_studio_workspace_engine_v175 import (
    contextual_actions,
    splitter_sizes_for_visibility,
    thumbnail_dimensions,
)


_INSTALLED = False


def _palette(theme: str) -> dict[str, str]:
    if theme == "escuro":
        return {
            "pasteboard": "#0D1722",
            "panel": "#142334",
            "panel_alt": "#1A2D40",
            "border": "#2B4054",
            "text": "#EDF3F7",
            "muted": "#9AABBA",
            "accent": "#D7B56D",
            "accent_text": "#182A3A",
            "signal": "#4CC5C7",
            "field": "#1B3044",
            "hover": "#223B50",
            "danger": "#A94D59",
        }
    return {
        "pasteboard": "#E9EFF4",
        "panel": "#FCFDFE",
        "panel_alt": "#F3F6F9",
        "border": "#D5DFE7",
        "text": "#1B3448",
        "muted": "#718596",
        "accent": "#B18B43",
        "accent_text": "#FFFFFF",
        "signal": "#168E98",
        "field": "#FFFFFF",
        "hover": "#E8F0F4",
        "danger": "#B74B56",
    }


def _visual_stylesheet(theme: str) -> str:
    c = _palette(theme)
    return f"""
    QWidget#artStudioPage {{ background:{c['pasteboard']}; color:{c['text']}; font-family:"Segoe UI"; }}
    QFrame#artStudioToolbar {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:12px; }}
    QFrame#artStudioPanel {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:12px; }}
    QFrame#artStudioWorkspace {{ background:{c['pasteboard']}; border:1px solid {c['border']}; border-radius:14px; }}
    QGraphicsView#artCanvasView {{ background:{c['pasteboard']}; border:0; border-radius:10px; outline:0; }}
    QLabel#artPanelTitle {{ color:{c['muted']}; border:0; border-bottom:1px solid {c['border']}; padding:3px 2px 8px 2px; font-size:10px; font-weight:900; letter-spacing:1px; }}
    QLabel#artStudioBrandTitle {{ color:{c['text']}; font-size:13px; font-weight:950; letter-spacing:1px; }}
    QLabel#artStudioBrandSub {{ color:{c['muted']}; font-size:7px; font-weight:800; letter-spacing:1.1px; }}
    QLabel#artStudioSectionHeading {{ color:{c['text']}; font-size:10px; font-weight:900; letter-spacing:.5px; }}
    QLabel#artStudioSectionHint {{ color:{c['muted']}; font-size:9px; }}
    QTabWidget#artStudioElementsTabs::pane, QTabWidget#artStudioInspectorTabs::pane {{ background:{c['panel_alt']}; border:1px solid {c['border']}; border-radius:9px; top:-1px; }}
    QTabBar::tab {{ background:{c['panel_alt']}; color:{c['muted']}; border:1px solid transparent; border-radius:6px; padding:6px 8px; margin:1px; min-height:22px; font-size:9px; font-weight:850; }}
    QTabBar::tab:selected {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; border-bottom:2px solid {c['signal']}; }}
    QWidget#artStudioPage QTabWidget::pane {{ border:1px solid {c['border']}; }}
    QWidget#artStudioPage QTabBar::tab {{ border:1px solid transparent; }}
    QWidget#artStudioPage QTabBar::tab:selected {{ border:1px solid {c['border']}; border-bottom:2px solid {c['signal']}; }}
    QTabBar::tab:hover {{ background:{c['hover']}; color:{c['text']}; }}
    QPushButton {{ min-height:30px; border-radius:7px; padding:4px 8px; font-size:9px; font-weight:750; }}
    QPushButton[secondary="true"] {{ background:{c['panel_alt']}; color:{c['text']}; border:1px solid {c['border']}; }}
    QPushButton[secondary="true"]:hover {{ background:{c['hover']}; border-color:{c['signal']}; }}
    QPushButton[gold="true"] {{ background:{c['accent']}; color:{c['accent_text']}; border:1px solid {c['accent']}; font-weight:900; }}
    QPushButton[gold="true"]:hover {{ background:{c['signal']}; border-color:{c['signal']}; color:#FFFFFF; }}
    QPushButton[danger="true"] {{ background:{c['panel']}; color:{c['danger']}; border:1px solid {c['border']}; }}
    QPushButton[danger="true"]:hover {{ background:{c['danger']}; color:#FFFFFF; border-color:{c['danger']}; }}
    QToolButton#artStudioPanelToggleV175 {{ background:{c['panel_alt']}; color:{c['muted']}; border:1px solid {c['border']}; border-radius:7px; padding:5px 8px; font-size:9px; font-weight:850; }}
    QToolButton#artStudioPanelToggleV175:checked {{ background:{c['hover']}; color:{c['text']}; border-color:{c['signal']}; }}
    QToolButton#artStudioPanelToggleV175:hover {{ border-color:{c['signal']}; color:{c['text']}; }}
    QListWidget#artLayersList {{ background:{c['panel_alt']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:8px; padding:4px; outline:0; }}
    QListWidget#artLayersList::item {{ min-height:28px; border-radius:5px; padding:3px 6px; margin:1px; }}
    QListWidget#artLayersList::item:selected {{ background:{c['signal']}; color:#FFFFFF; }}
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{ background:{c['field']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:7px; padding:5px 7px; min-height:23px; selection-background-color:{c['signal']}; }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{ border-color:{c['signal']}; }}
    QScrollBar:vertical {{ background:transparent; width:7px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{c['border']}; border-radius:3px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{c['signal']}; }}
    QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal {{ background:{c['border']}; border-radius:2px; margin:6px 1px; }}
    QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal:hover {{ background:{c['signal']}; }}
    QFrame#artStudioContextToolbarV175 {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:10px; }}
    QLabel#artStudioContextLabelV175 {{ color:{c['muted']}; font-size:9px; font-weight:900; padding:0 8px; }}
    QToolButton#artStudioContextActionV175 {{ background:transparent; color:{c['text']}; border:0; border-radius:6px; padding:6px 9px; font-size:9px; font-weight:800; }}
    QToolButton#artStudioContextActionV175:hover {{ background:{c['hover']}; color:{c['signal']}; }}
    QToolButton#artStudioContextDangerV175 {{ background:transparent; color:{c['danger']}; border:0; border-radius:6px; padding:6px 9px; font-size:9px; font-weight:850; }}
    QToolButton#artStudioContextDangerV175:hover {{ background:{c['danger']}; color:#FFFFFF; }}
    QMenu {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; padding:5px; }}
    QMenu::item {{ padding:7px 22px 7px 10px; border-radius:5px; font-size:9px; }}
    QMenu::item:selected {{ background:{c['hover']}; color:{c['signal']}; }}
    """


def _inside_art_studio(widget: QWidget) -> bool:
    current = widget
    while current is not None:
        if current.objectName() == "artStudioPage":
            return True
        current = current.parentWidget()
    return False


def _install_gold_border_exclusions() -> None:
    """Mantém contornos dourados no restante da Central, não no editor gráfico.

    O Estúdio usa sua própria hierarquia neutra/teal; a regra global da Central
    continua aplicada normalmente às demais páginas.
    """
    try:
        from monitor_noticias.ui import gold_borders_patch
    except Exception:
        return
    if getattr(gold_borders_patch, "_v175_art_studio_exclusions", False):
        return

    original_append = gold_borders_patch._append_page_rules
    original_force = gold_borders_patch._force_widget_border
    original_card = gold_borders_patch._is_card_frame

    def append_without_studio(widget):
        if _inside_art_studio(widget):
            return
        original_append(widget)

    def force_without_studio(widget):
        if _inside_art_studio(widget):
            return
        original_force(widget)

    def card_without_studio(widget):
        if _inside_art_studio(widget):
            return False
        return original_card(widget)

    gold_borders_patch._append_page_rules = append_without_studio
    gold_borders_patch._force_widget_border = force_without_studio
    gold_borders_patch._is_card_frame = card_without_studio
    gold_borders_patch._v175_art_studio_exclusions = True


def _wrap_theme_stylesheet() -> None:
    try:
        from monitor_noticias.ui import art_studio_v161
    except Exception:
        return
    if getattr(art_studio_v161, "_v175_skin_wrapped", False):
        return
    original = art_studio_v161._skin_stylesheet

    def stylesheet_with_v175(theme: str) -> str:
        return original(theme) + _visual_stylesheet(theme)

    art_studio_v161._skin_stylesheet = stylesheet_with_v175
    art_studio_v161._v175_skin_wrapped = True


def _theme_name(page) -> str:
    try:
        from monitor_noticias.ui import art_studio_v161
        return art_studio_v161._theme_id(page)
    except Exception:
        return "escuro" if page.palette().color(QPalette.ColorRole.Window).lightness() < 128 else "claro"


def _apply_theme(page, *, force: bool = False) -> None:
    theme = _theme_name(page)
    if not force and getattr(page, "_v175_active_theme", None) == theme:
        return
    try:
        from monitor_noticias.ui import art_studio_v161
        page.setStyleSheet(art_studio_v161._skin_stylesheet(theme))
    except Exception:
        page.setStyleSheet(_visual_stylesheet(theme))
    page._v175_active_theme = theme


def _page_items(page) -> list:
    try:
        selected = [
            item for item in page.scene.selectedItems()
            if not item.data(FRAME_CHILD_KEY)
            and item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
        ]
    except RuntimeError:
        return []
    return selected_roots(selected, lambda item: item.parentItem())


def _item_kind(item) -> str:
    if isinstance(item, QGraphicsTextItem):
        return "TEXTO"
    if isinstance(item, QGraphicsPixmapItem):
        return "IMAGEM"
    if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
        return "FORMA"
    if isinstance(item, QGraphicsItemGroup):
        return "GRUPO"
    return "OBJETO"


def _trigger_existing(page, name: str) -> None:
    button = getattr(page, name, None)
    if isinstance(button, QPushButton) and button.isEnabled():
        button.click()


def _select_inspector_tab(page, target_name: str) -> None:
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    target = page.findChild(QWidget, target_name)
    if target is None:
        return
    index = tabs.indexOf(target)
    if index >= 0:
        _set_panel_visible(page, "right", True)
        tabs.setCurrentIndex(index)


def _context_action(page, key: str) -> None:
    routes = {
        "duplicate": lambda: _trigger_existing(page, "duplicate_button"),
        "edit_text": lambda: _trigger_existing(page, "edit_text_button"),
        "delete": lambda: _trigger_existing(page, "delete_button"),
        "group": lambda: _trigger_existing(page, "v146_group_button"),
        "ungroup": lambda: _trigger_existing(page, "v146_ungroup_button"),
        "front": lambda: _trigger_existing(page, "forward_button"),
        "back": lambda: _trigger_existing(page, "backward_button"),
        "transform": lambda: _select_inspector_tab(page, "artStudioTransformTabV172"),
        "shape": lambda: _select_inspector_tab(page, "artStudioShapeTabV173"),
    }
    callback = routes.get(key)
    if callback is not None:
        callback()
    QTimer.singleShot(0, lambda: _sync_context_toolbar(page))


def _add_context_button(page, layout: QHBoxLayout, label: str, key: str, *, danger: bool = False):
    button = QToolButton(page.v175_context_toolbar)
    button.setObjectName("artStudioContextDangerV175" if danger else "artStudioContextActionV175")
    button.setText(label)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    button.clicked.connect(lambda _checked=False, action=key: _context_action(page, action))
    layout.addWidget(button)
    return button


def _install_context_toolbar(page) -> None:
    if getattr(page, "_v175_context_toolbar_installed", False):
        return
    view = getattr(page, "view", None)
    viewport = view.viewport() if view is not None else None
    if viewport is None:
        return
    frame = QFrame(viewport)
    frame.setObjectName("artStudioContextToolbarV175")
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    frame.setFrameShape(QFrame.Shape.NoFrame)
    row = QHBoxLayout(frame)
    row.setContentsMargins(6, 4, 6, 4)
    row.setSpacing(2)
    title = QLabel("OBJETO", frame)
    title.setObjectName("artStudioContextLabelV175")
    row.addWidget(title)
    row.addSpacing(4)
    page.v175_context_label = title
    buttons = {}
    buttons["duplicate"] = _add_context_button(page, row, "Duplicar", "duplicate")
    buttons["edit_text"] = _add_context_button(page, row, "Editar texto", "edit_text")
    buttons["transform"] = _add_context_button(page, row, "Transformar", "transform")
    buttons["shape"] = _add_context_button(page, row, "Forma", "shape")
    buttons["group"] = _add_context_button(page, row, "Agrupar", "group")
    buttons["ungroup"] = _add_context_button(page, row, "Desagrupar", "ungroup")
    more = QToolButton(frame)
    more.setObjectName("artStudioContextActionV175")
    more.setText("Mais  ▾")
    more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    more.setCursor(Qt.CursorShape.PointingHandCursor)
    menu = QMenu(more)
    more.setMenu(menu)
    row.addWidget(more)
    buttons["more"] = more
    buttons["delete"] = _add_context_button(page, row, "Excluir", "delete", danger=True)
    page.v175_context_menu = menu
    page.v175_context_buttons = buttons
    page.v175_context_toolbar = frame
    shadow = QGraphicsDropShadowEffect(frame)
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 4)
    shadow_color = QColor("#000000")
    shadow_color.setAlpha(55)
    shadow.setColor(shadow_color)
    frame.setGraphicsEffect(shadow)
    frame.hide()

    event_filter = _ContextToolbarViewportFilter(page, viewport)
    viewport.installEventFilter(event_filter)
    page.v175_context_view_filter = event_filter
    page.scene.selectionChanged.connect(lambda: _sync_context_toolbar(page))
    position_timer = QTimer(page)
    position_timer.setSingleShot(True)
    position_timer.setInterval(24)
    position_timer.timeout.connect(lambda ref=weakref.ref(page): _position_context_toolbar(ref))
    page.scene.changed.connect(lambda *_args: position_timer.start())
    page._v175_context_position_timer = position_timer
    layers = getattr(page, "layers", None)
    if layers is not None:
        layers.itemSelectionChanged.connect(lambda: _sync_context_toolbar(page))
    page._v175_context_toolbar_installed = True


class _ContextToolbarViewportFilter(QObject):
    def __init__(self, page, viewport):
        super().__init__(viewport)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        page_ref = self._page_ref
        if event.type() in (
            QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move,
            QEvent.Type.Wheel, QEvent.Type.Scroll,
        ):
            QTimer.singleShot(0, lambda ref=page_ref: _position_context_toolbar(ref))
        elif event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.FocusIn):
            def refresh(ref=page_ref):
                page = ref()
                if page is not None:
                    _sync_context_toolbar(page)
                    _position_context_toolbar(ref)
            QTimer.singleShot(0, refresh)
        return False


def _position_context_toolbar(page_ref) -> None:
    page = page_ref()
    if page is None:
        return
    toolbar = getattr(page, "v175_context_toolbar", None)
    view = getattr(page, "view", None)
    if toolbar is None or view is None or not toolbar.isVisible():
        return
    viewport = view.viewport()
    toolbar.adjustSize()
    available_width = max(120, viewport.width() - 16)
    width = min(toolbar.sizeHint().width(), available_width)
    toolbar.setMaximumWidth(width)
    toolbar.adjustSize()
    items = _page_items(page)
    if items:
        rect = items[0].sceneBoundingRect()
        for item in items[1:]:
            rect = rect.united(item.sceneBoundingRect())
        center = view.mapFromScene(rect.center())
        top_left = view.mapFromScene(rect.topLeft())
        x = center.x() - toolbar.width() // 2
        y = top_left.y() - toolbar.height() - 12
    else:
        x = (viewport.width() - toolbar.width()) // 2
        y = 10
    x = max(8, min(x, viewport.width() - toolbar.width() - 8))
    if y < 8:
        y = 8
    y = min(y, max(8, viewport.height() - toolbar.height() - 8))
    toolbar.move(QPoint(x, y))
    toolbar.raise_()


def _has_locked_descendant(item) -> bool:
    stack = list(item.childItems())
    seen = set()
    while stack:
        child = stack.pop()
        marker = id(child)
        if marker in seen:
            continue
        seen.add(marker)
        if child.data(FRAME_CHILD_KEY):
            continue
        try:
            if bool(child.data(LOCKED_KEY)):
                return True
            stack.extend(child.childItems())
        except RuntimeError:
            continue
    return False


def _selection_is_editable(items) -> bool:
    for item in items:
        try:
            if bool(item.data(LOCKED_KEY)) or _has_locked_descendant(item):
                return False
        except RuntimeError:
            return False
    return bool(items)


def _sync_context_toolbar(page) -> None:
    toolbar = getattr(page, "v175_context_toolbar", None)
    if toolbar is None:
        return
    items = _page_items(page)
    focused = page.scene.focusItem()
    if isinstance(focused, QGraphicsTextItem) and focused.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        toolbar.hide()
        return
    if not items:
        toolbar.hide()
        return

    from PySide6.QtWidgets import QGraphicsTextItem as TextItem
    text_item = len(items) == 1 and isinstance(items[0], TextItem)
    shape_item = len(items) == 1 and isinstance(items[0], (QGraphicsRectItem, QGraphicsEllipseItem))
    group_item = len(items) == 1 and isinstance(items[0], QGraphicsItemGroup)
    group_button = getattr(page, "v146_group_button", None)
    ungroup_button = getattr(page, "v146_ungroup_button", None)
    editable = _selection_is_editable(items)
    action_names = contextual_actions(
        selection_count=len(items),
        has_text=text_item,
        has_shape=shape_item,
        has_group=group_item,
        can_group=bool(group_button is not None and group_button.isEnabled() and editable),
    )
    visible_keys = set(action_names)
    for key, button in page.v175_context_buttons.items():
        button.setVisible(key in visible_keys or (key == "more" and len(items) > 0))
        if key == "more":
            button.setEnabled(editable)
        elif key in {"duplicate", "edit_text", "transform", "shape", "group", "ungroup", "delete"}:
            button.setEnabled(editable)
    if not text_item:
        page.v175_context_buttons["edit_text"].hide()
    if not shape_item:
        page.v175_context_buttons["shape"].hide()
    if not group_item and len(items) <= 1:
        page.v175_context_buttons["ungroup"].hide()
    if len(items) <= 1:
        page.v175_context_buttons["group"].hide()

    if len(items) == 1:
        name = str(items[0].data(ITEM_NAME_KEY) or _item_kind(items[0]))[:28]
        page.v175_context_label.setText(f"{_item_kind(items[0])}  ·  {name}")
    else:
        page.v175_context_label.setText(f"{len(items)} OBJETOS SELECIONADOS")

    menu = page.v175_context_menu
    menu.clear()
    extra_actions = [
        ("front", "Trazer para frente", editable and hasattr(page, "forward_button")),
        ("back", "Enviar para trás", editable and hasattr(page, "backward_button")),
        ("group", "Agrupar seleção", len(items) > 1 and group_button is not None and editable),
        ("ungroup", "Desagrupar grupo", group_item and ungroup_button is not None and editable),
    ]
    for key, label, enabled in extra_actions:
        if enabled:
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, value=key: _context_action(page, value))
    toolbar.show()
    QTimer.singleShot(0, lambda: _position_context_toolbar(weakref.ref(page)))


def _panel_toggle_button(page, side: str, text: str, layout: QHBoxLayout, insert_at: int):
    button = QToolButton(page.findChild(QFrame, "artStudioToolbar"))
    button.setObjectName("artStudioPanelToggleV175")
    button.setText(text)
    button.setCheckable(True)
    button.setChecked(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip("Recolher ou mostrar o painel " + ("de elementos" if side == "left" else "de propriedades"))
    button.setMinimumHeight(30)
    button.setMaximumHeight(32)
    layout.insertWidget(insert_at, button)
    button.toggled.connect(lambda visible, key=side: _set_panel_visible(page, key, visible))
    return button


def _install_panel_toggles(page) -> None:
    if getattr(page, "_v175_panel_toggles_installed", False):
        return
    splitter = getattr(page, "_v162_workspace_splitter", None)
    panels = getattr(page, "_v162_workspace_panels", None)
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    if not isinstance(splitter, QSplitter) or not panels or len(panels) != 3 or layout is None:
        return

    page._v175_expanded_sizes = list(splitter.sizes()) or list(getattr(page, "_v174_applied_split_sizes", [228, 900, 318]))
    page.v175_left_panel_toggle = _panel_toggle_button(page, "left", "Elementos", layout, max(0, layout.count() - 2))
    page.v175_right_panel_toggle = _panel_toggle_button(page, "right", "Propriedades", layout, max(0, layout.count() - 2))
    page._v175_panel_toggles_installed = True


def _set_panel_visible(page, side: str, visible: bool) -> None:
    panels = getattr(page, "_v162_workspace_panels", None)
    splitter = getattr(page, "_v162_workspace_splitter", None)
    if not panels or not isinstance(splitter, QSplitter):
        return
    index = 0 if side == "left" else 2
    panel = panels[index]
    current = list(splitter.sizes())
    if visible and not panel.isHidden():
        return
    if not visible and not panel.isHidden() and not panels[0].isHidden() and not panels[2].isHidden():
        if len(current) == 3 and sum(current) > 0:
            page._v175_expanded_sizes = current
    panel.setVisible(bool(visible))
    for key, button in (("left", getattr(page, "v175_left_panel_toggle", None)), ("right", getattr(page, "v175_right_panel_toggle", None))):
        if button is not None and key == side:
            button.blockSignals(True)
            button.setChecked(bool(visible))
            button.blockSignals(False)
    QTimer.singleShot(0, lambda: _apply_visible_split_sizes(page))
    if getattr(page, "v175_context_toolbar", None) is not None:
        QTimer.singleShot(20, lambda: _position_context_toolbar(weakref.ref(page)))


def _apply_visible_split_sizes(page) -> None:
    splitter = getattr(page, "_v162_workspace_splitter", None)
    panels = getattr(page, "_v162_workspace_panels", None)
    if not isinstance(splitter, QSplitter) or not panels or len(panels) != 3:
        return
    left_visible = not panels[0].isHidden()
    right_visible = not panels[2].isHidden()
    visible_count = 1 + int(left_visible) + int(right_visible)
    available = max(0, splitter.width() - max(0, visible_count - 1) * splitter.handleWidth())
    sizes = splitter_sizes_for_visibility(
        available,
        getattr(page, "_v175_expanded_sizes", [228, 900, 318]),
        left_visible=left_visible,
        right_visible=right_visible,
    )
    splitter.setSizes(list(sizes))


def _render_page_thumbnail(page, page_index: int) -> None:
    tab_bar = getattr(page, "v150_tab_bar", None)
    pages = getattr(page, "_v150_pages", None)
    if not isinstance(tab_bar, QTabBar) or not isinstance(pages, list):
        return
    if page_index != getattr(page, "_v150_active_index", -1) or not 0 <= page_index < len(pages):
        return
    entry = pages[page_index]
    page_id = str(entry.get("id") or page_index)
    width = max(1, int(getattr(page, "_width", 1080)))
    height = max(1, int(getattr(page, "_height", 1080)))
    thumb_w, thumb_h = thumbnail_dimensions(width, height, max_width=48, max_height=34)

    colors = _palette(_theme_name(page))
    pixmap = QPixmap(58, 42)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QColor(colors["panel"]))
    painter.drawRoundedRect(QRectF(1, 1, 56, 40), 4, 4)

    overlays = []
    page._v175_rendering_thumbnail = True
    try:
        for name in ("_v150_grid_lines", "_v150_guide_lines", "_v148_handles", "_v173_handles"):
            for overlay in list(getattr(page, name, []) or []):
                try:
                    if overlay.scene() is page.scene:
                        overlays.append((overlay, overlay.isVisible()))
                        overlay.hide()
                except RuntimeError:
                    continue
        source = QRectF(0, 0, width, height)
        target = QRectF((58 - thumb_w) / 2, (42 - thumb_h) / 2, thumb_w, thumb_h)
        try:
            page.scene.render(painter, target, source, Qt.AspectRatioMode.KeepAspectRatio)
        except RuntimeError:
            return
        painter.setPen(QPen(QColor(colors["border"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(target.adjusted(-0.5, -0.5, 0.5, 0.5), 3, 3)
    finally:
        for overlay, was_visible in overlays:
            try:
                overlay.setVisible(was_visible)
            except RuntimeError:
                pass
        page._v175_rendering_thumbnail = False
        painter.end()

    page._v175_thumbnail_cache[page_id] = QIcon(pixmap)
    for index, item in enumerate(pages):
        icon = page._v175_thumbnail_cache.get(str(item.get("id") or index))
        tab_bar.setTabIcon(index, icon if icon is not None else QIcon())


def _install_page_thumbnails(page) -> None:
    if getattr(page, "_v175_thumbnails_installed", False):
        return
    tab_bar = getattr(page, "v150_tab_bar", None)
    if not isinstance(tab_bar, QTabBar):
        return
    page._v175_thumbnail_cache = {}
    tab_bar.setIconSize(QSize(40, 28))
    tab_bar.setMinimumHeight(30)
    tab_bar.setMaximumHeight(34)
    tab_bar.setStyleSheet(
        tab_bar.styleSheet()
        + "QTabBar::tab {padding:2px 7px;margin:1px;min-height:28px;font-size:9px;}"
        + "QTabBar::tab:selected {border-bottom:2px solid #168E98;}"
    )
    timer = QTimer(page)
    timer.setSingleShot(True)
    timer.setInterval(700)
    timer.timeout.connect(lambda: _render_page_thumbnail(page, getattr(page, "_v150_active_index", 0)))
    page._v175_thumbnail_timer = timer

    def schedule_thumbnail(*_args):
        if not getattr(page, "_v175_rendering_thumbnail", False):
            timer.start()

    page.scene.changed.connect(schedule_thumbnail)

    def before_switch(_new_index: int) -> None:
        old_index = getattr(page, "_v150_active_index", -1)
        if 0 <= old_index < len(getattr(page, "_v150_pages", [])):
            _render_page_thumbnail(page, old_index)
        QTimer.singleShot(100, lambda: _render_page_thumbnail(page, getattr(page, "_v150_active_index", 0)))

    tab_bar.currentChanged.connect(before_switch)
    tab_bar.tabMoved.connect(lambda *_args: QTimer.singleShot(0, lambda: _render_page_thumbnail(page, getattr(page, "_v150_active_index", 0))))
    tab_bar.tabCloseRequested.connect(lambda *_args: QTimer.singleShot(160, lambda: _render_page_thumbnail(page, getattr(page, "_v150_active_index", 0))))
    page._v175_thumbnails_installed = True
    QTimer.singleShot(500, lambda: _render_page_thumbnail(page, getattr(page, "_v150_active_index", 0)))


def _install_visual_refinements(page) -> None:
    _apply_theme(page, force=True)
    left_tabs = getattr(page, "_v161_left_tabs", None)
    right_tabs = getattr(page, "_v161_inspector_tabs", None)
    for tabs in (left_tabs, right_tabs):
        if isinstance(tabs, QTabWidget):
            tabs.tabBar().setUsesScrollButtons(True)
            tabs.tabBar().setExpanding(False)
            tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)
            tabs.tabBar().setDrawBase(False)
    for heading in page.findChildren(QLabel, "artPanelTitle"):
        if heading.text().strip().upper() == "CAMADAS E OBJETOS":
            heading.setText("PROPRIEDADES")
        elif heading.text().strip().upper() == "ELEMENTOS":
            heading.setText("ELEMENTOS")

    for button in page.findChildren(QPushButton):
        button.setMinimumHeight(min(button.minimumHeight() or 30, 36))
        button.setStyleSheet(
            button.styleSheet() +
            "QPushButton {font-family:'Segoe UI';font-size:9px;padding:5px 9px;border-radius:7px;}"
        )
    for tabs_name in ("_v161_left_tabs", "_v161_inspector_tabs"):
        tabs = getattr(page, tabs_name, None)
        if isinstance(tabs, QTabWidget):
            tabs.tabBar().setMinimumHeight(30)
            tabs.tabBar().setMaximumHeight(34)
            tabs.tabBar().setStyleSheet(
                tabs.tabBar().styleSheet() +
                "QTabBar::tab {font-family:'Segoe UI';font-size:9px;padding:6px 8px;border-color:transparent;}"
                "QTabBar::tab:selected {border:1px solid #9AAEBD;border-bottom:2px solid #168E98;}"
            )
    for button_name in ("save_button", "export_button"):
        button = getattr(page, button_name, None)
        if isinstance(button, QPushButton):
            button.setProperty("gold", True)
            button.style().unpolish(button)
            button.style().polish(button)


def _install_theme_filter(page) -> None:
    if getattr(page, "_v175_theme_filter_installed", False):
        return
    filt = _V175ThemeFilter(page)
    page._v175_theme_filter = filt
    page.installEventFilter(filt)
    owner = page.window()
    if owner is not None:
        owner.installEventFilter(filt)
    page._v175_theme_filter_installed = True


class _V175ThemeFilter(QObject):
    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange, QEvent.Type.StyleChange):
            page_ref = self._page_ref
            # Reaplica à força depois do tema global, que percorre os widgets
            # e pode transformar a folha de estilo local do Estúdio.
            QTimer.singleShot(0, lambda ref=page_ref: _apply_theme_from_ref(ref, force=True))
        return False


def _apply_theme_from_ref(page_ref, *, force: bool = False) -> None:
    page = page_ref()
    if page is not None:
        _apply_theme(page, force=force)


def enhance_art_studio_page_v175(page) -> None:
    if getattr(page, "_v175_installed", False):
        return
    _install_visual_refinements(page)
    _install_panel_toggles(page)
    _install_context_toolbar(page)
    _install_page_thumbnails(page)
    _install_theme_filter(page)
    page._v175_installed = True
    page.status_label.setText(
        "Central Studio V175: identidade visual refinada, painéis recolhíveis, miniaturas e ações contextuais."
    )


def install_art_studio_v175() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _wrap_theme_stylesheet()
    _install_gold_border_exclusions()
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v175_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v175(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v175(page)
            page_ref = weakref.ref(page)
            # A aplicação instala o tema global e o filtro das bordas após criar
            # a janela. Reaplicamos a folha específica do Estúdio depois disso.
            QTimer.singleShot(450, lambda ref=page_ref: _apply_theme_from_ref(ref, force=True))

    MainWindow.__init__ = init_with_v175
    MainWindow._v175_integration_installed = True
    _INSTALLED = True
