from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.screen_recorder_page import ScreenRecorderPage
from monitor_noticias.ui.sections import Section
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem


def install_screen_recorder(window) -> ScreenRecorderPage:
    """Instala o Gravador de Tela sem reescrever o MainWindow inteiro.

    A página é um QWidget nativo do PySide6 e entra no mesmo QStackedWidget
    usado por Notícias, Capas, Editor de PDF, Editor de Vídeo e Planilhas.
    """

    existing = getattr(
        window,
        "screen_recorder_page",
        None,
    )
    if existing is not None:
        return existing

    page = ScreenRecorderPage(
        window.paths.root,
        window.stack,
    )
    window.stack.addWidget(page)

    nav = SidebarNavItem(
        icon_text="●",
        label_text="Gravador de Tela",
        icon_color="#FF4D6D",
    )

    # Insere imediatamente antes de Configurações,
    # preservando Configurações como a última aba.
    sidebar_layout = window.sidebar.layout()
    settings_nav = window.nav_buttons.get(
        Section.SETTINGS
    )

    settings_index = (
        sidebar_layout.indexOf(settings_nav)
        if settings_nav is not None
        else -1
    )

    if settings_index >= 0:
        sidebar_layout.insertWidget(
            settings_index,
            nav,
        )
    else:
        sidebar_layout.addWidget(nav)

    original_navigate = window.navigate

    def normal_navigate(section):
        nav.set_active(False)
        return original_navigate(section)

    # Os lambdas do MainWindow consultam self.navigate no momento do clique,
    # então envolver o método da instância mantém todos os atalhos atuais.
    window.navigate = normal_navigate

    def open_recorder():
        for button in window.nav_buttons.values():
            button.set_active(False)

        nav.set_active(True)
        window.stack.setCurrentWidget(page)
        window.header_identity.setVisible(True)
        window.title.setText(
            "Gravador de Tela"
        )
        window.subtitle.setText(
            "Grave tela inteira ou uma área personalizada em MP4."
        )
        page.on_activated()

    nav.clicked.connect(open_recorder)

    # Ações do tray: essenciais quando a opção
    # "Ocultar a Central depois de iniciar" estiver marcada.
    tray_menu = window.tray.contextMenu()
    exit_action = None

    if tray_menu is not None:
        for action in tray_menu.actions():
            if action.text() == "Sair":
                exit_action = action
                break

    open_action = QAction(
        "Abrir Gravador de Tela",
        window,
    )
    open_action.triggered.connect(
        open_recorder
    )

    pause_action = QAction(
        "Pausar gravação de tela",
        window,
    )
    pause_action.setEnabled(False)
    pause_action.triggered.connect(
        page.toggle_pause
    )

    stop_action = QAction(
        "Parar gravação de tela",
        window,
    )
    stop_action.setEnabled(False)
    stop_action.triggered.connect(
        page.stop_recording
    )

    if tray_menu is not None:
        if exit_action is not None:
            tray_menu.insertSeparator(
                exit_action
            )
            tray_menu.insertAction(
                exit_action,
                open_action,
            )
            tray_menu.insertAction(
                exit_action,
                pause_action,
            )
            tray_menu.insertAction(
                exit_action,
                stop_action,
            )
        else:
            tray_menu.addSeparator()
            tray_menu.addAction(open_action)
            tray_menu.addAction(pause_action)
            tray_menu.addAction(stop_action)

    def update_tray(state: str) -> None:
        pause_action.setEnabled(
            state
            in {
                page.RECORDING,
                page.PAUSED,
            }
        )
        stop_action.setEnabled(
            state
            in {
                page.STARTING,
                page.RECORDING,
                page.PAUSED,
                page.ERROR,
            }
        )
        pause_action.setText(
            "Continuar gravação de tela"
            if state == page.PAUSED
            else "Pausar gravação de tela"
        )

    page.state_changed.connect(
        update_tray
    )

    app = QApplication.instance()

    if app is not None:
        app.aboutToQuit.connect(
            page.shutdown
        )

    window.screen_recorder_page = page
    window.screen_recorder_nav = nav
    window.screen_recorder_open_action = open_action
    window.screen_recorder_pause_action = pause_action
    window.screen_recorder_stop_action = stop_action

    return page
