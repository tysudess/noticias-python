from __future__ import annotations

"""Integra o Estúdio de Artes à navegação já consolidada da Central."""

import logging
import weakref
from pathlib import Path

from PySide6.QtWidgets import QFrame

from monitor_noticias.ui.art_studio_page import ArtStudioPage
from monitor_noticias.ui.art_studio_v145 import enhance_art_studio_page
import monitor_noticias.ui.art_studio_v146 as art_studio_v146_module
from monitor_noticias.ui.art_studio_v146 import enhance_art_studio_page_v146
from monitor_noticias.ui.art_studio_v147 import enhance_art_studio_page_v147
from monitor_noticias.ui.main_window import MainWindow
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem
import monitor_noticias.ui.sidebar_widgets as sidebar_widgets


class _DeferredArtStudioView:
    """Adia o acesso ao canvas até o QGraphicsView real estar construído."""

    __slots__ = ("_page_ref",)

    def __init__(self, page: ArtStudioPage) -> None:
        self._page_ref = weakref.ref(page)

    def actual_size(self) -> None:
        page = self._page_ref()
        if page is None:
            return
        view = page.__dict__.get("_art_studio_view_actual")
        if view is not None:
            view.actual_size()


def _get_art_studio_view(page: ArtStudioPage):
    actual = page.__dict__.get("_art_studio_view_actual")
    if actual is not None:
        return actual
    proxy = page.__dict__.get("_art_studio_view_deferred")
    if proxy is None:
        proxy = _DeferredArtStudioView(page)
        page.__dict__["_art_studio_view_deferred"] = proxy
    return proxy


def _set_art_studio_view(page: ArtStudioPage, view) -> None:
    page.__dict__["_art_studio_view_actual"] = view


def _install_deferred_view_compatibility() -> None:
    """Corrige a conexão antecipada do zoom sem substituir o canvas real."""
    current = getattr(ArtStudioPage, "view", None)
    if not isinstance(current, property):
        ArtStudioPage.view = property(
            _get_art_studio_view,
            _set_art_studio_view,
        )


log = logging.getLogger(__name__)
_INSTALLED = False


def install_art_studio() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Instala a compatibilidade antes de qualquer ArtStudioPage ser criada.
    # O proxy resolve a conexão do botão 100% sem acessar self.view cedo demais.
    _install_deferred_view_compatibility()

    groups = []
    for label, names in sidebar_widgets._GROUPS:
        if label == "FERRAMENTAS" and "ART_STUDIO" not in names:
            names = tuple(names) + ("ART_STUDIO",)
        groups.append((label, names))
    sidebar_widgets._GROUPS = tuple(groups)

    extra = (
        "ART_STUDIO",
        "art_studio_nav",
        "Estúdio de Artes",
        "Crie artes, cards, montagens e materiais gráficos.",
    )
    if not any(item[0] == "ART_STUDIO" for item in sidebar_widgets._EXTRA_NAV_ITEMS):
        sidebar_widgets._EXTRA_NAV_ITEMS = sidebar_widgets._EXTRA_NAV_ITEMS + (extra,)

    original_build_sidebar = MainWindow._build_sidebar

    def build_sidebar_with_art_studio(self):
        sidebar = original_build_sidebar(self)
        button = SidebarNavItem(
            icon_text="✎",
            label_text="Estúdio de Artes",
            icon_color="#F4B719",
            parent=sidebar,
        )
        button.setObjectName("artStudioNavItem")
        button.clicked.connect(self._open_art_studio)
        self.art_studio_nav = button
        layout = sidebar.layout()
        if layout is not None:
            insert_at = max(2, layout.count() - 2)
            layout.insertWidget(insert_at, button)
        return sidebar

    MainWindow._build_sidebar = build_sidebar_with_art_studio

    original_init = MainWindow.__init__

    def init_with_art_studio(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        state_root = Path(getattr(self.paths, "state_root", self.paths.root))
        projects_dir = state_root / "ArtStudioProjects"
        self.art_studio_page = ArtStudioPage(projects_dir, self)
        enhance_art_studio_page(self.art_studio_page)
        # V146 usa QFrame no painel avançado, mas sua lista de imports não o
        # declarava. Registra a classe no namespace do módulo antes da chamada.
        art_studio_v146_module.QFrame = QFrame
        enhance_art_studio_page_v146(self.art_studio_page)
        enhance_art_studio_page_v147(self.art_studio_page)
        self.pages["ART_STUDIO"] = self.art_studio_page
        self.stack.addWidget(self.art_studio_page)

    MainWindow.__init__ = init_with_art_studio

    original_navigate = MainWindow.navigate

    def navigate_with_art_studio(self, section):
        original_navigate(self, section)
        self.art_studio_nav.set_active(False)

    MainWindow.navigate = navigate_with_art_studio

    def open_art_studio(self):
        page = getattr(self, "art_studio_page", None)
        if page is None:
            log.error("A página do Estúdio de Artes ainda não foi inicializada.")
            return
        self._current = "ART_STUDIO"
        self.stack.setCurrentWidget(page)
        for button in self.nav_buttons.values():
            button.set_active(False)
        self.art_studio_nav.set_active(True)
        self.title.setText("Estúdio de Artes")
        self.subtitle.setText("Crie e edite artes, cards, montagens e materiais gráficos.")
        self.header_identity.setVisible(False)
        page.refresh()
        self._last_refresh_signature = self._state_signature()

    MainWindow._open_art_studio = open_art_studio
    _INSTALLED = True
