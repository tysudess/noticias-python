from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from monitor_noticias.auth.admin_api import delete_user, update_user
from monitor_noticias.ui.admin_users_page import AdminUsersPage


_PATCHED = False
_VALID_PROFILES = ("OPERADOR", "CONSULTA", "EDICAO", "ADMIN")
_VALID_STATUSES = ("ATIVO", "INATIVO", "BLOQUEADO")


def _actor_username(page) -> str:
    session = getattr(page.runtime, "session", None)
    user = getattr(session, "user", None)
    return str(getattr(user, "username", "") or "").strip().casefold()


def _selected_record(page):
    username = page._selected_username().strip().casefold()
    if not username:
        return None
    for user in getattr(page, "_users", []):
        if str(user.get("username", "")).strip().casefold() == username:
            return user
    return None


def _update_action_buttons(page) -> None:
    username = page._selected_username().strip().casefold()
    actor = _actor_username(page)
    own_account = bool(username and actor and username == actor)
    available = bool(username) and not own_account and not getattr(page, "_v114_busy", False)

    edit_button = getattr(page, "_v114_edit_button", None)
    delete_button = getattr(page, "_v114_delete_button", None)
    if edit_button is not None:
        edit_button.setEnabled(available)
        edit_button.setToolTip(
            "A conta da sessão atual é protegida."
            if own_account else "Editar nome, perfil, situação, validade, dispositivos e permissões."
        )
    if delete_button is not None:
        delete_button.setEnabled(available)
        delete_button.setToolTip(
            "Não é permitido excluir a conta da sessão atual."
            if own_account else "Excluir a conta selecionada e revogar suas sessões."
        )


def _install_management_controls(page) -> None:
    if getattr(page, "_v114_controls_installed", False):
        return

    table = getattr(page, "table", None)
    refresh_button = getattr(page, "refresh_button", None)
    if table is None or refresh_button is None:
        return

    manage_layout = table.parentWidget().layout()
    top_layout = None
    for index in range(manage_layout.count()):
        child_layout = manage_layout.itemAt(index).layout()
        if child_layout is not None and child_layout.indexOf(refresh_button) >= 0:
            top_layout = child_layout
            break
    if top_layout is None:
        return

    page._v114_edit_button = QPushButton("✎  Editar usuário")
    page._v114_edit_button.setObjectName("adminSecondary")
    page._v114_edit_button.clicked.connect(lambda: _edit_selected_user(page))
    top_layout.addWidget(page._v114_edit_button)

    page._v114_delete_button = QPushButton("⌫  Excluir usuário")
    page._v114_delete_button.setObjectName("adminDanger")
    page._v114_delete_button.clicked.connect(lambda: _delete_selected_user(page))
    top_layout.addWidget(page._v114_delete_button)

    page._v114_busy = False
    page.table.itemSelectionChanged.connect(lambda: _update_action_buttons(page))
    page._v114_controls_installed = True
    _update_action_buttons(page)


def _edit_selected_user(page) -> None:
    user = _selected_record(page)
    if not user:
        QMessageBox.information(page, "Editar usuário", "Selecione um usuário na tabela.")
        return

    username = str(user.get("username", "")).strip()
    if username.casefold() == _actor_username(page):
        QMessageBox.warning(
            page,
            "Editar usuário",
            "Por segurança, a conta usada nesta sessão não pode ser editada por esta tela.",
        )
        return

    dialog = QDialog(page)
    dialog.setWindowTitle(f"Editar usuário — {username}")
    dialog.setMinimumWidth(470)
    form = QFormLayout(dialog)

    name_edit = QLineEdit(str(user.get("name", "") or ""))
    name_edit.setPlaceholderText("Nome completo")
    profile_combo = QComboBox()
    profile_combo.addItems(list(_VALID_PROFILES))
    profile_combo.setCurrentText(str(user.get("profile", "CONSULTA") or "CONSULTA").upper())

    status_combo = QComboBox()
    status_combo.addItems(list(_VALID_STATUSES))
    existing_status = str(user.get("status", "ATIVO") or "ATIVO").upper()
    status_combo.setCurrentText(existing_status if existing_status in _VALID_STATUSES else "INATIVO")

    no_validity = QCheckBox("Sem data de validade")
    raw_validity = str(user.get("validity", "") or "").strip()[:10]
    no_validity.setChecked(not bool(raw_validity))
    validity_edit = QDateEdit()
    validity_edit.setCalendarPopup(True)
    validity_edit.setDisplayFormat("dd/MM/yyyy")
    parsed_date = QDate.fromString(raw_validity, "yyyy-MM-dd")
    validity_edit.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate().addYears(1))
    validity_edit.setEnabled(not no_validity.isChecked())
    no_validity.toggled.connect(lambda checked: validity_edit.setEnabled(not checked))

    devices = QSpinBox()
    devices.setRange(1, 20)
    try:
        devices.setValue(max(1, min(20, int(user.get("max_devices", 1) or 1))))
    except (TypeError, ValueError):
        devices.setValue(1)

    permissions = QLineEdit(str(user.get("permissions", "") or ""))
    permissions.setPlaceholderText("Vazio = permissões do perfil; * = todas")

    username_edit = QLineEdit(username)
    username_edit.setReadOnly(True)
    form.addRow("Usuário (não editável)", username_edit)
    form.addRow("Nome", name_edit)
    form.addRow("Perfil", profile_combo)
    form.addRow("Situação", status_combo)
    form.addRow("Validade", validity_edit)
    form.addRow("", no_validity)
    form.addRow("Máx. dispositivos", devices)
    form.addRow("Permissões", permissions)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)

    dialog.setStyleSheet(
        "QDialog{background:#F5F9FF;color:#08245F;}"
        "QLineEdit,QComboBox,QSpinBox,QDateEdit{min-height:34px;border:1px solid #C8DBEF;"
        "border-radius:8px;padding:0 8px;background:white;color:#12365F;}"
        "QPushButton{min-height:32px;padding:0 12px;border:1px solid #C7DBEF;"
        "border-radius:7px;background:white;color:#123F76;font-weight:700;}"
    )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    name = name_edit.text().strip()
    if not name:
        page._operation_failed("Informe o nome do usuário.")
        return

    validity = "" if no_validity.isChecked() else validity_edit.date().toString("yyyy-MM-dd")
    changed_profile = profile_combo.currentText() != str(user.get("profile", "")).upper()
    changed_status = status_combo.currentText() != str(user.get("status", "")).upper()
    prompt = (
        f"Salvar as alterações de {username}?"
        "\n\nAs sessões atuais desse usuário serão revogadas e ele precisará entrar novamente."
    )
    if changed_profile or changed_status:
        prompt += "\nA alteração de perfil/situação pode mudar o acesso ao aplicativo."

    answer = QMessageBox.question(
        page,
        "Confirmar alteração",
        prompt,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    payload = {
        "username": username,
        "name": name,
        "profile": profile_combo.currentText(),
        "status": status_combo.currentText(),
        "validity": validity,
        "max_devices": devices.value(),
        "permissions": permissions.text().strip(),
    }
    page._run(
        lambda: update_user(page.runtime, **payload),
        lambda updated: _user_updated(page, username, updated),
        busy_text=f"Atualizando usuário {username}…",
    )


def _user_updated(page, username: str, updated) -> None:
    page._set_status(
        f"Usuário {username} atualizado. Sessões anteriores revogadas; o usuário precisará entrar novamente."
    )
    page.load_users()


def _delete_selected_user(page) -> None:
    user = _selected_record(page)
    if not user:
        QMessageBox.information(page, "Excluir usuário", "Selecione um usuário na tabela.")
        return

    username = str(user.get("username", "")).strip()
    if username.casefold() == _actor_username(page):
        QMessageBox.warning(
            page,
            "Excluir usuário",
            "Por segurança, não é permitido excluir a conta usada nesta sessão.",
        )
        return

    answer = QMessageBox.question(
        page,
        "Excluir usuário",
        (
            f"Excluir permanentemente a conta {username}?"
            "\n\nO acesso será revogado, as sessões serão encerradas e os dispositivos registrados serão desativados."
            "\n\nEsta ação não pode ser desfeita pela Central."
        ),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    page._run(
        lambda: delete_user(page.runtime, username=username),
        lambda _result: _user_deleted(page, username),
        busy_text=f"Excluindo usuário {username}…",
    )


def _user_deleted(page, username: str) -> None:
    page._set_status(f"Usuário {username} excluído; sessões revogadas e dispositivos desativados.")
    page.load_users()


def install_admin_user_management_patch() -> None:
    """Adiciona botões de edição/exclusão à tela existente sem recriar o layout."""
    global _PATCHED
    if _PATCHED:
        return

    original_init = AdminUsersPage.__init__
    original_set_busy = AdminUsersPage._set_busy

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_management_controls(self)

    def patched_set_busy(self, busy: bool):
        self._v114_busy = bool(busy)
        original_set_busy(self, busy)
        _update_action_buttons(self)

    AdminUsersPage.__init__ = patched_init
    AdminUsersPage._set_busy = patched_set_busy
    _PATCHED = True
