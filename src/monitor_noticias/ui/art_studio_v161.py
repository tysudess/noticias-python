from __future__ import annotations

"""V161 — reformulação profissional da interface do Estúdio de Artes.

Organiza os controles existentes em áreas de trabalho e abas sem substituir
os widgets funcionais, suas conexões, o canvas ou o formato .centralart.
"""

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, weakref
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


_INSTALLED = False


def _widget_contains_any(widget: QWidget, targets: set[int]) -> bool:
    if id(widget) in targets:
        return True
    return any(id(child) in targets for child in widget.findChildren(QWidget))


def _layout_contains_any(layout: QLayout, targets: set[int]) -> bool:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None and _widget_contains_any(widget, targets):
            return True
        child_layout = item.layout()
        if child_layout is not None and _layout_contains_any(child_layout, targets):
            return True
    return False


def _page_intro(title: str, subtitle: str, parent: QWidget):
    page = QWidget(parent)
    page.setObjectName("artStudioInspectorTabPage")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 10, 10, 14)
    layout.setSpacing(8)
    heading = QLabel(title, page)
    heading.setObjectName("artStudioSectionHeading")
    hint = QLabel(subtitle, page)
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(hint)
    return page, layout


def _move_layout_items(source: QLayout, targets: dict[str, QVBoxLayout], classifier) -> int:
    moved = 0
    while source.count():
        item = source.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            category = classifier(widget, None)
            targets[category].addWidget(widget)
            moved += 1
        elif child_layout is not None:
            category = classifier(None, child_layout)
            targets[category].addLayout(child_layout)
            moved += 1
        # Espaçadores antigos são descartados; as novas páginas controlam
        # espaçamento e alongamento de forma consistente.
        del item
    return moved


def _install_left_workspace(page) -> None:
    if getattr(page, "_v161_left_workspace_installed", False):
        return
    scroll = page.findChild(QScrollArea, "artStudioElementsScroll")
    content = scroll.widget() if scroll is not None else None
    source = content.layout() if content is not None else None
    if source is None:
        return

    tabs = QTabWidget(content)
    tabs.setObjectName("artStudioElementsTabs")
    insert_page, insert_layout = _page_intro(
        "Adicionar ao projeto",
        "Insira elementos na página e monte sua composição.",
        tabs,
    )
    page_page, page_layout = _page_intro(
        "Página e fundo",
        "Defina o formato, as dimensões e o plano de fundo da arte.",
        tabs,
    )
    tabs.addTab(insert_page, "＋  Elementos")
    tabs.addTab(page_page, "▧  Página")

    insert_targets = {
        id(value)
        for value in (
            getattr(page, "add_image_button", None),
            getattr(page, "add_text_button", None),
            getattr(page, "add_rect_button", None),
            getattr(page, "add_ellipse_button", None),
            getattr(page, "templates_button", None),
        )
        if value is not None
    }
    page_targets = {
        id(value)
        for value in (
            getattr(page, "background_button", None),
            getattr(page, "preset_combo", None),
            getattr(page, "width_spin", None),
            getattr(page, "height_spin", None),
            getattr(page, "apply_size_button", None),
            getattr(page, "v150_solid_bg_button", None),
            getattr(page, "v150_gradient_bg_button", None),
            getattr(page, "v150_image_bg_button", None),
        )
        if value is not None
    }
    library_names = {"etiqueta", "faixa de título", "selo", "botão", "chamada", "número"}

    def classify(widget, child_layout) -> str:
        if widget is not None:
            if id(widget) in page_targets:
                return "page"
            if id(widget) in insert_targets:
                return "insert"
            if isinstance(widget, QLabel):
                text = widget.text().strip().casefold()
                if text in {"formato da arte", "fundos avançados"}:
                    return "page"
                if text == "biblioteca de elementos":
                    return "insert"
            if widget.property("secondary") and widget.text().strip().casefold() in library_names:
                return "insert"
            if widget.objectName() == "artStudioPageSettingsGroup":
                return "page"
        if child_layout is not None:
            page_ids = {
                id(getattr(page, "width_spin", None)),
                id(getattr(page, "height_spin", None)),
            }
            if _layout_contains_any(child_layout, page_ids):
                return "page"
        return "insert"

    moved = _move_layout_items(source, {"insert": insert_layout, "page": page_layout}, classify)
    insert_layout.addStretch(1)
    page_layout.addStretch(1)
    source.addWidget(tabs)
    page._v161_left_tabs = tabs
    page._v161_left_workspace_installed = moved > 0
    page._v161_left_workspace_item_count = moved


def _install_inspector_workspace(page) -> None:
    if getattr(page, "_v161_inspector_workspace_installed", False):
        return
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    source = content.layout() if content is not None else None
    if source is None:
        return

    tabs = QTabWidget(content)
    tabs.setObjectName("artStudioInspectorTabs")
    tab_pages = {}
    tab_layouts = {}
    for key, tab_title, heading, hint in (
        ("layers", "☷  Camadas", "Camadas e objetos", "Selecione, organize, bloqueie e recupere os elementos da página."),
        ("design", "⚙  Design", "Propriedades do objeto", "Ajuste tamanho, posição, aparência e transformações."),
        ("compose", "⇄  Composição", "Composição e alinhamento", "Organize vários elementos e refine a distribuição visual."),
        ("protect", "♧  Proteção", "Integridade do projeto", "Recupere camadas e acompanhe a proteção da composição."),
    ):
        tab_page, tab_layout = _page_intro(heading, hint, tabs)
        tabs.addTab(tab_page, tab_title)
        tab_pages[key] = tab_page
        tab_layouts[key] = tab_layout

    layer_targets = {
        id(value)
        for value in (
            getattr(page, "selection_label", None),
            getattr(page, "layers", None),
            getattr(page, "v154_layer_filter", None),
            getattr(page, "v154_layer_count", None),
        )
        if value is not None
    }
    layer_action_targets = {
        id(value)
        for value in (
            getattr(page, "v145_visibility_button", None),
            getattr(page, "v145_lock_button", None),
            getattr(page, "v145_crop_button", None),
            getattr(page, "v145_align_button", None),
            getattr(page, "v146_group_button", None),
            getattr(page, "v146_ungroup_button", None),
            getattr(page, "v146_photo_button", None),
            getattr(page, "v146_frame_button", None),
            getattr(page, "v146_effect_button", None),
            getattr(page, "v154_rename_button", None),
            getattr(page, "v154_visibility_button", None),
            getattr(page, "v154_lock_button", None),
        )
        if value is not None
    }
    design_panel_names = {
        "artStudioObjectSizePanel",
        "artStudioPositionPanel",
        "artStudioShapeStylePanel",
    }
    compose_panel_names = {
        "artStudioCompositionPanelV151",
        "artStudioTransformPanelV152",
    }
    protect_panel_names = {
        "artStudioIntegrityPanelV155",
        "artStudioRecyclePanelV156",
    }
    property_targets = {
        id(value)
        for value in (
            getattr(page, "rotation_spin", None),
            getattr(page, "scale_spin", None),
            getattr(page, "opacity_slider", None),
            getattr(page, "apply_transform_button", None),
            getattr(page, "edit_text_button", None),
            getattr(page, "font_button", None),
            getattr(page, "color_button", None),
            getattr(page, "center_button", None),
            getattr(page, "duplicate_button", None),
            getattr(page, "forward_button", None),
            getattr(page, "backward_button", None),
            getattr(page, "delete_button", None),
        )
        if value is not None
    }

    def classify(widget, child_layout) -> str:
        if widget is not None:
            if id(widget) in layer_targets:
                return "layers"
            name = widget.objectName()
            if name in design_panel_names:
                return "design"
            if name in compose_panel_names:
                return "compose"
            if name in protect_panel_names:
                return "protect"
            if _widget_contains_any(widget, layer_action_targets):
                return "layers"
            if id(widget) in property_targets:
                return "design"
            return "design"
        if child_layout is not None:
            if _layout_contains_any(child_layout, layer_action_targets):
                return "layers"
            if _layout_contains_any(child_layout, property_targets):
                return "design"
            return "design"
        return "design"

    moved = _move_layout_items(source, tab_layouts, classify)
    for key, layout in tab_layouts.items():
        layout.addStretch(1)
    source.addWidget(tabs)
    page._v161_inspector_tabs = tabs
    page._v161_inspector_workspace_installed = moved > 0
    page._v161_inspector_workspace_item_count = moved


def _theme_id(page) -> str:
    owner = page
    while owner is not None:
        value = getattr(owner, "_central_theme", None)
        if value in {"claro", "escuro"}:
            return value
        owner = owner.parentWidget()
    return "escuro" if page.palette().color(QPalette.ColorRole.Window).lightness() < 128 else "claro"


def _skin_stylesheet(theme: str) -> str:
    dark = theme == "escuro"
    if dark:
        window = "#0B1724"
        panel = "#12283A"
        panel_alt = "#162F43"
        border = "#29475D"
        text = "#E8F0F6"
        muted = "#91A8BA"
        accent = "#D6B66D"
        accent_text = "#12283A"
        workspace = "#0D1C2A"
        field = "#1A3449"
        secondary = "#1A354B"
        hover = "#25465E"
    else:
        window = "#EEF3F7"
        panel = "#FFFFFF"
        panel_alt = "#F6F9FB"
        border = "#CDD9E3"
        text = "#17344A"
        muted = "#688096"
        accent = "#B18B3E"
        accent_text = "#FFFFFF"
        workspace = "#E2EAF1"
        field = "#FFFFFF"
        secondary = "#F1F5F8"
        hover = "#E5EDF3"

    return f"""
    QWidget#artStudioPage {{ background:{window}; color:{text}; }}
    QFrame#artStudioToolbar {{ background:{panel}; border:1px solid {border}; border-radius:14px; }}
    QFrame#artStudioHeaderBrand {{ background:transparent; border:0; }}
    QLabel#artStudioBrandMark {{ background:{accent}; color:{accent_text}; border:0; border-radius:9px; font-size:15px; font-weight:900; min-width:38px; max-width:38px; min-height:38px; max-height:38px; }}
    QLabel#artStudioBrandTitle {{ color:{text}; background:transparent; border:0; font-size:13px; font-weight:900; }}
    QLabel#artStudioBrandSub {{ color:{muted}; background:transparent; border:0; font-size:8px; font-weight:700; letter-spacing:1px; }}
    QFrame#artStudioHeaderDivider {{ background:{border}; border:0; max-width:1px; min-width:1px; }}
    QLabel#artProjectName {{ color:{text}; background:{panel_alt}; border:1px solid {border}; border-radius:8px; padding:7px 11px; font-size:10px; font-weight:800; }}
    QFrame#artStudioPanel {{ background:{panel}; border:1px solid {border}; border-radius:14px; }}
    QLabel#artPanelTitle {{ color:{text}; background:transparent; border:0; border-bottom:1px solid {border}; padding:4px 3px 10px 3px; font-size:10px; font-weight:900; letter-spacing:1px; }}
    QLabel#artSmallLabel {{ color:{muted}; background:transparent; border:0; font-size:8px; font-weight:900; letter-spacing:0.8px; padding-top:5px; }}
    QLabel#artStudioSectionHeading {{ color:{text}; background:transparent; border:0; font-size:12px; font-weight:900; }}
    QLabel#artStudioSectionHint {{ color:{muted}; background:transparent; border:0; font-size:9px; }}
    QFrame#artStudioWorkspace {{ background:{workspace}; border:1px solid {border}; border-radius:16px; }}
    QGraphicsView#artCanvasView {{ background:{workspace}; border:1px solid {border}; border-radius:10px; outline:0; }}
    QScrollArea#artStudioElementsScroll, QScrollArea#artStudioLayersScroll {{ background:transparent; border:0; }}
    QTabWidget#artStudioElementsTabs::pane, QTabWidget#artStudioInspectorTabs::pane {{ background:{panel_alt}; border:1px solid {border}; border-radius:9px; top:-1px; }}
    QTabBar::tab {{ background:{panel_alt}; color:{muted}; border:1px solid {border}; border-bottom:0; border-top-left-radius:7px; border-top-right-radius:7px; padding:8px 9px; margin-right:3px; font-size:9px; font-weight:800; }}
    QTabBar::tab:selected {{ background:{panel}; color:{text}; border-color:{accent}; }}
    QTabBar::tab:hover {{ color:{text}; background:{hover}; }}
    QPushButton {{ min-height:34px; border-radius:8px; padding:5px 10px; font-size:9px; font-weight:750; }}
    QPushButton[secondary="true"] {{ background:{secondary}; color:{text}; border:1px solid {border}; }}
    QPushButton[secondary="true"]:hover {{ background:{hover}; border-color:{accent}; }}
    QPushButton[danger="true"] {{ background:#8E3540; color:#FFFFFF; border:1px solid #A94E59; }}
    QPushButton[purple="true"] {{ background:#55458B; color:#FFFFFF; border:1px solid #7565AD; }}
    QPushButton[green="true"] {{ background:#167653; color:#FFFFFF; border:1px solid #26956D; }}
    QComboBox, QSpinBox, QDoubleSpinBox {{ background:{field}; color:{text}; border:1px solid {border}; border-radius:7px; padding:5px 7px; min-height:25px; font-size:9px; }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ border-color:{accent}; }}
    QListWidget#artLayersList {{ background:{panel_alt}; color:{text}; border:1px solid {border}; border-radius:8px; padding:4px; outline:0; }}
    QListWidget#artLayersList::item {{ min-height:27px; border-radius:5px; padding:3px 5px; }}
    QListWidget#artLayersList::item:selected {{ background:{accent}; color:{accent_text}; }}
    QLabel#muted, QLabel#artStudioStatusBar {{ color:{muted}; background:transparent; border:0; font-size:9px; }}
    QCheckBox {{ color:{text}; spacing:6px; font-size:9px; }}
    QScrollBar:vertical {{ background:transparent; width:7px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{border}; border-radius:3px; min-height:26px; }}
    QScrollBar::handle:vertical:hover {{ background:{accent}; }}
    QScrollBar:horizontal {{ background:transparent; height:7px; margin:2px; }}
    QScrollBar::handle:horizontal {{ background:{border}; border-radius:3px; min-width:26px; }}
    """


def _apply_skin(page) -> None:
    theme = _theme_id(page)
    if getattr(page, "_v161_skin_theme", None) == theme:
        return
    page.setStyleSheet(_skin_stylesheet(theme))
    page._v161_skin_theme = theme
    # O canvas é mantido intacto; só o fundo do viewport acompanha o tema.
    if hasattr(page, "view"):
        color = "#0D1C2A" if theme == "escuro" else "#E2EAF1"
        page.view.setStyleSheet(
            f"QGraphicsView#artCanvasView {{background:{color};border:0;outline:0;}}"
        )
    text_toolbar = getattr(page, "v147_text_toolbar", None)
    if text_toolbar is not None:
        border = "#29475D" if theme == "escuro" else "#CDD9E3"
        panel = "#12283A" if theme == "escuro" else "#FFFFFF"
        text_toolbar.setStyleSheet(
            f"QFrame#artStudioInlineTextToolbar {{background:{panel};border:1px solid {border};border-radius:11px;}}"
            "QToolButton,QPushButton,QComboBox,QSpinBox,QDoubleSpinBox {min-height:32px;padding:3px 8px;border-radius:7px;}"
            f"QToolButton:checked {{background:{'#D6B66D' if theme == 'escuro' else '#E6D5AE'};color:{'#12283A' if theme == 'escuro' else '#17344A'};border:1px solid {accent};}}"
        )
    pages_bar = getattr(page, "v150_pages_bar", None)
    if pages_bar is not None:
        bar_bg = "#132B3F" if theme == "escuro" else "#E7EEF4"
        tab_bg = "#17344D" if theme == "escuro" else "#FFFFFF"
        tab_text = "#DCE7EF" if theme == "escuro" else "#17344A"
        pages_bar.setStyleSheet(
            f"QFrame#artStudioPagesBar {{background:{bar_bg};border:1px solid {border};border-radius:10px;}}"
            f"QTabBar::tab {{background:{tab_bg};color:{tab_text};border:1px solid {border};border-radius:7px;padding:7px 12px;margin:2px;font-size:9px;font-weight:800;}}"
            f"QTabBar::tab:selected {{background:{accent};color:{accent_text};border-color:{accent};}}"
        )
    page.update()


class _ThemeRefreshFilter(QObject):
    def __init__(self, page, parent=None):
        super().__init__(parent)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):
        if event.type() in {
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ApplicationPaletteChange,
        }:
            page = self._page_ref()
            if page is not None:
                QTimer.singleShot(0, lambda ref=self._page_ref: _refresh_from_ref(ref))
        return False


def _refresh_from_ref(page_ref) -> None:
    page = page_ref()
    if page is not None:
        _apply_skin(page)


def _install_header_identity(page) -> None:
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None or getattr(page, "_v161_header_installed", False):
        return
    brand = QFrame(toolbar)
    brand.setObjectName("artStudioHeaderBrand")
    row = QHBoxLayout(brand)
    row.setContentsMargins(0, 0, 8, 0)
    row.setSpacing(9)
    mark = QLabel("CM")
    mark.setObjectName("artStudioBrandMark")
    mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_block = QWidget(brand)
    title_layout = QVBoxLayout(title_block)
    title_layout.setContentsMargins(0, 0, 0, 0)
    title_layout.setSpacing(2)
    title = QLabel("ESTÚDIO DE ARTES")
    title.setObjectName("artStudioBrandTitle")
    subtitle = QLabel("DESIGN • COMPOSIÇÃO • CRIAÇÃO")
    subtitle.setObjectName("artStudioBrandSub")
    title_layout.addWidget(title)
    title_layout.addWidget(subtitle)
    row.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(title_block, 1, Qt.AlignmentFlag.AlignVCenter)
    layout.insertWidget(0, brand, 0)

    divider = QFrame(toolbar)
    divider.setObjectName("artStudioHeaderDivider")
    divider.setFixedWidth(1)
    divider.setFixedHeight(36)
    layout.insertWidget(1, divider)

    for name, label, tooltip in (
        ("new_button", "＋  Novo", "Criar um projeto novo"),
        ("open_button", "↗  Abrir projeto", "Abrir um projeto salvo"),
        ("save_button", "Salvar", "Salvar o projeto atual"),
        ("export_button", "Exportar arte", "Exportar a arte atual"),
    ):
        button = getattr(page, name, None)
        if button is not None:
            button.setText(label)
            button.setToolTip(tooltip)
            button.setMinimumHeight(38)
            if name in {"save_button", "export_button"}:
                button.setProperty("secondary", False)
                button.setProperty("gold", True)
    project_label = getattr(page, "project_label", None)
    if project_label is not None:
        project_label.setMinimumWidth(150)
        project_label.setMaximumWidth(260)
        project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    toolbar.setMinimumHeight(62)
    page._v161_header_installed = True


def _polish_element_actions(page) -> None:
    specs = (
        ("add_image_button", "▧  Imagem"),
        ("add_text_button", "T  Texto"),
        ("add_rect_button", "□  Retângulo"),
        ("add_ellipse_button", "○  Círculo"),
        ("background_button", "◐  Fundo da arte"),
        ("templates_button", "▦  Modelos rápidos"),
    )
    for attr, text in specs:
        button = getattr(page, attr, None)
        if button is not None:
            button.setText(text)
            button.setMinimumHeight(40)
            button.setToolTip(button.toolTip() or text)
    for name, text in (
        ("v150_solid_bg_button", "◉  Cor sólida"),
        ("v150_gradient_bg_button", "◒  Degradê"),
        ("v150_image_bg_button", "▧  Imagem de fundo"),
    ):
        button = getattr(page, name, None)
        if button is not None:
            button.setText(text)
    if hasattr(page, "status_label"):
        page.status_label.setObjectName("artStudioStatusBar")
        page.status_label.setMinimumHeight(25)
        page.status_label.setContentsMargins(8, 2, 8, 2)
    if hasattr(page, "_v161_inspector_tabs"):
        page._v161_inspector_tabs.setCurrentIndex(0)


def enhance_art_studio_page_v161(page) -> None:
    if getattr(page, "_v161_installed", False):
        return
    _install_left_workspace(page)
    _install_inspector_workspace(page)
    _install_header_identity(page)
    _polish_element_actions(page)

    # Mais espaço para o canvas e painéis laterais com larguras previsíveis.
    left = next(
        (label.parentWidget() for label in page.findChildren(QLabel, "artPanelTitle") if label.text() == "ELEMENTOS"),
        None,
    )
    right = next(
        (label.parentWidget() for label in page.findChildren(QLabel, "artPanelTitle") if label.text() == "CAMADAS E OBJETOS"),
        None,
    )
    if left is not None:
        left.setFixedWidth(224)
        left.setMinimumWidth(210)
    if right is not None:
        right.setFixedWidth(336)
        right.setMinimumWidth(316)
    root = page.layout()
    if root is not None:
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
    workspace = page.findChild(QFrame, "artStudioWorkspace")
    if workspace is not None:
        workspace.setMinimumWidth(460)
    page._v161_installed = True
    _apply_skin(page)

    filter_object = _ThemeRefreshFilter(page, page)
    page._v161_theme_filter = filter_object
    owner = page.window()
    if owner is not None:
        owner.installEventFilter(filter_object)
    page.installEventFilter(filter_object)

    page.status_label.setText(
        "Estúdio reorganizado: Elementos e Página à esquerda; Camadas, Design, Composição e Proteção à direita."
    )


def install_art_studio_v161() -> None:
    """Instala a V161 depois das evoluções V143–V160."""
    global _INSTALLED
    if _INSTALLED:
        return
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v161_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v161(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v161(page)

    MainWindow.__init__ = init_with_v161
    MainWindow._v161_integration_installed = True
    _INSTALLED = True
