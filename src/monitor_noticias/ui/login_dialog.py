from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from monitor_noticias.auth.client import AuthApiError
from monitor_noticias.auth.models import AuthSession
from monitor_noticias.auth.runtime import AuthRuntime
from monitor_noticias.ui.password_change_dialog import PasswordChangeDialog


class _AuthWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str, str)
    finished = Signal()

    def __init__(self, operation) -> None:
        super().__init__()
        self.operation = operation

    def run(self) -> None:
        try:
            self.succeeded.emit(self.operation())
        except AuthApiError as exc:
            self.failed.emit(exc.code, str(exc))
        except Exception as exc:
            self.failed.emit(
                "AUTH_ERROR",
                str(exc) or exc.__class__.__name__,
            )
        finally:
            self.finished.emit()


class ProxyDialog(QDialog):
    def __init__(self, runtime: AuthRuntime, parent=None) -> None:
        super().__init__(parent)
        self.runtime = runtime

        self.setWindowTitle("Proxy Geral")
        self.setModal(True)
        self.setMinimumWidth(470)

        cfg = runtime.proxy_settings.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        title = QLabel("Configuração do Proxy Geral")
        title.setStyleSheet("font-size:18px;font-weight:800;")
        root.addWidget(title)

        subtitle = QLabel(
            "Esta configuração também será usada para acessar o servidor de login."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#5f7290;")
        root.addWidget(subtitle)

        self.enabled = QCheckBox("Usar Proxy Geral")
        self.enabled.setChecked(cfg.enabled)
        root.addWidget(self.enabled)

        form = QFormLayout()
        form.setSpacing(10)

        self.host = QLineEdit(cfg.host)

        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(cfg.port)

        self.username = QLineEdit(cfg.username)
        self.password = QLineEdit(cfg.password)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Servidor:", self.host)
        form.addRow("Porta:", self.port)
        form.addRow("Usuário:", self.username)
        form.addRow("Senha:", self.password)
        root.addLayout(form)

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color:#49617f;")
        root.addWidget(self.message)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        test = QPushButton("Testar")
        test.clicked.connect(self._test)
        buttons.addWidget(test)

        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Salvar")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(save)

        root.addLayout(buttons)

    def _store(self) -> None:
        self.runtime.proxy_settings.save(
            enabled=self.enabled.isChecked(),
            host=self.host.text(),
            port=self.port.value(),
            username=self.username.text(),
            password=self.password.text(),
        )

    def _test(self) -> None:
        try:
            self._store()
        except Exception as exc:
            self.message.setText(
                "Não foi possível salvar o proxy: "
                + (str(exc) or exc.__class__.__name__)
            )
            return

        if not self.enabled.isChecked():
            ok, message = self.runtime.client.test_server()
        else:
            ok, message = self.runtime.proxy_settings.test_connection()

            if ok:
                server_ok, server_message = self.runtime.client.test_server()
                if not server_ok:
                    ok = False
                    message = server_message
                else:
                    message = "Proxy conectado e servidor de autenticação acessível."

        self.message.setText(("✓  " if ok else "✕  ") + message)

    def _save(self) -> None:
        try:
            self._store()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Proxy Geral",
                "Não foi possível salvar o proxy.\n\n"
                + (str(exc) or exc.__class__.__name__),
            )
            return

        self.accept()


class LoginDialog(QDialog):
    """Tela de autenticação exibida antes da MainWindow."""

    def __init__(
        self,
        runtime: AuthRuntime,
        *,
        app_icon=None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.runtime = runtime
        self.session: AuthSession | None = None
        self._thread: QThread | None = None
        self._worker: _AuthWorker | None = None

        self.setWindowTitle("Central Inteligente de Mídia — Acesso")
        self.setModal(True)
        self.setFixedSize(540, 640)

        if app_icon is not None and not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.setStyleSheet(
            """
            QDialog { background:#F4F8FD; }
            QFrame#card {
                background:#FFFFFF;
                border:1px solid #D8E4F2;
                border-radius:18px;
            }
            QLabel#brand {
                color:#082B61;
                font-size:25px;
                font-weight:900;
            }
            QLabel#subtitle {
                color:#647895;
                font-size:12px;
            }
            QLabel#message {
                color:#46617F;
                background:#F5F9FE;
                border:1px solid #DCE7F4;
                border-radius:10px;
                padding:10px;
            }
            QLineEdit {
                min-height:42px;
                border:1px solid #BFD3EA;
                border-radius:9px;
                padding:0 12px;
                background:#FFFFFF;
            }
            QLineEdit:focus { border:2px solid #1683F8; }
            QPushButton {
                min-height:42px;
                border-radius:9px;
                border:1px solid #BED2E9;
                background:#FFFFFF;
                font-weight:700;
                color:#12345D;
                padding:0 14px;
            }
            QPushButton#primary {
                background:#0D7FF2;
                color:#FFFFFF;
                border:0;
                font-weight:900;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)

        card = QFrame()
        card.setObjectName("card")

        box = QVBoxLayout(card)
        box.setContentsMargins(28, 28, 28, 28)
        box.setSpacing(14)

        brand = QLabel("CENTRAL INTELIGENTE DE MÍDIA")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(brand)

        subtitle = QLabel("Acesso autorizado")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(subtitle)
        box.addSpacing(12)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Usuário")
        box.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Senha")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.returnPressed.connect(self._login)
        box.addWidget(self.password)

        self.remember = QCheckBox("Manter conectado neste computador")
        self.remember.setChecked(True)
        box.addWidget(self.remember)

        self.message = QLabel("Informe seu usuário e senha.")
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        box.addWidget(self.message)

        self.login_button = QPushButton("ENTRAR")
        self.login_button.setObjectName("primary")
        self.login_button.clicked.connect(self._login)
        box.addWidget(self.login_button)

        proxy_row = QHBoxLayout()

        self.proxy_status = QLabel()
        self.proxy_status.setStyleSheet("color:#506B8C;")
        proxy_row.addWidget(self.proxy_status, 1)

        proxy_button = QPushButton("Configurar proxy")
        proxy_button.clicked.connect(self._proxy)
        proxy_row.addWidget(proxy_button)
        box.addLayout(proxy_row)

        server_test = QPushButton("Testar conexão com servidor")
        server_test.clicked.connect(self._test_server)
        box.addWidget(server_test)

        device = runtime.device
        device_label = QLabel(
            "Computador: " + device.device_name + "\n" + device.os_name
        )
        device_label.setObjectName("subtitle")
        device_label.setWordWrap(True)
        box.addWidget(device_label)
        box.addStretch(1)

        root.addWidget(card)
        self._refresh_proxy_status()

        token = runtime.saved_token()
        if token:
            self.message.setText("Validando sessão salva...")
            self._run_async(
                lambda: runtime.client.validate(token),
                self._saved_session_ok,
            )

    def _refresh_proxy_status(self) -> None:
        cfg = self.runtime.proxy_settings.load()

        if cfg.enabled:
            self.proxy_status.setText(
                f"● Proxy ativo — {cfg.host}:{cfg.port}"
            )
        else:
            self.proxy_status.setText("○ Proxy inativo")

    def _set_busy(self, busy: bool) -> None:
        self.login_button.setEnabled(not busy)
        self.username.setEnabled(not busy)
        self.password.setEnabled(not busy)

    def _run_async(self, operation, on_success) -> None:
        if self._thread is not None and self._thread.isRunning():
            return

        self._set_busy(True)

        thread = QThread(self)
        worker = _AuthWorker(operation)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.succeeded.connect(on_success)
        worker.failed.connect(self._auth_failed)
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

    def _complete_session(self, session: AuthSession) -> None:
        self.runtime.session = session

        if session.user.must_change_password:
            self.message.setText(
                "Sua senha é temporária. Altere-a para continuar."
            )

            dialog = PasswordChangeDialog(
                self.runtime,
                forced=True,
                parent=self,
            )

            if (
                dialog.exec()
                == QDialog.DialogCode.Accepted
                and dialog.session is not None
            ):
                self.session = dialog.session
                self.accept()
                return

            try:
                self.runtime.logout()
            except Exception:
                self.runtime.token_store.clear()
                self.runtime.session = None

            self.message.setText(
                "A alteração da senha temporária é obrigatória para entrar."
            )
            return

        self.session = session
        self.accept()

    def _saved_session_ok(self, session: AuthSession) -> None:
        self._complete_session(session)

    def _login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            self.message.setText("Informe usuário e senha.")
            return

        self.message.setText("Validando acesso...")
        remember = self.remember.isChecked()

        self._run_async(
            lambda: self.runtime.login(
                username,
                password,
                remember=remember,
            ),
            self._login_ok,
        )

    def _login_ok(self, session: AuthSession) -> None:
        self._complete_session(session)

    def _auth_failed(self, code: str, message: str) -> None:
        if code in {
            "NETWORK_ERROR",
            "NETWORK_TIMEOUT",
            "PROXY_ERROR",
            "PROXY_NOT_READY",
        }:
            prefix = (
                "Não foi possível validar o acesso. "
                "Verifique a conexão e o Proxy Geral.\n\n"
            )
        else:
            prefix = ""

        self.message.setText(prefix + message)
        self.password.clear()
        self.password.setFocus()

    def _proxy(self) -> None:
        dialog = ProxyDialog(self.runtime, self)
        dialog.exec()
        self._refresh_proxy_status()

    def _test_server(self) -> None:
        self.message.setText("Testando conexão...")
        self._run_async(
            self.runtime.client.test_server,
            self._server_test_result,
        )

    def _server_test_result(self, result) -> None:
        ok, message = result
        self.message.setText(("✓  " if ok else "✕  ") + message)
