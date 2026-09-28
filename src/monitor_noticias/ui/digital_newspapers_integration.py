from __future__ import annotations

from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.digital_newspapers_page import DigitalNewspapersPage
from monitor_noticias.ui.sections import Section
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem


_PAGE_KEY = "DIGITAL_NEWSPAPERS"


def install_digital_newspapers(window) -> DigitalNewspapersPage:
    """V77: adiciona Jornais Digitais sem alterar o enum/stack legado.

    A integração é propositalmente isolada para reduzir risco nas telas e
    correções anteriores. A página entra no QStackedWidget e usa um item próprio
    na sidebar; ao sair dela, o navigate() normal do MainWindow continua intacto.
    """

    existing = getattr(window, "_digital_newspapers_page", None)
    if existing is not None:
        return existing

    page = DigitalNewspapersPage(window.paths)
    window._digital_newspapers_page = page
    window.pages[_PAGE_KEY] = page
    window.stack.addWidget(page)

    nav = SidebarNavItem(
        icon_text="▥",
        label_text="Jornais Digitais",
        icon_color="#35C3FF",
    )

    def open_page() -> None:
        window._current = _PAGE_KEY
        window.stack.setCurrentWidget(page)

        for button in window.nav_buttons.values():
            button.set_active(False)
        nav.set_active(True)

        window.title.setText("Jornais Digitais")
        window.subtitle.setText(
            "Acesse edições completas usando suas próprias assinaturas."
        )
        window.header_identity.setVisible(True)
        page.refresh(None)

    nav.clicked.connect(open_page)
    window.nav_buttons[_PAGE_KEY] = nav

    layout = window.sidebar.layout()
    if layout is not None:
        settings_button = window.nav_buttons.get(Section.SETTINGS)
        settings_index = (
            layout.indexOf(settings_button)
            if settings_button is not None
            else -1
        )
        insert_at = (
            settings_index
            if settings_index >= 0
            else max(0, layout.count() - 2)
        )
        layout.insertWidget(insert_at, nav)

    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(page.shutdown)

    return page
