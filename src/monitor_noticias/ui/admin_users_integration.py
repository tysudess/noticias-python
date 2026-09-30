from __future__ import annotations

import types

from monitor_noticias.auth.models import AuthSession
from monitor_noticias.auth.runtime import AuthRuntime
from monitor_noticias.ui.admin_users_page import AdminUsersPage
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem


_ADMIN_SENTINEL = "__central_admin_users__"


def install_admin_users_page(
    window,
    runtime: AuthRuntime,
    session: AuthSession,
) -> None:
    """Instala a aba Administração somente para perfil ADMIN."""

    if str(session.user.profile or "").strip().upper() != "ADMIN":
        return

    if getattr(window, "_admin_users_installed", False):
        return

    page = AdminUsersPage(
        runtime,
        window,
    )

    window.stack.addWidget(page)

    button = SidebarNavItem(
        icon_text="♚",
        label_text="Administração",
        icon_color="#FFD66B",
        parent=window.sidebar,
    )

    layout = window.sidebar.layout()

    status_index = -1
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is window.sidebar_status_card:
            status_index = index
            break

    insert_index = (
        max(0, status_index - 1)
        if status_index >= 0
        else max(0, layout.count() - 1)
    )

    layout.insertWidget(
        insert_index,
        button,
    )

    original_navigate = window.navigate

    def navigate_with_admin_reset(self, section):
        button.set_active(False)
        return original_navigate(section)

    window.navigate = types.MethodType(
        navigate_with_admin_reset,
        window,
    )

    def open_admin() -> None:
        for nav in window.nav_buttons.values():
            nav.set_active(False)

        button.set_active(True)
        window._current = _ADMIN_SENTINEL
        window.stack.setCurrentWidget(page)

        window.title.setText(
            "Administração"
        )
        window.subtitle.setText(
            "Cadastro de usuários e redefinição segura de senhas."
        )
        window.header_identity.setVisible(True)

        try:
            window._last_refresh_signature = (
                window._state_signature()
            )
        except Exception:
            pass

        page.load_users()

    button.clicked.connect(
        open_admin
    )

    window._admin_users_installed = True
    window._admin_users_page = page
    window._admin_users_button = button
