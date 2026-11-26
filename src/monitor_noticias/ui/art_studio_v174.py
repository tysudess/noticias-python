from __future__ import annotations

import weakref

"""V174 — bancada compacta, canvas ampliado e faixa de páginas recolhível.

Ajusta a arquitetura existente sem reconstruir a cena: remove apenas o rodapé
informativo global, compacta a faixa multipágina, reduz os painéis laterais e
prioriza a área central. Os comandos de status internos do editor permanecem.
"""

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolButton,
    QWidget,
)

from monitor_noticias.ui.art_studio_layout_engine_v174 import (
    compact_pages_bar_metrics,
    workspace_split_sizes,
)


_INSTALLED = False


def _theme_tokens(page) -> dict[str, str]:
    dark = False
    try:
        from monitor_noticias.ui import art_studio_v161
        dark = art_studio_v161._theme_id(page) == "escuro"
    except Exception:
        dark = page.palette().color(QPalette.ColorRole.Window).lightness() < 128
    if dark:
        return {
            "panel": "#10263A",
            "panel_alt": "#142F45",
            "border": "#304F66",
            "text": "#F0F4F7",
            "muted": "#9CB0C0",
            "accent": "#D7B56D",
            "accent_text": "#14283A",
            "hover": "#203F57",
        }
    return {
        "panel": "#FFFFFF",
        "panel_alt": "#F7F9FC",
        "border": "#D4DEE7",
        "text": "#17344A",
        "muted": "#6E8293",
        "accent": "#A98239",
        "accent_text": "#FFFFFF",
        "hover": "#EAF0F5",
    }


def _find_layout_containing(layout: QLayout | None, widget: QWidget):
    if layout is None:
        return None
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is None:
            continue
        if item.widget() is widget:
            return layout
        child_layout = item.layout()
        if child_layout is not None:
            found = _find_layout_containing(child_layout, widget)
            if found is not None:
                return found
        child_widget = item.widget()
        if child_widget is not None and child_widget.layout() is not None:
            found = _find_layout_containing(child_widget.layout(), widget)
            if found is not None:
                return found
    return None


def _hide_global_footer(window) -> None:
    """Retira o rodapé global em todas as páginas sem afetar o status do editor."""
    if getattr(window, "_v174_global_footer_hidden", False):
        return
    left = getattr(window, "footer_left", None)
    right = getattr(window, "footer_right", None)
    widgets = [w for w in (left, right) if isinstance(w, QWidget)]
    if not widgets:
        window._v174_global_footer_hidden = True
        return

    root = window.centralWidget().layout() if window.centralWidget() else None
    footer_layout = _find_layout_containing(root, widgets[0]) if widgets else None
    for widget in widgets:
        widget.hide()
        widget.setMinimumSize(0, 0)
        widget.setMaximumSize(0, 0)
        policy = widget.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
        policy.setVerticalPolicy(QSizePolicy.Policy.Ignored)
        widget.setSizePolicy(policy)
        if footer_layout is not None:
            footer_layout.removeWidget(widget)
            widget.setParent(None)

    if footer_layout is not None:
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(0)
    window._v174_global_footer_hidden = True


def _compact_main_window(window) -> None:
    if getattr(window, "_v174_main_window_compacted", False):
        return
    _hide_global_footer(window)
    window._v174_main_window_compacted = True


def _compact_pages_bar(page) -> None:
    bar = getattr(page, "v150_pages_bar", None)
    if not isinstance(bar, QFrame):
        return
    colors = _theme_tokens(page)
    metrics = compact_pages_bar_metrics(expanded=True)
    bar.setStyleSheet(
        f"QFrame#artStudioPagesBar {{background:{colors['panel_alt']};"
        f"border:1px solid {colors['border']};border-radius:9px;}}"
    )
    bar.setMinimumHeight(metrics["height"])
    bar.setMaximumHeight(metrics["height"])
    bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    row = bar.layout()
    if row is not None:
        row.setContentsMargins(
            metrics["horizontal_margin"], metrics["vertical_margin"],
            metrics["horizontal_margin"], metrics["vertical_margin"],
        )
        row.setSpacing(metrics["spacing"])

    tab_bar = getattr(page, "v150_tab_bar", None)
    if tab_bar is not None:
        tab_bar.setMinimumHeight(27)
        tab_bar.setMaximumHeight(31)
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
        tab_bar.setStyleSheet(
            "QTabBar::tab {"
            f"background:{colors['panel_alt']};color:{colors['text']};"
            f"border:1px solid {colors['border']};border-radius:6px;"
            "padding:4px 9px;margin:1px;font-size:8px;font-weight:800;min-height:20px;"
            "}"
            "QTabBar::tab:selected {"
            f"background:{colors['accent']};color:{colors['accent_text']};"
            f"border-color:{colors['accent']};"
            "}"
            "QTabBar::tab:hover {"
            f"background:{colors['hover']};"
            "}"
        )

    title = next((child for child in bar.findChildren(QLabel) if child.text().strip().upper() == "PÁGINAS"), None)
    if title is not None:
        title.setText("Páginas")
        title.setStyleSheet(f"color:{colors['muted']};font-size:8px;font-weight:900;letter-spacing:.5px;")
        title.setMaximumWidth(48)

    for name in (
        "v150_add_page_button", "v150_duplicate_page_button",
        "v150_rename_page_button", "v150_export_pages_button",
    ):
        button = getattr(page, name, None)
        if isinstance(button, QPushButton):
            button.setMinimumHeight(metrics["button_height"])
            button.setMaximumHeight(metrics["button_height"])
            button.setMinimumWidth(54 if name != "v150_export_pages_button" else 82)
            button.setMaximumWidth(112)
            button.setStyleSheet(
                f"QPushButton {{font-size:8px;padding:3px 7px;border-radius:7px;"
                f"border:1px solid {colors['border']};background:{colors['panel']};color:{colors['text']};}}"
                f"QPushButton:hover {{border-color:{colors['accent']};background:{colors['hover']};}}"
            )

    for check in (getattr(page, "v150_grid_check", None), getattr(page, "v150_snap_check", None)):
        if isinstance(check, QCheckBox):
            check.setMinimumHeight(24)
            check.setMaximumHeight(27)
            check.setStyleSheet(f"QCheckBox {{color:{colors['text']};font-size:8px;spacing:4px;}}")

    count = getattr(page, "v150_page_count_label", None)
    if isinstance(count, QLabel):
        count.setStyleSheet(f"color:{colors['muted']};font-size:8px;font-weight:800;")
        count.setMinimumWidth(48)

    page._v174_pages_bar_compact = True


def _style_pages_toggle(page) -> None:
    toggle = getattr(page, "v174_pages_toggle", None)
    if not isinstance(toggle, QToolButton):
        return


def _refresh_theme_styles(page_ref) -> None:
    page = page_ref()
    if page is None:
        return
    _compact_pages_bar(page)
    _refine_inspector_tabs(page)
    _style_pages_toggle(page)


class _V174ThemeFilter(QObject):
    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):  # noqa: N802 - assinatura Qt
        if event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ApplicationPaletteChange,
        }:
            QTimer.singleShot(0, lambda ref=self._page_ref: _refresh_theme_styles(ref))
        return False


def _install_pages_toggle(page) -> None:
    if getattr(page, "_v174_pages_toggle_installed", False):
        return
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    bar = getattr(page, "v150_pages_bar", None)
    if layout is None or not isinstance(bar, QFrame):
        return

    toggle = QToolButton(toolbar)
    toggle.setText("Páginas")
    toggle.setToolTip("Mostrar ou recolher a faixa de páginas")
    toggle.setCheckable(True)
    toggle.setChecked(True)
    toggle.setCursor(Qt.CursorShape.PointingHandCursor)
    toggle.setMinimumSize(58, 30)
    toggle.setMaximumHeight(32)
    project_label = getattr(page, "project_label", None)
    index = layout.indexOf(project_label) if project_label is not None else -1
    if index >= 0:
        layout.insertWidget(index, toggle)
    else:
        layout.addWidget(toggle)

    def set_pages_visible(visible: bool) -> None:
        bar.setVisible(bool(visible))
        toggle.setText("Páginas" if visible else "Páginas +")
        page.updateGeometry()
        if visible:
            QTimer.singleShot(0, lambda: _compact_pages_bar(page))

    toggle.toggled.connect(set_pages_visible)
    page.v174_pages_toggle = toggle
    page._v174_pages_toggle_installed = True
    _style_pages_toggle(page)


def _refine_inspector_tabs(page) -> None:
    colors = _theme_tokens(page)
    for name in ("_v161_inspector_tabs", "_v161_left_tabs"):
        tabs = getattr(page, name, None)
        if not isinstance(tabs, QTabWidget):
            continue
        bar = tabs.tabBar()
        bar.setUsesScrollButtons(True)
        bar.setExpanding(False)
        bar.setElideMode(Qt.TextElideMode.ElideRight)
        bar.setDrawBase(False)
        bar.setStyleSheet(
            "QTabBar::tab {"
            f"background:{colors['panel_alt']};color:{colors['muted']};border:1px solid {colors['border']};"
            "border-radius:6px;padding:5px 6px;margin:1px;font-size:8px;font-weight:850;min-height:21px;"
            "}"
            "QTabBar::tab:selected {"
            f"background:{colors['panel']};color:{colors['text']};border:1px solid {colors['accent']};"
            "}"
        )

    # Nomes curtos evitam que a navegação lateral seja cortada.
    aliases = {
        "⇄  Composição": "Compor",
        "♧  Proteção": "Proteção",
        "⌗  Transformar": "Transformar",
        "⧉  Encaixe": "Encaixe",
    }
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if isinstance(tabs, QTabWidget):
        for index in range(tabs.count()):
            current = tabs.tabText(index)
            if current in aliases:
                tabs.setTabText(index, aliases[current])


def _compact_editor_toolbar(page) -> None:
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    if not isinstance(toolbar, QFrame):
        return
    toolbar.setMinimumHeight(52)
    toolbar.setMaximumHeight(56)
    layout = toolbar.layout()
    if layout is not None:
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(5)
    for button in toolbar.findChildren(QPushButton):
        button.setMinimumHeight(30)
        button.setMaximumHeight(33)
        button.setStyleSheet(
            button.styleSheet()
            + "QPushButton {font-size:8px;padding:4px 8px;border-radius:7px;}"
        )
    project_label = getattr(page, "project_label", None)
    if isinstance(project_label, QLabel):
        project_label.setMinimumHeight(30)
        project_label.setMaximumHeight(34)
        project_label.setMinimumWidth(120)
        project_label.setMaximumWidth(220)


def _refine_workspace(page) -> None:
    if getattr(page, "_v174_workspace_refined", False):
        return
    root = page.layout()
    if root is not None:
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
    _compact_editor_toolbar(page)
    panels = getattr(page, "_v162_workspace_panels", None)
    splitter = getattr(page, "_v162_workspace_splitter", None)
    if panels and len(panels) == 3 and isinstance(splitter, QSplitter):
        left, center, right = panels
        left.setMinimumWidth(184)
        left.setMaximumWidth(258)
        center.setMinimumWidth(560)
        right.setMinimumWidth(246)
        right.setMaximumWidth(348)
        splitter.setHandleWidth(5)
        splitter.setChildrenCollapsible(False)

        def apply_sizes() -> None:
            total = max(0, splitter.width() - 2 * splitter.handleWidth())
            if total <= 0:
                return
            sizes = workspace_split_sizes(total)
            splitter.setSizes(list(sizes))
            page._v174_applied_split_sizes = list(sizes)

        page._v174_apply_split_sizes = apply_sizes
        QTimer.singleShot(0, apply_sizes)
        QTimer.singleShot(160, apply_sizes)

    workspace = page.findChild(QFrame, "artStudioWorkspace")
    if workspace is not None:
        workspace.setContentsMargins(5, 5, 5, 5)

    for name in (
        "add_image_button", "add_text_button", "add_rect_button",
        "add_ellipse_button", "background_button", "templates_button",
    ):
        button = getattr(page, name, None)
        if isinstance(button, QPushButton):
            button.setMinimumHeight(31)
            button.setMaximumHeight(36)

    for button in page.findChildren(QPushButton):
        if button.objectName() in {"artStudioDeleteLayersV170", "artStudioApplyTransformV172"}:
            button.setMinimumHeight(30)
            button.setMaximumHeight(34)

    for scroll in page.findChildren(QWidget):
        if scroll.objectName() in {"artStudioElementsScroll", "artStudioLayersScroll", "artStudioTabScrollV171"}:
            from PySide6.QtWidgets import QScrollArea
            if isinstance(scroll, QScrollArea):
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setWidgetResizable(True)

    # O status textual antigo ocupava uma linha fixa no rodapé do editor.
    # As mensagens continuam sendo atualizadas internamente, mas a faixa
    # visual desaparece para devolver essa altura ao canvas.
    status = getattr(page, "status_label", None)
    if isinstance(status, QLabel):
        status.hide()
        status.setMinimumSize(0, 0)
        status.setMaximumSize(0, 0)
        policy = status.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Ignored)
        status.setSizePolicy(policy)

    _refine_inspector_tabs(page)
    page._v174_workspace_refined = True


def enhance_art_studio_page_v174(page) -> None:
    if getattr(page, "_v174_installed", False):
        return
    _compact_pages_bar(page)
    _install_pages_toggle(page)
    _refine_workspace(page)
    theme_filter = _V174ThemeFilter(page)
    page._v174_theme_filter = theme_filter
    page.installEventFilter(theme_filter)
    owner = page.window()
    if owner is not None:
        owner.installEventFilter(theme_filter)
    page._v174_installed = True
    page.status_label.setText(
        "Central Studio V174: bancada compacta, canvas ampliado e faixa de páginas recolhível."
    )


def install_art_studio_v174() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v174_integration_installed", False):
        _INSTALLED = True
        return

    original_init = MainWindow.__init__

    def init_with_v174(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _compact_main_window(self)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v174(page)

    MainWindow.__init__ = init_with_v174
    MainWindow._v174_integration_installed = True
    _INSTALLED = True
