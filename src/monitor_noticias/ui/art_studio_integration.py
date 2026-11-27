from __future__ import annotations

"""Integra o Estúdio de Artes à navegação da Central com carga gradual.

O editor é criado somente no primeiro acesso. Suas camadas V145–V177 são
aplicadas uma por vez em callbacks Qt, permitindo que a janela continue
processando eventos e exibindo o andamento da abertura.
"""

import logging
import time
import weakref
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

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
        ArtStudioPage.view = property(_get_art_studio_view, _set_art_studio_view)


log = logging.getLogger(__name__)
_INSTALLED = False


def _enhance_art_studio_page(page=None):
    """Aplica todas as camadas em ordem ou devolve a fila para carga gradual."""
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
    if page is not None:
        for enhance in enhancers:
            enhance(page)
    return enhancers


def _art_studio_enhancers():
    """Nome explícito para os chamadores que agendam uma camada por vez."""
    return _enhance_art_studio_page()


def _enhancer_label(enhance) -> str:
    module = getattr(enhance, "__module__", "")
    suffix = module.rsplit("_v", 1)[-1]
    return f"V{suffix}" if suffix.isdigit() else "V145"


def _enhancer_failure_stage(queue, index: int) -> str:
    """Descreve a etapa sem indexar a função como se fosse uma tupla."""
    if 0 <= index < len(queue):
        return f"{_enhancer_label(queue[index])} ({index + 1}/{len(queue)})"
    return "criação/importação inicial"


def _set_loading_message(window, message: str) -> None:
    label = getattr(window, "_art_studio_loading_label", None)
    if label is not None:
        try:
            label.setText(message)
        except RuntimeError:
            log.debug("O rótulo de carregamento do Estúdio já foi destruído.")


def _create_art_studio_page(window):
    """Cria a página base; as camadas avançadas são aplicadas separadamente."""
    existing = getattr(window, "_art_studio_building_page", None)
    if existing is not None:
        return existing

    existing = getattr(window, "art_studio_page", None)
    if existing is not None:
        return existing

    page = None
    try:
        from monitor_noticias.ui.art_studio_page import ArtStudioPage

        _install_deferred_view_compatibility()
        projects_dir = Path(window._art_studio_projects_dir)
        page = ArtStudioPage(projects_dir, window.stack)
        page.setObjectName("artStudioPage")
        # A página fica registrada no stack, mas o placeholder permanece visível
        # até que todas as camadas terminem de ser instaladas.
        window.stack.addWidget(page)
        window._art_studio_building_page = page
        log.info("[ArtStudioLoad] Página base criada; iniciando camadas V145–V177.")
        return page
    except Exception:
        log.exception("[ArtStudioLoad] Falha na criação da página base do Estúdio.")
        if page is not None:
            try:
                window.stack.removeWidget(page)
                page.deleteLater()
            except RuntimeError:
                log.exception("[ArtStudioLoad] Falha ao remover página base incompleta.")
        window._art_studio_building_page = None
        raise


def _is_art_studio_current(window) -> bool:
    current = getattr(window, "_current", None)
    return current == "ART_STUDIO" or getattr(current, "value", None) == "ART_STUDIO"


def _show_art_studio(window, page) -> None:
    window._current = "ART_STUDIO"
    window.stack.setCurrentWidget(page)
    for button in getattr(window, "nav_buttons", {}).values():
        button.set_active(False)
    nav = getattr(window, "art_studio_nav", None)
    if nav is not None:
        nav.set_active(True)
    window.title.setText("Estúdio de Artes")
    window.subtitle.setText("Crie e edite artes, cards, montagens e materiais gráficos.")
    identity = getattr(window, "header_identity", None)
    if identity is not None:
        identity.setVisible(False)
    page.refresh()
    if hasattr(window, "_state_signature"):
        window._last_refresh_signature = window._state_signature()


def _finish_art_studio_loading(window, page) -> None:
    window.art_studio_page = page
    window._art_studio_building_page = None
    window._art_studio_ready = True
    window._art_studio_loading = False
    window._art_studio_last_failed_stage = None
    window.pages["ART_STUDIO"] = page

    placeholder = getattr(window, "_art_studio_placeholder", None)
    if placeholder is not None:
        window.stack.removeWidget(placeholder)
        placeholder.deleteLater()
        window._art_studio_placeholder = None

    timer = getattr(window, "_art_studio_load_timer", None)
    if timer is not None:
        timer.stop()

    log.info("[ArtStudioLoad] CONCLUÍDO: todas as 33 camadas V145–V177 foram aplicadas.")
    if _is_art_studio_current(window):
        _show_art_studio(window, page)


def _abort_art_studio_loading(window, page, stage: str, exc: Exception) -> None:
    """Descarrega a página parcial sem abrir diálogo modal que pareça travamento."""
    log.exception("[ArtStudioLoad] FALHA durante %s; o Estúdio será descarregado.", stage)
    window._art_studio_last_failed_stage = stage
    window._art_studio_current_stage = stage
    timer = getattr(window, "_art_studio_load_timer", None)
    if timer is not None:
        timer.stop()

    if page is not None:
        try:
            window.stack.removeWidget(page)
            page.deleteLater()
        except RuntimeError:
            log.exception("[ArtStudioLoad] Falha ao remover uma página incompleta.")

    window.art_studio_page = None
    window._art_studio_building_page = None
    window._art_studio_ready = False
    window._art_studio_loading = False
    window._art_studio_enhancer_queue = None
    window.pages["ART_STUDIO"] = window._art_studio_placeholder
    _set_loading_message(
        window,
        "Não foi possível preparar o Estúdio de Artes.\n"
        f"Etapa: {stage}.\n"
        "A Central continua disponível. Clique novamente para tentar abrir.",
    )

    if not getattr(window, "_art_studio_suppress_error_dialog", False):
        # QMessageBox.critical() é modal e pode deixar a janela principal
        # aparentemente congelada caso o diálogo apareça atrás dela.
        dialog = QMessageBox(window)
        dialog.setIcon(QMessageBox.Icon.Critical)
        dialog.setWindowTitle("Não foi possível abrir o Estúdio de Artes")
        dialog.setText(
            "A inicialização foi interrompida durante "
            f"{stage}. O restante da Central continua disponível.\n\n"
            "Consulte logs/inicializacao.log para ver o erro completo."
        )
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setModal(False)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window._art_studio_error_dialog = dialog
        dialog.show()


def _advance_art_studio_loading(window) -> None:
    """Executa uma camada por evento, sem monopolizar o loop de interface."""
    if not getattr(window, "_art_studio_loading", False):
        return

    page = getattr(window, "_art_studio_building_page", None)
    stage = "criação/importação inicial"
    try:
        if page is None:
            started = time.perf_counter()
            page = _create_art_studio_page(window)
            page_elapsed = time.perf_counter() - started
            log.info("[ArtStudioLoad] Criação da página base: %.3fs.", page_elapsed)
            if page_elapsed >= 1.0:
                log.warning("[ArtStudioLoad] A criação da página base demorou %.3fs.", page_elapsed)

            import_started = time.perf_counter()
            queue = _art_studio_enhancers()
            window._art_studio_enhancer_queue = queue
            window._art_studio_enhancer_index = 0
            import_elapsed = time.perf_counter() - import_started
            log.info(
                "[ArtStudioLoad] Importação das camadas: %.3fs; %s etapas.",
                import_elapsed,
                len(queue),
            )
            if import_elapsed >= 1.0:
                log.warning("[ArtStudioLoad] A importação das camadas demorou %.3fs.", import_elapsed)
            _set_loading_message(window, f"Página criada. Preparando camada 1 de {len(queue)}…")
            window._art_studio_load_timer.start(15)
            return

        queue = window._art_studio_enhancer_queue
        index = int(window._art_studio_enhancer_index)
        if index >= len(queue):
            stage = "finalização/abertura da página"
            window._art_studio_current_stage = stage
            _finish_art_studio_loading(window, page)
            return

        enhance = queue[index]
        stage = _enhancer_failure_stage(queue, index)
        window._art_studio_current_stage = stage
        _set_loading_message(window, f"Preparando Estúdio de Artes…\n{stage}")
        started = time.perf_counter()
        log.info("[ArtStudioLoad] INÍCIO %s.", stage)
        enhance(page)
        elapsed = time.perf_counter() - started
        log.info("[ArtStudioLoad] CONCLUÍDO %s em %.3fs.", stage, elapsed)
        if elapsed >= 1.0:
            log.warning("[ArtStudioLoad] A camada %s bloqueou o event loop por %.3fs.", stage, elapsed)
        window._art_studio_enhancer_index = index + 1
        window._art_studio_current_stage = None
        window._art_studio_load_timer.start(15)
    except Exception as exc:
        queue = getattr(window, "_art_studio_enhancer_queue", None) or ()
        index = int(getattr(window, "_art_studio_enhancer_index", 0))
        # Corrigido: cada entrada da fila é uma função; nunca se deve usar
        # queue[index][0], pois isso mascara a exceção original com TypeError.
        if queue and 0 <= index < len(queue):
            stage = _enhancer_failure_stage(queue, index)
        _abort_art_studio_loading(window, page, stage, exc)


def _start_art_studio_loading(window) -> None:
    if getattr(window, "_art_studio_loading", False):
        _set_loading_message(window, "O Estúdio de Artes já está sendo preparado…")
        return

    window._art_studio_loading = True
    window._art_studio_ready = False
    window._art_studio_enhancer_queue = None
    window._art_studio_enhancer_index = 0
    window._art_studio_current_stage = None
    window._art_studio_last_failed_stage = None
    _set_loading_message(
        window,
        "Iniciando Estúdio de Artes…\nA Central continuará responsiva durante a preparação.",
    )

    timer = getattr(window, "_art_studio_load_timer", None)
    if timer is None:
        timer = QTimer(window)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: _advance_art_studio_loading(window))
        window._art_studio_load_timer = timer
    timer.start(30)


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
        self._art_studio_building_page = None
        self._art_studio_ready = False
        self._art_studio_loading = False
        self._art_studio_load_timer = None
        self._art_studio_enhancer_queue = None
        self._art_studio_enhancer_index = 0
        self._art_studio_current_stage = None
        self._art_studio_last_failed_stage = None

        # O placeholder leve permite feedback visível durante a carga gradual.
        placeholder = QWidget(self.stack)
        placeholder.setObjectName("artStudioDeferredPlaceholder")
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.addStretch(1)
        message = QLabel(
            "O Estúdio de Artes será preparado quando esta ferramenta for aberta.",
            placeholder,
        )
        message.setObjectName("artStudioLoadingMessage")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        placeholder_layout.addWidget(message)
        placeholder_layout.addStretch(1)
        self._art_studio_placeholder = placeholder
        self._art_studio_loading_label = message
        self.pages["ART_STUDIO"] = placeholder
        self.stack.addWidget(placeholder)

    MainWindow.__init__ = init_with_art_studio

    original_navigate = MainWindow.navigate

    def navigate_with_art_studio(self, section):
        original_navigate(self, section)
        self.art_studio_nav.set_active(False)

    MainWindow.navigate = navigate_with_art_studio

    def open_art_studio(self):
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            _show_art_studio(self, page)
            return

        self._current = "ART_STUDIO"
        placeholder = getattr(self, "_art_studio_placeholder", None)
        if placeholder is not None:
            self.stack.setCurrentWidget(placeholder)
        for button in self.nav_buttons.values():
            button.set_active(False)
        self.art_studio_nav.set_active(True)
        self.title.setText("Estúdio de Artes")
        self.subtitle.setText("Preparando o ambiente de criação…")
        self.header_identity.setVisible(False)
        _start_art_studio_loading(self)

    MainWindow._open_art_studio = open_art_studio
    _INSTALLED = True
