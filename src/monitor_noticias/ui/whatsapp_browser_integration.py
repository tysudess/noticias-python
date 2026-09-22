from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.sections import Section
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem
from monitor_noticias.ui.whatsapp_browser_page import (
    WhatsAppBrowserPage,
)


def install_whatsapp_browser(
    window,
) -> WhatsAppBrowserPage:
    """Adiciona a aba WhatsApp sem reescrever MainWindow."""

    existing = getattr(
        window,
        "whatsapp_browser_page",
        None,
    )
    if existing is not None:
        return existing

    page = WhatsAppBrowserPage(
        window.paths.root,
        window.stack,
    )

    automation_page = (
        window.pages.get(
            Section.SPREADSHEETS
        )
    )
    page.set_automation_page(
        automation_page
    )

    window.stack.addWidget(
        page
    )

    nav = SidebarNavItem(
        icon_text="WA",
        label_text="WhatsApp",
        icon_color="#29D6A3",
    )

    sidebar_layout = (
        window.sidebar.layout()
    )

    spreadsheets_nav = (
        window.nav_buttons.get(
            Section.SPREADSHEETS
        )
    )

    insert_index = (
        sidebar_layout.indexOf(
            spreadsheets_nav
        )
        if spreadsheets_nav is not None
        else -1
    )

    if insert_index >= 0:
        sidebar_layout.insertWidget(
            insert_index,
            nav,
        )
    else:
        sidebar_layout.addWidget(
            nav
        )

    previous_navigate = (
        window.navigate
    )

    def normal_navigate(section):
        nav.set_active(False)
        return previous_navigate(
            section
        )

    window.navigate = normal_navigate

    recorder_nav = getattr(
        window,
        "screen_recorder_nav",
        None,
    )

    if recorder_nav is not None:
        try:
            recorder_nav.clicked.connect(
                lambda: nav.set_active(
                    False
                )
            )
        except Exception:
            pass

    def open_whatsapp():
        for button in (
            window.nav_buttons.values()
        ):
            button.set_active(False)

        recorder = getattr(
            window,
            "screen_recorder_nav",
            None,
        )
        if recorder is not None:
            recorder.set_active(False)

        nav.set_active(True)
        window.stack.setCurrentWidget(
            page
        )
        window.header_identity.setVisible(
            True
        )
        window.title.setText(
            "WhatsApp"
        )
        window.subtitle.setText(
            "Chrome portátil persistente compartilhado com a Automação de Planilhas"
        )
        page.on_activated()

    nav.clicked.connect(
        open_whatsapp
    )

    tray_menu = (
        window.tray.contextMenu()
    )

    open_action = QAction(
        "Abrir WhatsApp",
        window,
    )
    open_action.triggered.connect(
        open_whatsapp
    )

    if tray_menu is not None:
        exit_action = None
        for action in (
            tray_menu.actions()
        ):
            if action.text() == "Sair":
                exit_action = action
                break

        if exit_action is not None:
            tray_menu.insertAction(
                exit_action,
                open_action,
            )
        else:
            tray_menu.addAction(
                open_action
            )

    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(
            page.shutdown
        )

    window.whatsapp_browser_page = (
        page
    )
    window.whatsapp_browser_nav = (
        nav
    )
    window.whatsapp_browser_open_action = (
        open_action
    )

    return page
