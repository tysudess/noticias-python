from __future__ import annotations

import types

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton

from monitor_noticias.auth.client import AuthApiError
from monitor_noticias.auth.models import AuthSession
from monitor_noticias.auth.runtime import AuthRuntime
from monitor_noticias.ui.sections import Section
from monitor_noticias.ui.password_change_dialog import PasswordChangeDialog


SECTION_PERMISSION = {
    Section.HOME: "home",
    Section.NEWS: "news",
    Section.VIDEOS: "videos",
    Section.DEMANDS: "demands",
    Section.SOURCES: "sources",
    Section.HISTORY: "history",
    Section.TERMS: "terms",
    Section.STOP: "stop",
    Section.NEWS_EXTRACTOR: "news_extractor",
    Section.COVERS: "covers",
    Section.PDF_EDITOR: "pdf_editor",
    Section.EXTRACTOR: "extractor",
    Section.VIDEO_EDITOR: "video_editor",
    Section.SETTINGS: "settings",
}


class _ValidationWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, runtime: AuthRuntime) -> None:
        super().__init__()
        self.runtime = runtime

    def run(self) -> None:
        try:
            self.succeeded.emit(self.runtime.validate_current())
        except AuthApiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)
        finally:
            self.finished.emit()


def _find_layout_with_widget(layout, widget):
    if layout is None:
        return None

    for index in range(layout.count()):
        item = layout.itemAt(index)

        if item.widget() is widget:
            return layout

        child_layout = item.layout()
        if child_layout is not None:
            found = _find_layout_with_widget(child_layout, widget)
            if found is not None:
                return found

    return None


def _allowed_sections(session: AuthSession) -> set[Section]:
    permissions = session.user.permissions
    allowed = {Section.HOME}

    for section, permission in SECTION_PERMISSION.items():
        if permission in permissions:
            allowed.add(section)

    return allowed


def install_authenticated_window(
    window,
    runtime: AuthRuntime,
    session: AuthSession,
) -> None:
    """Aplica permissões e identidade do usuário na MainWindow."""

    allowed = _allowed_sections(session)

    window._auth_runtime = runtime
    window._auth_session = session
    window._auth_allowed_sections = allowed

    for section, button in window.nav_buttons.items():
        permission = SECTION_PERMISSION.get(section)

        if permission is not None and section not in allowed:
            button.setVisible(False)

    original_navigate = window.navigate

    def authenticated_navigate(self, section):
        if section in SECTION_PERMISSION and section not in self._auth_allowed_sections:
            self.footer_right.setText("Acesso não permitido para este usuário.")

            if self._current not in self._auth_allowed_sections:
                return original_navigate(Section.HOME)

            return None

        return original_navigate(section)

    window.navigate = types.MethodType(
        authenticated_navigate,
        window,
    )

    tray_menu = (
        window.tray.contextMenu()
        if window.tray is not None
        else None
    )

    if tray_menu is not None:
        action_permissions = {
            "Buscar notícias agora": "news",
            "Buscar vídeos agora": "videos",
            "Buscar demandas agora": "demands",
            "Parar buscas": "stop",
        }

        for action in tray_menu.actions():
            required = action_permissions.get(action.text())

            if required and required not in session.user.permissions:
                action.setEnabled(False)

    header_layout = _find_layout_with_widget(
        window.centralWidget().layout(),
        window.clock,
    )

    if header_layout is not None:
        user_label = QLabel(
            "👤  "
            + session.display_name
            + "\n"
            + (session.user.profile or "USUÁRIO")
        )
        user_label.setObjectName("authUserChip")
        user_label.setStyleSheet(
            """
            QLabel#authUserChip {
                background:#F1F7FF;
                color:#103A6E;
                border:1px solid #C7DCF2;
                border-radius:10px;
                padding:7px 10px;
                font-weight:700;
            }
            """
        )

        account_button = QPushButton("Minha conta")
        account_button.setStyleSheet(
            """
            QPushButton {
                background:#FFFFFF;
                color:#174C84;
                border:1px solid #C1D7EE;
                border-radius:9px;
                padding:8px 10px;
                font-weight:700;
            }
            """
        )

        logout_button = QPushButton("Sair da conta")
        logout_button.setStyleSheet(
            """
            QPushButton {
                background:#FFFFFF;
                color:#9D2540;
                border:1px solid #E7BEC8;
                border-radius:9px;
                padding:8px 10px;
                font-weight:700;
            }
            """
        )

        header_layout.insertWidget(
            max(0, header_layout.count() - 1),
            user_label,
        )
        header_layout.insertWidget(
            max(0, header_layout.count() - 1),
            account_button,
        )
        header_layout.insertWidget(
            max(0, header_layout.count() - 1),
            logout_button,
        )

        window._auth_user_label = user_label
        window._auth_account_button = account_button
        window._auth_logout_button = logout_button

        def change_password():
            dialog = PasswordChangeDialog(
                runtime,
                forced=False,
                parent=window,
            )

            if (
                dialog.exec()
                == dialog.DialogCode.Accepted
                and dialog.session is not None
            ):
                new_session = dialog.session
                window._auth_session = new_session
                user_label.setText(
                    "👤  "
                    + new_session.display_name
                    + "\n"
                    + (new_session.user.profile or "USUÁRIO")
                )
                QMessageBox.information(
                    window,
                    "Minha conta",
                    "Senha alterada com sucesso.",
                )

        account_button.clicked.connect(change_password)

        def logout():
            answer = QMessageBox.question(
                window,
                "Sair da conta",
                "Deseja encerrar sua sessão neste computador?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

            try:
                runtime.logout()
            except Exception:
                runtime.token_store.clear()

            window.exit_application()

        logout_button.clicked.connect(logout)

    if tray_menu is not None:
        tray_menu.addSeparator()
        change_password_action = tray_menu.addAction("Alterar senha")

        def tray_change_password():
            dialog = PasswordChangeDialog(
                runtime,
                forced=False,
                parent=window,
            )

            if (
                dialog.exec()
                == dialog.DialogCode.Accepted
                and dialog.session is not None
            ):
                window._auth_session = dialog.session

        change_password_action.triggered.connect(
            tray_change_password
        )

        logout_action = tray_menu.addAction("Sair da conta")

        def tray_logout():
            try:
                runtime.logout()
            except Exception:
                runtime.token_store.clear()

            window.exit_application()

        logout_action.triggered.connect(tray_logout)

    timer = QTimer(window)
    timer.setInterval(30 * 60 * 1000)

    window._auth_validation_timer = timer
    window._auth_validation_thread = None
    window._auth_validation_worker = None

    def validate_periodically():
        current_thread = getattr(
            window,
            "_auth_validation_thread",
            None,
        )

        if current_thread is not None and current_thread.isRunning():
            return

        thread = QThread(window)
        worker = _ValidationWorker(runtime)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def valid(new_session):
            window._auth_session = new_session

        def invalid(message: str):
            runtime.token_store.clear()
            timer.stop()

            QMessageBox.critical(
                window,
                "Sessão encerrada",
                "Seu acesso não pôde ser validado.\n\n"
                + message
                + "\n\nA Central será encerrada.",
            )

            window.exit_application()

        worker.succeeded.connect(valid)
        worker.failed.connect(invalid)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)

        def cleanup():
            window._auth_validation_thread = None
            window._auth_validation_worker = None

        thread.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)

        window._auth_validation_thread = thread
        window._auth_validation_worker = worker
        thread.start()

    timer.timeout.connect(validate_periodically)
    timer.start()

    window.navigate(Section.HOME)
