from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QDate,
    QThread,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.auth.admin_api import (
    create_user,
    list_users,
    reset_password,
)
from monitor_noticias.auth.runtime import AuthRuntime


class _AdminWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        callback: Callable[[], Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._callback = callback

    def run(self) -> None:
        try:
            self.succeeded.emit(
                self._callback()
            )
        except Exception as exc:
            self.failed.emit(
                str(exc)
                or exc.__class__.__name__
            )


class AdminUsersPage(QWidget):
    """Gerenciamento de usuários exclusivo do perfil ADMIN."""

    def __init__(
        self,
        runtime: AuthRuntime,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.runtime = runtime
        self._workers: set[_AdminWorker] = set()
        self._users: list[dict[str, Any]] = []

        self._build_ui()
        self._set_status(
            "Pronto. Clique em Atualizar usuários para carregar a lista."
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("adminHeader")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 15, 18, 15)

        title_box = QVBoxLayout()

        title = QLabel("Administração de usuários")
        title.setObjectName("adminTitle")

        subtitle = QLabel(
            "Crie contas e redefina senhas sem abrir a planilha do Google. "
            "Todas as operações são validadas novamente pelo servidor."
        )
        subtitle.setObjectName("adminMuted")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hl.addLayout(title_box, 1)

        badge = QLabel("ADMIN • ACESSO RESTRITO")
        badge.setObjectName("adminBadge")
        hl.addWidget(badge)

        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(12)

        create_card = QFrame()
        create_card.setObjectName("adminCard")
        create_card.setMinimumWidth(390)
        create_card.setMaximumWidth(520)

        cl = QVBoxLayout(create_card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(9)

        create_title = QLabel("Criar novo usuário")
        create_title.setObjectName("adminCardTitle")
        cl.addWidget(create_title)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.username = QLineEdit()
        self.username.setPlaceholderText("ex.: joao.silva")

        self.name = QLineEdit()
        self.name.setPlaceholderText("Nome completo")

        self.profile = QComboBox()
        self.profile.addItems(
            [
                "OPERADOR",
                "CONSULTA",
                "EDICAO",
                "ADMIN",
            ]
        )

        self.max_devices = QSpinBox()
        self.max_devices.setRange(1, 20)
        self.max_devices.setValue(1)

        self.no_validity = QCheckBox("Sem data de validade")
        self.no_validity.setChecked(True)

        self.validity = QDateEdit()
        self.validity.setCalendarPopup(True)
        self.validity.setDisplayFormat("dd/MM/yyyy")
        self.validity.setDate(
            QDate.currentDate().addYears(1)
        )
        self.validity.setEnabled(False)

        self.no_validity.toggled.connect(
            lambda checked: self.validity.setEnabled(
                not checked
            )
        )

        self.permissions = QLineEdit()
        self.permissions.setPlaceholderText(
            "Opcional. Vazio = permissões do perfil; * = todas"
        )

        self.password = QLineEdit()
        self.password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.password.setPlaceholderText(
            "Senha temporária • mínimo 8 caracteres"
        )

        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.password_confirm.setPlaceholderText(
            "Confirme a senha temporária"
        )

        self.show_create_password = QCheckBox(
            "Mostrar senha temporária"
        )
        self.show_create_password.toggled.connect(
            self._toggle_create_password
        )

        fields = [
            ("Usuário", self.username),
            ("Nome", self.name),
            ("Perfil", self.profile),
            ("Máx. dispositivos", self.max_devices),
        ]

        row = 0
        for label, widget in fields:
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)
            row += 1

        form.addWidget(self.no_validity, row, 0, 1, 2)
        row += 1
        form.addWidget(QLabel("Validade"), row, 0)
        form.addWidget(self.validity, row, 1)
        row += 1
        form.addWidget(QLabel("Permissões"), row, 0)
        form.addWidget(self.permissions, row, 1)
        row += 1
        form.addWidget(QLabel("Senha temporária"), row, 0)
        form.addWidget(self.password, row, 1)
        row += 1
        form.addWidget(QLabel("Confirmar senha"), row, 0)
        form.addWidget(self.password_confirm, row, 1)

        cl.addLayout(form)
        cl.addWidget(self.show_create_password)

        hint = QLabel(
            "A senha é enviada por HTTPS ao Apps Script, transformada em hash "
            "e nunca é mantida em texto puro na planilha. O novo usuário será "
            "obrigado a trocá-la no primeiro acesso."
        )
        hint.setObjectName("adminMuted")
        hint.setWordWrap(True)
        cl.addWidget(hint)

        self.create_button = QPushButton("＋  Criar usuário")
        self.create_button.setObjectName("adminPrimary")
        self.create_button.clicked.connect(
            self._create_user
        )
        cl.addWidget(self.create_button)
        cl.addStretch(1)

        body.addWidget(create_card)

        manage_card = QFrame()
        manage_card.setObjectName("adminCard")

        ml = QVBoxLayout(manage_card)
        ml.setContentsMargins(18, 16, 18, 16)
        ml.setSpacing(10)

        top = QHBoxLayout()

        manage_title = QLabel("Usuários cadastrados")
        manage_title.setObjectName("adminCardTitle")
        top.addWidget(manage_title)

        top.addStretch(1)

        self.refresh_button = QPushButton("↻  Atualizar usuários")
        self.refresh_button.clicked.connect(
            self.load_users
        )
        top.addWidget(self.refresh_button)

        ml.addLayout(top)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Usuário",
                "Nome",
                "Perfil",
                "Status",
                "Validade",
                "Dispositivos",
                "Último login",
                "Trocar senha",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        ml.addWidget(self.table, 1)

        reset_box = QFrame()
        reset_box.setObjectName("adminReset")

        rl = QVBoxLayout(reset_box)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(8)

        self.selected_user = QLabel(
            "Selecione um usuário na tabela para redefinir a senha."
        )
        self.selected_user.setObjectName("adminSelected")
        rl.addWidget(self.selected_user)

        reset_row = QHBoxLayout()

        self.reset_password = QLineEdit()
        self.reset_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.reset_password.setPlaceholderText(
            "Nova senha temporária"
        )
        reset_row.addWidget(self.reset_password, 1)

        self.reset_confirm = QLineEdit()
        self.reset_confirm.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.reset_confirm.setPlaceholderText(
            "Confirme a senha"
        )
        reset_row.addWidget(self.reset_confirm, 1)

        self.show_reset_password = QCheckBox("Mostrar")
        self.show_reset_password.toggled.connect(
            self._toggle_reset_password
        )
        reset_row.addWidget(self.show_reset_password)

        self.reset_button = QPushButton(
            "Redefinir senha"
        )
        self.reset_button.setObjectName("adminDanger")
        self.reset_button.clicked.connect(
            self._reset_selected_password
        )
        reset_row.addWidget(self.reset_button)

        rl.addLayout(reset_row)

        reset_hint = QLabel(
            "Ao redefinir a senha, as sessões anteriores desse usuário serão "
            "revogadas e a nova senha será marcada como temporária."
        )
        reset_hint.setObjectName("adminMuted")
        reset_hint.setWordWrap(True)
        rl.addWidget(reset_hint)

        ml.addWidget(reset_box)
        body.addWidget(manage_card, 1)

        root.addLayout(body, 1)

        self.status = QLabel()
        self.status.setObjectName("adminStatus")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.table.itemSelectionChanged.connect(
            self._selection_changed
        )

        self.setStyleSheet(
            """
            QFrame#adminHeader, QFrame#adminCard {
                background:#FFFFFF;
                border:1px solid #D4E4F5;
                border-radius:12px;
            }
            QLabel#adminTitle {
                color:#082E67;
                font-size:20px;
                font-weight:900;
            }
            QLabel#adminCardTitle {
                color:#0A326C;
                font-size:15px;
                font-weight:900;
            }
            QLabel#adminMuted {
                color:#607CA6;
                font-size:10px;
            }
            QLabel#adminBadge {
                background:#FFF4DE;
                color:#8C5700;
                border:1px solid #F3D99E;
                border-radius:9px;
                padding:8px 12px;
                font-weight:900;
            }
            QFrame#adminReset {
                background:#F7FAFE;
                border:1px solid #D8E5F3;
                border-radius:10px;
            }
            QLabel#adminSelected {
                color:#153F78;
                font-weight:800;
            }
            QLabel#adminStatus {
                background:#EDF8F3;
                color:#087A58;
                border:1px solid #C7E9DA;
                border-radius:9px;
                padding:9px 12px;
                font-weight:700;
            }
            QLineEdit, QComboBox, QSpinBox, QDateEdit {
                min-height:34px;
                border:1px solid #C8DBEF;
                border-radius:8px;
                padding:0 9px;
                background:#FFFFFF;
                color:#12365F;
            }
            QPushButton {
                min-height:34px;
                border:1px solid #C7DBEF;
                border-radius:8px;
                background:#FFFFFF;
                color:#123F76;
                padding:0 12px;
                font-weight:800;
            }
            QPushButton#adminPrimary {
                min-height:42px;
                background:#087AF7;
                color:#FFFFFF;
                border:0;
            }
            QPushButton#adminDanger {
                background:#FFF3F5;
                color:#B12242;
                border:1px solid #F0C3CD;
            }
            QTableWidget {
                background:#FFFFFF;
                color:#12365F;
                border:1px solid #D5E4F3;
                border-radius:8px;
                gridline-color:#E6EEF7;
                selection-background-color:#DDEEFF;
                selection-color:#0A326C;
            }
            QHeaderView::section {
                background:#F1F7FD;
                color:#153F78;
                border:0;
                border-bottom:1px solid #D2E2F2;
                padding:7px;
                font-weight:800;
            }
            """
        )

    def refresh(self, _state=None) -> None:
        # A lista é atualizada explicitamente ao abrir a aba ou clicar em
        # Atualizar, evitando consultas contínuas ao Apps Script.
        pass

    def _toggle_create_password(self, visible: bool) -> None:
        mode = (
            QLineEdit.EchoMode.Normal
            if visible
            else QLineEdit.EchoMode.Password
        )
        self.password.setEchoMode(mode)
        self.password_confirm.setEchoMode(mode)

    def _toggle_reset_password(self, visible: bool) -> None:
        mode = (
            QLineEdit.EchoMode.Normal
            if visible
            else QLineEdit.EchoMode.Password
        )
        self.reset_password.setEchoMode(mode)
        self.reset_confirm.setEchoMode(mode)

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def _set_busy(self, busy: bool) -> None:
        self.create_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.reset_button.setEnabled(not busy)

    def _run(
        self,
        callback: Callable[[], Any],
        on_success: Callable[[Any], None],
        *,
        busy_text: str,
    ) -> None:
        self._set_busy(True)
        self._set_status(busy_text)

        worker = _AdminWorker(
            callback,
            self,
        )
        self._workers.add(worker)

        def cleanup() -> None:
            self._workers.discard(worker)
            self._set_busy(False)
            worker.deleteLater()

        def succeeded(value: object) -> None:
            cleanup()
            on_success(value)

        def failed(message: str) -> None:
            cleanup()
            self._operation_failed(message)

        worker.succeeded.connect(succeeded)
        worker.failed.connect(failed)
        worker.start()

    def _operation_failed(self, message: str) -> None:
        self._set_status(
            "Erro: " + message
        )
        QMessageBox.warning(
            self,
            "Administração de usuários",
            message,
        )

    def load_users(self) -> None:
        self._run(
            lambda: list_users(self.runtime),
            self._users_loaded,
            busy_text="Carregando usuários do servidor…",
        )

    def _users_loaded(self, users: object) -> None:
        self._users = (
            users
            if isinstance(users, list)
            else []
        )

        self.table.setRowCount(
            len(self._users)
        )

        for row, user in enumerate(self._users):
            values = [
                user.get("username", ""),
                user.get("name", ""),
                user.get("profile", ""),
                user.get("status", ""),
                user.get("validity", "") or "Sem validade",
                str(user.get("max_devices", "")),
                user.get("last_login", "") or "—",
                "Sim" if user.get("must_change_password") else "Não",
            ]

            for col, value in enumerate(values):
                self.table.setItem(
                    row,
                    col,
                    QTableWidgetItem(
                        str(value)
                    ),
                )

        self._set_status(
            f"{len(self._users)} usuário(s) carregado(s)."
        )

    def _create_user(self) -> None:
        username = self.username.text().strip()
        name = self.name.text().strip()
        password = self.password.text()
        confirmation = self.password_confirm.text()

        if not username or not name:
            self._operation_failed(
                "Informe usuário e nome."
            )
            return

        if len(password) < 8:
            self._operation_failed(
                "A senha temporária precisa ter pelo menos 8 caracteres."
            )
            return

        if password != confirmation:
            self._operation_failed(
                "A confirmação da senha não confere."
            )
            return

        validity = (
            ""
            if self.no_validity.isChecked()
            else self.validity.date().toString(
                "yyyy-MM-dd"
            )
        )

        kwargs = {
            "username": username,
            "name": name,
            "temporary_password": password,
            "profile": self.profile.currentText(),
            "validity": validity,
            "max_devices": self.max_devices.value(),
            "permissions": self.permissions.text().strip(),
        }

        self._run(
            lambda: create_user(
                self.runtime,
                **kwargs,
            ),
            self._user_created,
            busy_text=f"Criando usuário {username}…",
        )

    def _user_created(self, user: object) -> None:
        username = (
            user.get("username", "")
            if isinstance(user, dict)
            else ""
        )

        self.username.clear()
        self.name.clear()
        self.password.clear()
        self.password_confirm.clear()
        self.permissions.clear()
        self.profile.setCurrentText("OPERADOR")
        self.max_devices.setValue(1)
        self.no_validity.setChecked(True)

        self._set_status(
            f"Usuário {username} criado. A senha é temporária e deverá ser "
            "trocada no primeiro acesso."
        )

        self.load_users()

    def _selected_username(self) -> str:
        row = self.table.currentRow()

        if row < 0:
            return ""

        item = self.table.item(row, 0)

        return (
            item.text().strip()
            if item is not None
            else ""
        )

    def _selection_changed(self) -> None:
        username = self._selected_username()

        if username:
            self.selected_user.setText(
                f"Usuário selecionado: {username}"
            )
        else:
            self.selected_user.setText(
                "Selecione um usuário na tabela para redefinir a senha."
            )

    def _reset_selected_password(self) -> None:
        username = self._selected_username()

        if not username:
            self._operation_failed(
                "Selecione um usuário na tabela."
            )
            return

        password = self.reset_password.text()
        confirmation = self.reset_confirm.text()

        if len(password) < 8:
            self._operation_failed(
                "A nova senha temporária precisa ter pelo menos 8 caracteres."
            )
            return

        if password != confirmation:
            self._operation_failed(
                "A confirmação da nova senha não confere."
            )
            return

        answer = QMessageBox.question(
            self,
            "Redefinir senha",
            (
                f"Redefinir a senha de {username}?\n\n"
                "As sessões anteriores desse usuário serão revogadas e a "
                "senha será temporária."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self._run(
            lambda: reset_password(
                self.runtime,
                username=username,
                temporary_password=password,
            ),
            lambda _value: self._password_reset_done(
                username
            ),
            busy_text=f"Redefinindo senha de {username}…",
        )

    def _password_reset_done(self, username: str) -> None:
        self.reset_password.clear()
        self.reset_confirm.clear()

        self._set_status(
            f"Senha de {username} redefinida. Sessões antigas revogadas; "
            "troca obrigatória no próximo login."
        )
        self.load_users()
