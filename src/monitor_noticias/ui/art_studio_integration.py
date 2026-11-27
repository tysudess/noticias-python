from __future__ import annotations

"""Integra o Estúdio de Artes à navegação da Central com carga sob demanda.

A página do editor é deliberadamente criada somente quando o usuário abre a
ferramenta. A construção da cena Qt e a instalação das camadas V145–V177 não
participam mais da inicialização da janela principal.
"""

import logging
import weakref
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMessageBox, QVBoxLayout, QWidget

import monitor_noticias.ui.art_studio_v146 as art_studio_v146_module
from monitor_noticias.ui.main_window import MainWindow
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem
import monitor_noticias.ui.sidebar_widgets as sidebar_widgets


class _DeferredArtStudioView:
    """Adia o acesso ao canvas até o QGraphicsView real estar construído."""

    __slots__ = ("_page_ref",)

    def __init__(self, page) -> None:
        self._page_ref = weakref.ref(page)

    def actual_size(self) -> None:
        page = self._page_ref()
        if page is None:
            return
        view = page.__dict__.get("_art_studio_view_actual")
        if view is not None:
            view.actual_size()


def _get_art_studio_view(page):
    actual = page.__dict__.get("_art_studio_view_actual")
    if actual is not None:
        return actual
    proxy = page.__dict__.get("_art_studio_view_deferred")
    if proxy is None:
        proxy = _DeferredArtStudioView(page)
        page.__dict__["_art_studio_view_deferred"] = proxy
    return proxy


def _set_art_studio_view(page, view) -> None:
    page.__dict__["_art_studio_view_actual"] = view


def _install_deferred_view_compatibility() -> None:
    """Corrige a conexão antecipada do zoom sem substituir o canvas real."""
    from monitor_noticias.ui.art_studio_page import ArtStudioPage

    current = getattr(ArtStudioPage, "view", None)
    if not isinstance(current, property):
        ArtStudioPage.view = property(
            _get_art_studio_view,
            _set_art_studio_view,
        )


log = logging.getLogger(__name__)
_INSTALLED = False


def _enhance_art_studio_page(page) -> None:
    """Aplica, em ordem, todas as camadas do editor quando ele é solicitado."""
    from monitor_noticias.ui.art_studio_v145 import enhance_art_studio_page
    from monitor_noticias.ui.art_studio_v146 import enhance_art_studio_page_v146
    from monitor_noticias.ui.art_studio_v147 import enhance_art_studio_page_v147
    from monitor_noticias.ui.art_studio_v148 import enhance_art_studio_page_v148
    from monitor_noticias.ui.art_studio_v149 import enhance_art_studio_page_v149
    from monitor_noticias.ui.art_studio_v150 import enhance_art_studio_page_v150
    from monitor_noticias.ui.art_studio_v151 import enhance_art_studio_page_v151
    from monitor_noticias.ui.art_studio_v152 import enhance_art_studio_page_v152
    from monitor_noticias.ui.art_studio_v153 import enhance_art_studio_page_v153
    from monitor_noticias.ui.art_studio_v154 import enhance_art_studio_page_v154
    from monitor_noticias.ui.art_studio_v155 import enhance_art_studio_page_v155
    from monitor_noticias.ui.art_studio_v156 import enhance_art_studio_page_v156
    from monitor_noticias.ui.art_studio_v157 import enhance_art_studio_page_v157
    from monitor_noticias.ui.art_studio_v158 import enhance_art_studio_page_v158
    from monitor_noticias.ui.art_studio_v159 import enhance_art_studio_page_v159
    from monitor_noticias.ui.art_studio_v160 import enhance_art_studio_page_v160
    from monitor_noticias.ui.art_studio_v161 import enhance_art_studio_page_v161
    from monitor_noticias.ui.art_studio_v162 import enhance_art_studio_page_v162
    from monitor_noticias.ui.art_studio_v163 import enhance_art_studio_page_v163
    from monitor_noticias.ui.art_studio_v164 import enhance_art_studio_page_v164
    from monitor_noticias.ui.art_studio_v165 import enhance_art_studio_page_v165
    from monitor_noticias.ui.art_studio_v166 import enhance_art_studio_page_v166
    from monitor_noticias.ui.art_studio_v167 import enhance_art_studio_page_v167
    from monitor_noticias.ui.art_studio_v168 import enhance_art_studio_page_v168
    from monitor_noticias.ui.art_studio_v169 import enhance_art_studio_page_v169
    from monitor_noticias.ui.art_studio_v170 import enhance_art_studio_page_v170
    from monitor_noticias.ui.art_studio_v171 import enhance_art_studio_page_v171
    from monitor_noticias.ui.art_studio_v172 import enhance_art_studio_page_v172
    from monitor_noticias.ui.art_studio_v173 import enhance_art_studio_page_v173
    from monitor_noticias.ui.art_studio_v174 import enhance_art_studio_page_v174
    from monitor_noticias.ui.art_studio_v175 import enhance_art_studio_page_v175
    from monitor_noticias.ui.art_studio_v176 import enhance_art_studio_page_v176
    from monitor_noticias.ui.art_studio_v177 import enhance_art_studio_page_v177

    # V146 referencia QFrame pelo namespace do próprio módulo.
    art_studio_v146_module.QFrame = QFrame

    enhancers = (
        enhance_art_studio_page,
        enhance_art_studio_page_v146,
        enhance_art_studio_page_v147,
        enhance_art_studio_page_v148,
        enhance_art_studio_page_v149,
        enhance_art_studio_page_v150,
        enhance_art_studio_page_v151,
        enhance_art_studio_page_v152,
        enhance_art_studio_page_v153,
        enhance_art_studio_page_v154,
        enhance_art_studio_page_v155,
        enhance_art_studio_page_v156,
        enhance_art_studio_page_v157,
        enhance_art_studio_page_v158,
        enhance_art_studio_page_v159,
        enhance_art_studio_page_v160,
        enhance_art_studio_page_v161,
        enhance_art_studio_page_v162,
        enhance_art_studio_page_v163,
        enhance_art_studio_page_v164,
        enhance_art_studio_page_v165,
        enhance_art_studio_page_v166,
        enhance_art_studio_page_v167,
        enhance_art_studio_page_v168,
        enhance_art_studio_page_v169,
        enhance_art_studio_page_v170,
        enhance_art_studio_page_v171,
        enhance_art_studio_page_v172,
        enhance_art_studio_page_v173,
        enhance_art_studio_page_v174,
        enhance_art_studio_page_v175,
        enhance_art_studio_page_v176,
        enhance_art_studio_page_v177,
    )
    for enhance in enhancers:
        enhance(page)


def _create_art_studio_page(window):
    """Cria e integra o editor na primeira solicitação do usuário."""
    existing = getattr(window, "art_studio_page", None)
    if existing is not None:
        return existing

    from monitor_noticias.ui.art_studio_page import ArtStudioPage

    _install_deferred_view_compatibility()
    placeholder = getattr(window, "_art_studio_placeholder", None)
    projects_dir = Path(window._art_studio_projects_dir)
    page = None

    try:
        page = ArtStudioPage(projects_dir, window.stack)
        page.setObjectName("artStudioPage")
        window.art_studio_page = page
        _enhance_art_studio_page(page)

        insert_at = window.stack.indexOf(placeholder) if placeholder is not None else -1
        if insert_at < 0:
            window.stack.addWidget(page)
        else:
            window.stack.insertWidget(insert_at, page)

        window.pages["ART_STUDIO"] = page
        window._art_studio_ready = True

        if placeholder is not None:
            window.stack.removeWidget(placeholder)
            placeholder.deleteLater()
            window._art_studio_placeholder = None

        log.info("Estúdio de Artes carregado sob demanda (camadas V145–V177).")
        return page

    except Exception as exc:
        log.exception("Falha ao inicializar o Estúdio de Artes sob demanda.")
        if page is not None:
            window.stack.removeWidget(page)
            page.deleteLater()
        window.art_studio_page = None
        QMessageBox.critical(
            window,
            "Não foi possível abrir o Estúdio de Artes",
            "O restante da Central continua disponível. Consulte "
            "logs/inicializacao.log para identificar a falha do editor.\n\n"
            f"Detalhe: {exc}",
        )
        return None


def install_art_studio() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Nenhuma instância, cena ou painel do editor é criado durante o boot.

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
        self._art_studio_projects_dir = state_root / "ArtStudioProjects"
        self.art_studio_page = None
        self._art_studio_ready = False

        # A página leve preserva o espaço e a navegação do editor sem criar a
        # cena gráfica, os painéis e dezenas de filtros durante a inicialização.
        placeholder = QWidget(self.stack)
        placeholder.setObjectName("artStudioDeferredPlaceholder")
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.addStretch(1)
        message = QLabel(
            "O Estúdio de Artes será preparado quando esta ferramenta for aberta.",
            placeholder,
        )
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(message)
        placeholder_layout.addStretch(1)
        self._art_studio_placeholder = placeholder
        self.pages["ART_STUDIO"] = placeholder
        self.stack.addWidget(placeholder)

    MainWindow.__init__ = init_with_art_studio

    original_navigate = MainWindow.navigate

    def navigate_with_art_studio(self, section):
        original_navigate(self, section)
        self.art_studio_nav.set_active(False)

    MainWindow.navigate = navigate_with_art_studio

    def open_art_studio(self):
        page = _create_art_studio_page(self)
        if page is None:
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
