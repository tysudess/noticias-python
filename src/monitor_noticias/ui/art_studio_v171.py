from __future__ import annotations

"""V171 — refinamento de bancada e sistema visual autoral do Estúdio.

Organiza o espaço em três zonas de trabalho com melhor hierarquia, abas
roláveis, controles compactos e identidade própria marinho/bronze. Os widgets
funcionais são movidos, não recriados; a cena, a seleção e .centralart ficam
intactos. O código acrescenta o refinamento ao tema V161, inclusive após troca
entre tema claro e escuro.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QTabWidget, QVBoxLayout, QWidget

import monitor_noticias.ui.art_studio_v161 as v161


_INSTALLED = False


def _visual_stylesheet(theme: str) -> str:
    dark = theme == "escuro"
    panel = "#10263A" if dark else "#FFFFFF"
    panel_alt = "#142F45" if dark else "#F7F9FC"
    border = "#304F66" if dark else "#D4DEE7"
    accent = "#D7B56D" if dark else "#A98239"
    text = "#F0F4F7" if dark else "#17344A"
    muted = "#9CB0C0" if dark else "#6E8293"
    canvas_frame = "#0C1A28" if dark else "#E7EDF2"
    hover = "#203F57" if dark else "#EAF0F5"
    return f"""
    QFrame#artStudioToolbar {{ background:{panel}; border:1px solid {border}; border-radius:13px; }}
    QFrame#artStudioPanel {{ background:{panel}; border:1px solid {border}; border-radius:13px; }}
    QFrame#artStudioWorkspace {{ background:{canvas_frame}; border:1px solid {border}; border-radius:15px; }}
    QLabel#artStudioBrandTitle {{ color:{text}; font-size:13px; font-weight:950; letter-spacing:1.1px; }}
    QLabel#artStudioBrandSub {{ color:{muted}; font-size:8px; font-weight:800; letter-spacing:1.1px; }}
    QLabel#artStudioSectionHeading {{ color:{text}; font-size:11px; font-weight:950; letter-spacing:0.8px; }}
    QLabel#artStudioSectionHint {{ color:{muted}; font-size:9px; line-height:1.35; }}
    QTabWidget#artStudioElementsTabs::pane, QTabWidget#artStudioInspectorTabs::pane {{
        background:{panel_alt}; border:1px solid {border}; border-radius:10px; top:-1px;
    }}
    QTabBar::tab {{
        background:{panel_alt}; color:{muted}; border:1px solid {border};
        border-bottom:0; border-top-left-radius:8px; border-top-right-radius:8px;
        padding:9px 11px; margin-right:3px; min-height:21px; font-size:9px; font-weight:850;
    }}
    QTabBar::tab:selected {{ background:{panel}; color:{text}; border-color:{accent}; border-bottom:2px solid {accent}; }}
    QTabBar::tab:hover {{ background:{hover}; color:{text}; }}
    QScrollArea#artStudioTabScrollV171 {{ background:transparent; border:0; }}
    QScrollBar:vertical {{ background:transparent; width:7px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{border}; border-radius:3px; min-height:24px; }}
    QScrollBar::handle:vertical:hover {{ background:{accent}; }}
    QScrollBar:horizontal {{ background:transparent; height:7px; margin:2px; }}
    QScrollBar::handle:horizontal {{ background:{border}; border-radius:3px; min-width:24px; }}
    QPushButton {{ min-height:34px; border-radius:8px; padding:6px 10px; font-size:9px; font-weight:800; }}
    QPushButton[secondary="true"] {{ background:{panel_alt}; color:{text}; border:1px solid {border}; }}
    QPushButton[secondary="true"]:hover {{ background:{hover}; border-color:{accent}; }}
    QPushButton[danger="true"] {{ background:{'#702E39' if dark else '#F8E9EA'}; color:{'#FFFFFF' if dark else '#8C2735'}; border:1px solid {('#A94E59' if dark else '#D7A6AB')}; }}
    QFrame#artStudioSelectionCardV162 {{ border:1px solid {accent}; border-radius:10px; }}
    QListWidget#artLayersList {{ background:{panel_alt}; border:1px solid {border}; border-radius:9px; padding:5px; }}
    QListWidget#artLayersList::item {{ min-height:30px; border-radius:6px; padding:4px 7px; }}
    QListWidget#artLayersList::item:selected {{ background:{accent}; color:{'#152A3A' if dark else '#FFFFFF'}; }}
    """


def _wrap_tab_content(tab: QWidget, index: int) -> bool:
    if tab is None or tab.property("v171Scrollable"):
        return False
    root_layout = tab.layout()
    if root_layout is None:
        return False
    if root_layout.count() == 1:
        only = root_layout.itemAt(0)
        if only is not None and isinstance(only.widget(), QScrollArea):
            tab.setProperty("v171Scrollable", True)
            return False

    content = QWidget()
    content.setObjectName(f"artStudioTabContentV171_{index}")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(3, 4, 7, 9)
    content_layout.setSpacing(8)

    moved = 0
    while root_layout.count():
        item = root_layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            content_layout.addWidget(widget)
            moved += 1
        elif child_layout is not None:
            content_layout.addLayout(child_layout)
            moved += 1
        else:
            content_layout.addItem(item)

    scroll = QScrollArea(tab)
    scroll.setObjectName("artStudioTabScrollV171")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(content)
    root_layout.addWidget(scroll)
    tab.setProperty("v171Scrollable", True)
    tab._v171_scroll_area = scroll
    return moved > 0


def _improve_tab_bars(tabs: QTabWidget) -> None:
    if tabs is None:
        return
    bar = tabs.tabBar()
    bar.setUsesScrollButtons(True)
    bar.setExpanding(False)
    bar.setElideMode(Qt.TextElideMode.ElideNone)
    bar.setDrawBase(False)
    for index in range(tabs.count()):
        tab = tabs.widget(index)
        _wrap_tab_content(tab, index)
        bar.setTabToolTip(index, bar.tabText(index).replace("  ", " "))


def _refine_workspace(page) -> None:
    panels = getattr(page, "_v162_workspace_panels", None)
    if panels and len(panels) == 3:
        left, center, right = panels
        left.setMinimumWidth(208)
        left.setMaximumWidth(292)
        right.setMinimumWidth(286)
        right.setMaximumWidth(388)
        center.setMinimumWidth(500)
        splitter = getattr(page, "_v162_workspace_splitter", None)
        if splitter is not None:
            splitter.setHandleWidth(7)
            splitter.setChildrenCollapsible(False)
            page._v171_splitter = splitter
            page._v162_default_split_sizes = [236, 720, 330]
    workspace = page.findChild(QFrame, "artStudioWorkspace")
    if workspace is not None:
        workspace.setContentsMargins(8, 8, 8, 8)
        page._v171_canvas_workspace = workspace

    # Mantém a biblioteca de criação compacta e os controles acessíveis.
    left_buttons = []
    for name in (
        "add_image_button", "add_text_button", "add_rect_button",
        "add_ellipse_button", "background_button", "templates_button",
    ):
        button = getattr(page, name, None)
        if button is not None:
            left_buttons.append(button)
            button.setMinimumHeight(36)
    for button in getattr(page, "v163_template_buttons", []) or []:
        button.setMinimumHeight(35)

    # A barra superior continua familiar, mas ganha hierarquia de ações.
    for name in ("new_button", "open_button", "save_button", "export_button"):
        button = getattr(page, name, None)
        if button is not None:
            button.setMinimumHeight(38)
    if getattr(page, "export_button", None) is not None:
        page.export_button.setToolTip("Exportar a composição em PNG, JPG ou PDF")

    # Destaca o canvas como área principal sem substituir ou renderizar a cena.
    if getattr(page, "view", None) is not None:
        page.view.setMinimumSize(440, 360)
        page.view.setViewportUpdateMode(page.view.ViewportUpdateMode.SmartViewportUpdate)


def _apply_page_refinement(page) -> None:
    theme = v161._theme_id(page)
    page.setStyleSheet(v161._skin_stylesheet(theme))
    _refine_workspace(page)


def enhance_art_studio_page_v171(page) -> None:
    if getattr(page, "_v171_installed", False):
        return
    left_tabs = getattr(page, "_v161_left_tabs", None)
    inspector_tabs = getattr(page, "_v161_inspector_tabs", None)
    if isinstance(left_tabs, QTabWidget):
        _improve_tab_bars(left_tabs)
    if isinstance(inspector_tabs, QTabWidget):
        _improve_tab_bars(inspector_tabs)
    _refine_workspace(page)
    _apply_page_refinement(page)
    page._v171_installed = True
    page.status_label.setText(
        "V171: bancada refinada, painéis roláveis, canvas priorizado e identidade visual própria da Central."
    )


def install_art_studio_v171() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    # O tema V161 pode ser reaplicado quando o usuário alterna claro/escuro.
    # Acrescentamos as regras autorais à função central de paleta, em vez de
    # aplicar uma folha isolada que seria perdida na próxima troca de tema.
    if not getattr(v161, "_v171_skin_extension_installed", False):
        original_stylesheet = v161._skin_stylesheet

        def stylesheet_with_v171(theme: str) -> str:
            return original_stylesheet(theme) + _visual_stylesheet(theme)

        v161._skin_stylesheet = stylesheet_with_v171
        v161._v171_skin_extension_installed = True

    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v171_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v171(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v171(page)

    MainWindow.__init__ = init_with_v171
    MainWindow._v171_integration_installed = True
    _INSTALLED = True
