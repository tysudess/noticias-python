from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.auth.client import AuthApiError
from monitor_noticias.auth.models import AuthSession
from monitor_noticias.auth.runtime import AuthRuntime


class _PasswordWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str, str)
    finished = Signal()

    def __init__(self, operation) -> None:
        super().__init__()
        self.operation = operation

    def run(self) -> None:
        try:
            self.succeeded.emit(
                self.operation()
            )
        except AuthApiError as exc:
            self.failed.emit(
                exc.code,
                str(exc),
            )
        except Exception as exc:
            self.failed.emit(
                "PASSWORD_CHANGE_ERROR",
                str(exc) or exc.__class__.__name__,
            )
        finally:
            self.finished.emit()


class PasswordChangeDialog(QDialog):
    def __init__(
        self,
        runtime: AuthRuntime,
        *,
        forced: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.runtime = runtime
        self.forced = bool(forced)
        self.session: AuthSession | None = None
        self._thread: QThread | None = None
        self._worker: _PasswordWorker | None = None

        self.setWindowTitle(
            "Crie sua nova senha"
            if self.forced
            else "Alterar senha"
        )
        self.setModal(True)
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        title = QLabel(
            "Alteração obrigatória de senha"
            if self.forced
            else "Alterar minha senha"
        )
        title.setStyleSheet(
            "font-size:20px;font-weight:900;color:#0B3265;"
        )
        root.addWidget(title)

        description = QLabel(
            (
                "Sua senha atual é temporária. "
                "Crie uma nova senha para continuar."
            )
            if self.forced
            else (
                "Informe sua senha atual e escolha uma nova senha."
            )
        )
        description.setWordWrap(True)
        description.setStyleSheet("color:#607690;")
        root.addWidget(description)

        form = QFormLayout()
        form.setSpacing(10)

        self.current_password = QLineEdit()
        self.current_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.current_password.setPlaceholderText(
            "Senha atual / temporária"
        )

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.new_password.setPlaceholderText(
            "Mínimo de 8 caracteres"
        )

        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self.confirm_password.setPlaceholderText(
            "Repita a nova senha"
        )
        self.confirm_password.returnPressed.connect(
            self._change
        )

        form.addRow(
            "Senha atual:",
            self.current_password,
        )
        form.addRow(
            "Nova senha:",
            self.new_password,
        )
        form.addRow(
            "Confirmar:",
            self.confirm_password,
        )
        root.addLayout(form)

        self.message = QLabel(
            "A nova senha precisa ter pelo menos 8 caracteres."
        )
        self.message.setWordWrap(True)
        self.message.setStyleSheet(
            "color:#526B88;background:#F5F9FE;"
            "border:1px solid #D8E5F3;border-radius:8px;padding:9px;"
        )
        root.addWidget(self.message)

        self.change_button = QPushButton(
            "ALTERAR SENHA"
        )
        self.change_button.setDefault(True)
        self.change_button.setStyleSheet(
            "min-height:42px;background:#0D7FF2;color:white;"
            "border:0;border-radius:9px;font-weight:900;"
        )
        self.change_button.clicked.connect(
            self._change
        )
        root.addWidget(self.change_button)

        if not self.forced:
            cancel = QPushButton("Cancelar")
            cancel.clicked.connect(self.reject)
            root.addWidget(cancel)

    def _set_busy(self, busy: bool) -> None:
        self.change_button.setEnabled(not busy)
        self.current_password.setEnabled(not busy)
        self.new_password.setEnabled(not busy)
        self.confirm_password.setEnabled(not busy)

    def _change(self) -> None:
        current = self.current_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if not current or not new or not confirm:
            self.message.setText(
                "Preencha a senha atual, a nova senha e a confirmação."
            )
            return

        if len(new) < 8:
            self.message.setText(
                "A nova senha precisa ter pelo menos 8 caracteres."
            )
            return

        if new == current:
            self.message.setText(
                "A nova senha precisa ser diferente da senha atual."
            )
            return

        if new != confirm:
            self.message.setText(
                "A confirmação não corresponde à nova senha."
            )
            return

        if self._thread is not None and self._thread.isRunning():
            return

        self.message.setText("Alterando senha...")
        self._set_busy(True)

        thread = QThread(self)
        worker = _PasswordWorker(
            lambda: self.runtime.change_password(
                current,
                new,
            )
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._success)
        worker.failed.connect(self._failure)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)

        def cleanup():
            self._set_busy(False)
            self._thread = None
            self._worker = None

        thread.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _success(self, session: AuthSession) -> None:
        self.session = session
        self.message.setText("Senha alterada com sucesso.")
        self.accept()

    def _failure(self, _code: str, message: str) -> None:
        self.message.setText(message)
        self.current_password.clear()
        self.new_password.clear()
        self.confirm_password.clear()
        self.current_password.setFocus()
