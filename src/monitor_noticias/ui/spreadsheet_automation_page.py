from __future__ import annotations

import ctypes
import json
import os
import shutil
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QTimer,
    Qt,
)
from PySide6.QtGui import QWindow

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import ProxySettings
from monitor_noticias.ui.controller import (
    MainUiController,
)
from monitor_noticias.ui.pages import BasePage


class SpreadsheetAutomationPage(BasePage):
    """Hospeda o AutomacaoPlanilhas Windows Portable v1.0.4.

    Esta versão remove o motor Node/whatsapp-web.js que foi desenvolvido
    dentro do Central e usa diretamente o executável standalone fornecido
    pelo usuário, mantendo o mesmo programa que já funciona separadamente.
    """

    TOOL_EXE = (
        "AutomacaoPlanilhas-Windows-Portable-v1.0.4.exe"
    )

    DEFAULT_APPS_SCRIPT_URL = (
        "https://script.google.com/macros/s/"
        "AKfycbz9zWPX0OgVa7obrmqm5WSu1fImaTiyWz0pR3wuc13xl-uCS5KYTF4rhbRitrv26PBh/exec"
    )

    DEFAULT_GROUPS = [
        "556191047689-1555547406@g.us",
        "120363025807487932@g.us",
        "556192528699-1447447254@g.us",
    ]

    def __init__(
        self,
        controller: MainUiController,
        app_root: Path,
    ) -> None:
        super().__init__(controller)

        self.app_root = Path(app_root)
        self.tool_dir = (
            self.app_root
            / "tools"
            / "spreadsheet_automation"
        )
        self.exe_path = (
            self.tool_dir
            / self.TOOL_EXE
        )
        self.config_path = (
            self.tool_dir
            / "config.json"
        )

        self.process: QProcess | None = None

        self._embedded_hwnd: int | None = None
        self._embedded_original_style: int | None = None

        # Embedding supported by Qt for foreign native windows.
        # This replaces the old SetParent-only path that displayed the
        # Electron window but did not reliably transfer keyboard focus.
        self._native_window: QWindow | None = None
        self._window_container: QWidget | None = None

        # Janela do Chrome usada pelo próprio whatsapp-web.js no modo visual.
        # Ela usa o MESMO perfil LocalAuth da automação.
        self._login_hwnd: int | None = None
        self._login_native_window: QWindow | None = None
        self._login_window_container: QWidget | None = None

        self._launch_pid: int = 0
        self._launch_mode = "normal"
        self._started_once = False
        self._stopping = False
        self._poll_count = 0

        self._window_timer = QTimer(self)
        self._window_timer.setInterval(250)
        self._window_timer.timeout.connect(
            self._poll_window
        )

        self.root.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.root.setSpacing(10)

        self._build_ui()
        self._refresh_availability()

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------

    def _build_ui(self) -> None:
        top = QFrame()
        top.setObjectName(
            "sheetStandaloneHeader"
        )

        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(
            14,
            10,
            14,
            10,
        )
        top_l.setSpacing(8)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)

        title = QLabel(
            "Automação de Planilhas"
        )
        title.setObjectName(
            "sheetStandaloneTitle"
        )

        subtitle = QLabel(
            "Executando o AutomacaoPlanilhas "
            "Windows Portable v1.0.4 original."
        )
        subtitle.setObjectName(
            "sheetStandaloneMuted"
        )

        text_box.addWidget(title)
        text_box.addWidget(subtitle)

        top_l.addLayout(
            text_box,
            1,
        )

        self.status_chip = QLabel(
            "Preparando..."
        )
        self.status_chip.setObjectName(
            "sheetStandaloneStatus"
        )
        top_l.addWidget(
            self.status_chip
        )

        self.start_btn = QPushButton(
            "▶  INICIAR"
        )
        self.start_btn.setObjectName(
            "sheetStandalonePrimary"
        )
        self.start_btn.clicked.connect(
            self.start_tool
        )
        top_l.addWidget(
            self.start_btn
        )

        self.reembed_btn = QPushButton(
            "▣  INTEGRAR"
        )
        self.reembed_btn.setObjectName(
            "sheetStandaloneSecondary"
        )
        self.reembed_btn.clicked.connect(
            self._force_reembed
        )
        top_l.addWidget(
            self.reembed_btn
        )

        self.external_btn = QPushButton(
            "↗  ABRIR FORA"
        )
        self.external_btn.setObjectName(
            "sheetStandaloneSecondary"
        )
        self.external_btn.clicked.connect(
            self.open_external
        )
        top_l.addWidget(
            self.external_btn
        )

        self.restart_btn = QPushButton(
            "↻  REINICIAR"
        )
        self.restart_btn.setObjectName(
            "sheetStandaloneSecondary"
        )
        self.restart_btn.clicked.connect(
            self.restart_tool
        )
        top_l.addWidget(
            self.restart_btn
        )

        self.stop_btn = QPushButton(
            "■  ENCERRAR"
        )
        self.stop_btn.setObjectName(
            "sheetStandaloneDanger"
        )
        self.stop_btn.clicked.connect(
            self.stop_tool
        )
        top_l.addWidget(
            self.stop_btn
        )

        self.root.addWidget(top)

        self.tabs = QTabWidget()
        self.tabs.setObjectName(
            "sheetStandaloneTabs"
        )

        # ------------------------------------------------------
        # Aba 1: aplicativo da Automação
        # ------------------------------------------------------
        automation_tab = QWidget()
        automation_layout = QVBoxLayout(
            automation_tab
        )
        automation_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        automation_layout.setSpacing(8)

        self.browser_host = QFrame()
        self.browser_host.setObjectName(
            "sheetStandaloneHost"
        )
        self.browser_host.setMinimumSize(
            320,
            220,
        )
        self.browser_host.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow,
            True,
        )

        host_l = QVBoxLayout(
            self.browser_host
        )
        host_l.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        host_l.setSpacing(0)
        self.browser_host_layout = host_l

        self.placeholder = QLabel(
            "Automação de Planilhas v1.0.4\n\n"
            "Aguardando o aplicativo iniciar..."
        )
        self.placeholder.setObjectName(
            "sheetStandalonePlaceholder"
        )
        self.placeholder.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.placeholder.setWordWrap(
            True
        )
        host_l.addWidget(
            self.placeholder,
            1,
        )

        automation_layout.addWidget(
            self.browser_host,
            1,
        )

        note = QLabel(
            "A janela da Automação fica integrada ao Central. "
            "A área interna agora possui rolagem para permitir acessar "
            "configurações, log e controles mesmo em telas menores."
        )
        note.setObjectName(
            "sheetStandaloneMuted"
        )
        note.setWordWrap(True)
        automation_layout.addWidget(note)

        self.tabs.addTab(
            automation_tab,
            "Automação",
        )

        # ------------------------------------------------------
        # Aba 2: Chrome/WhatsApp visual usando o MESMO perfil da automação
        # ------------------------------------------------------
        login_tab = QWidget()
        login_layout = QVBoxLayout(
            login_tab
        )
        login_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        login_layout.setSpacing(8)

        login_actions = QFrame()
        login_actions.setObjectName(
            "sheetStandaloneHeader"
        )
        login_actions_l = QHBoxLayout(
            login_actions
        )
        login_actions_l.setContentsMargins(
            12,
            9,
            12,
            9,
        )
        login_actions_l.setSpacing(8)

        login_text = QVBoxLayout()
        login_title = QLabel(
            "Login do WhatsApp"
        )
        login_title.setObjectName(
            "sheetStandaloneTitle"
        )
        login_hint = QLabel(
            "Abre o Chrome portátil do próprio motor usando o mesmo "
            "perfil LocalAuth. Faça o login/QR aqui e depois coloque "
            "a automação em segundo plano."
        )
        login_hint.setObjectName(
            "sheetStandaloneMuted"
        )
        login_hint.setWordWrap(True)
        login_text.addWidget(login_title)
        login_text.addWidget(login_hint)
        login_actions_l.addLayout(
            login_text,
            1,
        )

        self.login_btn = QPushButton(
            "🔐  ABRIR LOGIN"
        )
        self.login_btn.setObjectName(
            "sheetStandalonePrimary"
        )
        self.login_btn.clicked.connect(
            self.start_whatsapp_login
        )
        login_actions_l.addWidget(
            self.login_btn
        )

        self.background_btn = QPushButton(
            "☁  USAR EM SEGUNDO PLANO"
        )
        self.background_btn.setObjectName(
            "sheetStandaloneSecondary"
        )
        self.background_btn.clicked.connect(
            self.start_background_automation
        )
        login_actions_l.addWidget(
            self.background_btn
        )

        self.login_external_btn = QPushButton(
            "↗  ABRIR LOGIN FORA"
        )
        self.login_external_btn.setObjectName(
            "sheetStandaloneSecondary"
        )
        self.login_external_btn.clicked.connect(
            self.open_login_external
        )
        login_actions_l.addWidget(
            self.login_external_btn
        )

        login_layout.addWidget(
            login_actions
        )

        self.login_host = QFrame()
        self.login_host.setObjectName(
            "sheetStandaloneHost"
        )
        self.login_host.setMinimumSize(
            320,
            220,
        )
        self.login_host.setAttribute(
            Qt.WidgetAttribute.WA_NativeWindow,
            True,
        )

        self.login_host_layout = QVBoxLayout(
            self.login_host
        )
        self.login_host_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.login_host_layout.setSpacing(0)

        self.login_placeholder = QLabel(
            "Login visual ainda não iniciado.\n\n"
            "Clique em ABRIR LOGIN para iniciar o Chrome portátil "
            "do WhatsApp dentro desta aba."
        )
        self.login_placeholder.setObjectName(
            "sheetStandalonePlaceholder"
        )
        self.login_placeholder.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.login_placeholder.setWordWrap(
            True
        )
        self.login_host_layout.addWidget(
            self.login_placeholder,
            1,
        )

        login_layout.addWidget(
            self.login_host,
            1,
        )

        login_note = QLabel(
            "Importante: este não é um Chrome separado. É a janela visual "
            "do mesmo whatsapp-web.js, com o mesmo perfil e o mesmo Proxy Geral. "
            "Por isso o login feito aqui é reutilizado pela automação."
        )
        login_note.setObjectName(
            "sheetStandaloneMuted"
        )
        login_note.setWordWrap(True)
        login_layout.addWidget(login_note)

        self.tabs.addTab(
            login_tab,
            "WhatsApp Login",
        )

        self.tabs.currentChanged.connect(
            self._tab_changed
        )

        self.root.addWidget(
            self.tabs,
            1,
        )

        self.setStyleSheet(
            """
            QFrame#sheetStandaloneHeader {
                background:#FFFFFF;
                border:1px solid #C9DDF2;
                border-radius:10px;
            }

            QLabel#sheetStandaloneTitle {
                color:#08245F;
                font-size:18px;
                font-weight:900;
            }

            QLabel#sheetStandaloneMuted {
                color:#6079A5;
                font-size:10px;
                font-weight:600;
            }

            QLabel#sheetStandaloneStatus {
                background:#EAF9F2;
                color:#087D59;
                border:1px solid #BFE8D4;
                border-radius:8px;
                padding:8px 11px;
                font-size:10px;
                font-weight:900;
            }

            QPushButton#sheetStandalonePrimary {
                background:#0A7DF8;
                color:#FFFFFF;
                border:0;
                border-radius:8px;
                padding:9px 14px;
                font-weight:900;
            }

            QPushButton#sheetStandaloneSecondary {
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
                border-radius:8px;
                padding:9px 12px;
                font-weight:800;
            }

            QPushButton#sheetStandaloneDanger {
                background:#FFF0F3;
                color:#D92F55;
                border:1px solid #FFB4C4;
                border-radius:8px;
                padding:9px 12px;
                font-weight:900;
            }

            QFrame#sheetStandaloneHost {
                background:#F4F8FD;
                border:1px solid #C9DDF2;
                border-radius:10px;
            }

            QTabWidget#sheetStandaloneTabs::pane {
                border:1px solid #C9DDF2;
                border-radius:10px;
                background:#F7FAFE;
                top:-1px;
            }

            QTabWidget#sheetStandaloneTabs QTabBar::tab {
                background:#EDF4FC;
                color:#365B86;
                border:1px solid #C9DDF2;
                padding:8px 16px;
                min-width:120px;
                font-weight:800;
            }

            QTabWidget#sheetStandaloneTabs QTabBar::tab:selected {
                background:#FFFFFF;
                color:#0A7DF8;
            }

            QLabel#sheetStandalonePlaceholder {
                background:#F4F8FD;
                color:#6079A5;
                font-size:14px;
                font-weight:800;
                padding:30px;
            }

            QPushButton:disabled {
                color:#9DABBC;
                background:#F1F4F8;
            }
            """
        )

    # ----------------------------------------------------------
    # Ciclo do aplicativo standalone
    # ----------------------------------------------------------

    def _refresh_availability(self) -> None:
        available = (
            self.exe_path.is_file()
            and self.config_path.is_file()
        )

        self.start_btn.setEnabled(
            available
        )

        if available:
            if self._embedded_hwnd:
                self.status_chip.setText(
                    "Integrado ao Central"
                )
            elif self._is_tool_window_alive():
                self.status_chip.setText(
                    "Executando"
                )
            else:
                self.status_chip.setText(
                    "Pronto"
                )
        else:
            self.status_chip.setText(
                "Arquivos ausentes"
            )
            self.placeholder.setText(
                "O AutomacaoPlanilhas v1.0.4 não foi encontrado.\n\n"
                "Esperado em:\n"
                f"{self.exe_path}"
            )

    def _build_process_environment(
        self,
        launch_mode: str = "normal",
    ) -> QProcessEnvironment | None:
        """Monta o ambiente do EXE com o Proxy Geral do Central.

        A senha permanece protegida no DPAPI do Central e só é lida no
        instante em que o processo é iniciado. Ela não é escrita no
        config.json da Automação de Planilhas.
        """
        env = QProcessEnvironment.systemEnvironment()

        # Impede que variáveis antigas do Windows/terminal sobreponham a
        # configuração explícita do Central.
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            env.remove(key)

        try:
            prefs = SharedPreferences(
                self.app_root
                / "data"
                / "prefs"
                / "monitor_prefs.properties"
            )

            settings = ProxySettings(
                prefs,
                data_dir=(
                    self.app_root
                    / "data"
                ),
            )

            config = settings.load()

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Proxy Geral",
                "Não foi possível ler a configuração de proxy do Central.\n\n"
                f"{exc}",
            )
            return None

        env.insert(
            "CENTRAL_PROXY_ENABLED",
            "1" if config.enabled else "0",
        )
        env.insert(
            "CENTRAL_PROXY_HOST",
            config.host or "",
        )
        env.insert(
            "CENTRAL_PROXY_PORT",
            str(config.port or 0),
        )
        env.insert(
            "CENTRAL_PROXY_USERNAME",
            config.username or "",
        )
        env.insert(
            "CENTRAL_PROXY_PASSWORD",
            config.password or "",
        )

        if config.enabled:
            if not config.ready:
                QMessageBox.warning(
                    self,
                    "Proxy Geral",
                    "O Proxy Geral está ativado, mas usuário/senha "
                    "não estão completos.\n\n"
                    "Abra Configurações do Central, corrija o proxy "
                    "e tente iniciar a Automação de Planilhas novamente.",
                )
                return None

            self.status_chip.setText(
                "Proxy geral do Central"
            )
        else:
            self.status_chip.setText(
                "Conexão direta"
            )

        env.remove(
            "CENTRAL_AUTOSTART_LOGIN"
        )
        env.remove(
            "CENTRAL_AUTOSTART_MOTOR"
        )

        if launch_mode == "login":
            env.insert(
                "CENTRAL_AUTOSTART_LOGIN",
                "1",
            )
        elif launch_mode == "background":
            env.insert(
                "CENTRAL_AUTOSTART_MOTOR",
                "1",
            )

        return env

    def _ensure_tool_config(self) -> bool:
        """Garante que o EXE receba um config.json válido e completo.

        O portable usa o config.json ao lado do EXE. Se o arquivo tiver sido
        apagado, esvaziado ou criado por uma versão antiga, a tela do Electron
        fica com Apps Script em branco. Corrigimos somente os campos ausentes,
        preservando qualquer personalização já salva pelo usuário.
        """
        config: dict = {}
        changed = False

        try:
            if self.config_path.is_file():
                raw = self.config_path.read_text(
                    encoding="utf-8-sig",
                ).strip()

                if raw:
                    loaded = json.loads(raw)

                    if isinstance(loaded, dict):
                        config = loaded
                    else:
                        changed = True
                else:
                    changed = True
            else:
                changed = True

        except Exception:
            # Guarda o arquivo inválido para não perder informação.
            try:
                if self.config_path.is_file():
                    backup = self.config_path.with_suffix(
                        ".json.invalid.bak"
                    )
                    shutil.copy2(
                        self.config_path,
                        backup,
                    )
            except Exception:
                pass

            config = {}
            changed = True

        apps_url = str(
            config.get("appsScriptUrl")
            or ""
        ).strip()

        if not apps_url:
            config["appsScriptUrl"] = (
                self.DEFAULT_APPS_SCRIPT_URL
            )
            changed = True

        groups = config.get("grupos")

        if (
            not isinstance(groups, list)
            or not [
                str(item).strip()
                for item in groups
                if str(item).strip()
            ]
        ):
            config["grupos"] = list(
                self.DEFAULT_GROUPS
            )
            changed = True

        if "diagnosticoGrupos" not in config:
            config["diagnosticoGrupos"] = False
            changed = True

        if "chromePath" not in config:
            config["chromePath"] = ""
            changed = True

        # O proxy desta integração é gerenciado pelo Central/DPAPI.
        # Mantemos o bloco somente por compatibilidade visual do standalone.
        if not isinstance(
            config.get("proxy"),
            dict,
        ):
            config["proxy"] = {
                "ativo": False,
                "host": "proxy-7dn.mb",
                "porta": 6060,
                "usuario": "",
                "senha": "",
            }
            changed = True

        try:
            self.config_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if changed:
                self.config_path.write_text(
                    json.dumps(
                        config,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            return True

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Automação de Planilhas",
                "Não foi possível preparar o config.json da Automação.\n\n"
                f"{exc}",
            )
            return False

    def _destroy_window_container(
        self,
    ) -> None:
        container = self._window_container
        self._window_container = None
        self._native_window = None

        if container is not None:
            try:
                self.browser_host_layout.removeWidget(
                    container
                )
            except Exception:
                pass

            try:
                container.hide()
                container.setParent(None)
                container.deleteLater()
            except Exception:
                pass

    def _destroy_login_window_container(
        self,
    ) -> None:
        container = self._login_window_container
        self._login_window_container = None
        self._login_native_window = None

        if container is not None:
            try:
                self.login_host_layout.removeWidget(
                    container
                )
            except Exception:
                pass

            try:
                container.hide()
                container.setParent(None)
                container.deleteLater()
            except Exception:
                pass

    def _focus_login_window(
        self,
    ) -> None:
        hwnd = self._login_hwnd

        if (
            os.name != "nt"
            or not hwnd
            or not self._is_window(hwnd)
        ):
            return

        try:
            ctypes.windll.user32.SetFocus(
                ctypes.c_void_p(hwnd)
            )
        except Exception:
            pass

    def _tab_changed(
        self,
        index: int,
    ) -> None:
        if index == 1:
            QTimer.singleShot(
                50,
                self._focus_login_window,
            )
        else:
            QTimer.singleShot(
                50,
                self._focus_embedded_window,
            )

    def _focus_embedded_window(
        self,
    ) -> None:
        """Transfere foco de teclado para o Electron incorporado."""
        hwnd = self._embedded_hwnd

        if (
            os.name != "nt"
            or not hwnd
            or not self._is_window(hwnd)
        ):
            return

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            user32.EnableWindow(
                ctypes.c_void_p(hwnd),
                True,
            )

            foreign_thread = (
                user32.GetWindowThreadProcessId(
                    ctypes.c_void_p(hwnd),
                    None,
                )
            )
            current_thread = (
                kernel32.GetCurrentThreadId()
            )

            attached = False

            if (
                foreign_thread
                and current_thread
                and foreign_thread
                != current_thread
            ):
                attached = bool(
                    user32.AttachThreadInput(
                        current_thread,
                        foreign_thread,
                        True,
                    )
                )

            try:
                user32.SetFocus(
                    ctypes.c_void_p(hwnd)
                )
            finally:
                if attached:
                    user32.AttachThreadInput(
                        current_thread,
                        foreign_thread,
                        False,
                    )

        except Exception:
            pass

    def start_tool(self) -> None:
        self._launch_tool(
            "normal"
        )

    def _launch_tool(
        self,
        launch_mode: str,
    ) -> None:
        if not self.exe_path.is_file():
            QMessageBox.warning(
                self,
                "Automação de Planilhas",
                "O executável standalone não foi encontrado:\n"
                f"{self.exe_path}",
            )
            return

        if not self._ensure_tool_config():
            return

        # Se já estiver no modo normal e a janela existir, apenas reincorpora.
        existing = self._find_tool_window()

        if (
            existing
            and launch_mode == "normal"
        ):
            self._embed_window(
                existing
            )
            return

        if (
            self.process is not None
            and self.process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self._start_window_poll()
            return

        self._launch_mode = launch_mode
        self._stopping = False
        self._poll_count = 0

        self.placeholder.show()

        if launch_mode == "login":
            self.placeholder.setText(
                "Iniciando Automação e Chrome visual do WhatsApp..."
            )
            self.login_placeholder.show()
            self.login_placeholder.setText(
                "Inicializando Chrome portátil com o mesmo perfil da automação...\n\n"
                "Aguarde o WhatsApp Web aparecer nesta aba."
            )
            self.tabs.setCurrentIndex(
                1
            )
        elif launch_mode == "background":
            self.placeholder.setText(
                "Iniciando Automação em segundo plano..."
            )
            self.tabs.setCurrentIndex(
                0
            )
        else:
            self.placeholder.setText(
                "Iniciando AutomacaoPlanilhas v1.0.4...\n\n"
                "A primeira abertura pode levar alguns segundos."
            )

        process_env = (
            self._build_process_environment(
                launch_mode
            )
        )

        if process_env is None:
            return

        process = QProcess(self)
        process.setWorkingDirectory(
            str(self.tool_dir)
        )
        process.setProcessEnvironment(
            process_env
        )

        process.started.connect(
            self._process_started
        )
        process.errorOccurred.connect(
            self._process_error
        )
        process.finished.connect(
            self._process_finished
        )

        self.process = process

        process.start(
            str(self.exe_path),
            [],
        )

        self.status_chip.setText(
            "Iniciando..."
        )

    def start_whatsapp_login(
        self,
    ) -> None:
        # A janela visual e o motor precisam usar o mesmo profile Chromium.
        # Portanto encerramos qualquer instância anterior antes de abrir login.
        self.stop_tool()

        self.login_placeholder.show()
        self.login_placeholder.setText(
            "Preparando sessão visual do WhatsApp..."
        )

        QTimer.singleShot(
            1300,
            lambda: self._launch_tool(
                "login"
            ),
        )

    def start_background_automation(
        self,
    ) -> None:
        # Depois do login, reinicia headless usando exatamente o mesmo
        # .wwebjs_auth_v2 criado pelo modo visual.
        self.stop_tool()

        QTimer.singleShot(
            1300,
            lambda: self._launch_tool(
                "background"
            ),
        )

    def _process_started(self) -> None:
        if self.process is not None:
            self._launch_pid = int(
                self.process.processId()
                or 0
            )

        self.status_chip.setText(
            "Localizando janela..."
        )
        self._start_window_poll()

    def _process_error(
        self,
        _error,
    ) -> None:
        if self._stopping:
            return

        message = (
            self.process.errorString()
            if self.process is not None
            else "Erro desconhecido."
        )

        self.status_chip.setText(
            "Erro ao iniciar"
        )
        self.placeholder.setText(
            "Não foi possível iniciar a Automação de Planilhas.\n\n"
            + message
        )

    def _process_finished(
        self,
        _exit_code: int,
        _exit_status,
    ) -> None:
        # O Electron Portable/NSIS pode encerrar o processo lançador e manter
        # o processo real aberto. Por isso não consideramos o aplicativo
        # encerrado até confirmar que a janela desapareceu.
        self.process = None

        if self._stopping:
            return

        QTimer.singleShot(
            500,
            self._poll_window,
        )

    def _start_window_poll(self) -> None:
        if not self._window_timer.isActive():
            self._window_timer.start()

        self._poll_window()

    def _poll_window(self) -> None:
        tool_ready = False

        hwnd = self._embedded_hwnd

        if hwnd and self._is_window(hwnd):
            self._resize_embedded()
            tool_ready = True
        else:
            if hwnd:
                self._embedded_hwnd = None
                self._embedded_original_style = None

            candidate = self._find_tool_window()

            if candidate:
                self._embed_window(
                    candidate
                )
                tool_ready = True

        login_ready = False

        if (
            self._login_hwnd
            and self._is_window(
                self._login_hwnd
            )
        ):
            login_ready = True
        else:
            if self._login_hwnd:
                self._destroy_login_window_container()
                self._login_hwnd = None

            login_candidate = (
                self._find_login_window()
            )

            if login_candidate:
                self._embed_login_window(
                    login_candidate
                )
                login_ready = True

        if (
            tool_ready
            and (
                self._launch_mode != "login"
                or login_ready
            )
        ):
            self._window_timer.stop()
            return

        self._poll_count += 1

        if self._poll_count > 360:
            self._window_timer.stop()

            if not tool_ready:
                self.status_chip.setText(
                    "Janela não localizada"
                )
                self.placeholder.setText(
                    "O aplicativo foi iniciado, mas a janela não pôde ser "
                    "incorporada automaticamente.\n\n"
                    "Clique em “ABRIR FORA” para usá-lo como janela normal."
                )

            if (
                self._launch_mode == "login"
                and not login_ready
            ):
                self.login_placeholder.setText(
                    "O motor iniciou, mas a janela visual do Chrome não foi "
                    "localizada.\n\n"
                    "Use ABRIR LOGIN novamente ou ABRIR LOGIN FORA."
                )

    @staticmethod
    def _is_window(hwnd: int) -> bool:
        if os.name != "nt" or not hwnd:
            return False

        try:
            return bool(
                ctypes.windll.user32.IsWindow(
                    ctypes.c_void_p(hwnd)
                )
            )
        except Exception:
            return False

    @staticmethod
    def _normalize(text: str) -> str:
        return (
            str(text)
            .lower()
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("õ", "o")
            .replace("ú", "u")
        )

    def _process_image_path(
        self,
        pid: int,
    ) -> str:
        if os.name != "nt" or pid <= 0:
            return ""

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        try:
            kernel32 = ctypes.windll.kernel32

            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                int(pid),
            )

            if not handle:
                return ""

            try:
                size = ctypes.c_ulong(32768)
                buffer = ctypes.create_unicode_buffer(
                    size.value
                )

                if kernel32.QueryFullProcessImageNameW(
                    handle,
                    0,
                    buffer,
                    ctypes.byref(size),
                ):
                    return buffer.value
            finally:
                kernel32.CloseHandle(handle)

        except Exception:
            pass

        return ""

    def _find_tool_window(self) -> int | None:
        if os.name != "nt":
            return None

        user32 = ctypes.windll.user32
        candidates: list[
            tuple[int, int, int]
        ] = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        @EnumWindowsProc
        def callback(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True

                title_len = user32.GetWindowTextLengthW(
                    hwnd
                )

                title_buffer = ctypes.create_unicode_buffer(
                    max(2, title_len + 1)
                )

                user32.GetWindowTextW(
                    hwnd,
                    title_buffer,
                    len(title_buffer),
                )

                title = title_buffer.value.strip()

                class_buffer = ctypes.create_unicode_buffer(
                    256
                )

                user32.GetClassNameW(
                    hwnd,
                    class_buffer,
                    256,
                )

                class_name = (
                    class_buffer.value
                )

                pid = ctypes.c_ulong(0)

                user32.GetWindowThreadProcessId(
                    hwnd,
                    ctypes.byref(pid),
                )

                pid_value = int(
                    pid.value
                )

                image = (
                    self._process_image_path(
                        pid_value
                    )
                )

                normalized_title = (
                    self._normalize(title)
                )
                normalized_image = (
                    self._normalize(image)
                )

                # Nunca captura a própria janela do Central.
                if (
                    "central inteligente de midia"
                    in normalized_title
                ):
                    return True

                score = 0

                if (
                    "automacao planilhas"
                    in normalized_title
                ):
                    score += 220

                if (
                    "automacao"
                    in normalized_title
                    and "planilha"
                    in normalized_title
                ):
                    score += 180

                if (
                    "whatsapp"
                    in normalized_title
                    and "planilha"
                    in normalized_title
                ):
                    score += 150

                if (
                    "automacao"
                    in normalized_image
                    and "planilha"
                    in normalized_image
                ):
                    score += 200

                if class_name.startswith(
                    "Chrome_WidgetWin"
                ):
                    score += 25

                if (
                    self._launch_pid
                    and pid_value
                    == self._launch_pid
                ):
                    score += 80

                if score < 150:
                    return True

                rect = ctypes.wintypes.RECT()

                area = 0

                if user32.GetWindowRect(
                    hwnd,
                    ctypes.byref(rect),
                ):
                    area = max(
                        0,
                        (
                            rect.right
                            - rect.left
                        )
                        * (
                            rect.bottom
                            - rect.top
                        ),
                    )

                candidates.append(
                    (
                        score,
                        area,
                        int(hwnd),
                    )
                )

            except Exception:
                pass

            return True

        # wintypes nem sempre vem anexado automaticamente ao ctypes.
        from ctypes import wintypes
        ctypes.wintypes = wintypes

        user32.EnumWindows(
            callback,
            0,
        )

        if not candidates:
            return None

        candidates.sort(
            reverse=True
        )

        return candidates[0][2]

    def _find_login_window(
        self,
    ) -> int | None:
        if os.name != "nt":
            return None

        user32 = ctypes.windll.user32
        candidates: list[
            tuple[int, int]
        ] = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        @EnumWindowsProc
        def callback(
            hwnd,
            _lparam,
        ):
            try:
                if not user32.IsWindowVisible(
                    hwnd
                ):
                    return True

                title_len = (
                    user32.GetWindowTextLengthW(
                        hwnd
                    )
                )

                title_buffer = (
                    ctypes.create_unicode_buffer(
                        max(
                            2,
                            title_len + 1,
                        )
                    )
                )

                user32.GetWindowTextW(
                    hwnd,
                    title_buffer,
                    len(title_buffer),
                )

                title = (
                    title_buffer.value
                    .strip()
                )

                normalized = (
                    self._normalize(
                        title
                    )
                )

                # O engine V31 força este marcador no título da página
                # do Chromium visual a cada segundo.
                if (
                    "central whatsapp login"
                    not in normalized
                ):
                    return True

                from ctypes import wintypes
                rect = wintypes.RECT()
                area = 0

                if user32.GetWindowRect(
                    hwnd,
                    ctypes.byref(
                        rect
                    ),
                ):
                    area = max(
                        0,
                        (
                            rect.right
                            - rect.left
                        )
                        * (
                            rect.bottom
                            - rect.top
                        ),
                    )

                candidates.append(
                    (
                        area,
                        int(hwnd),
                    )
                )

            except Exception:
                pass

            return True

        user32.EnumWindows(
            callback,
            0,
        )

        if not candidates:
            return None

        candidates.sort(
            reverse=True
        )

        return candidates[0][1]

    def _embed_login_window(
        self,
        hwnd: int,
    ) -> None:
        if os.name != "nt":
            return

        try:
            self._destroy_login_window_container()

            native_window = QWindow.fromWinId(
                int(hwnd)
            )

            if native_window is None:
                raise RuntimeError(
                    "Qt não conseguiu incorporar a janela do Chrome."
                )

            container = QWidget.createWindowContainer(
                native_window,
                self.login_host,
            )

            container.setObjectName(
                "sheetStandaloneNativeContainer"
            )
            container.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus
            )
            container.setMinimumSize(
                1,
                1,
            )

            self.login_host_layout.addWidget(
                container,
                1,
            )

            self._login_native_window = (
                native_window
            )
            self._login_window_container = (
                container
            )
            self._login_hwnd = (
                int(hwnd)
            )

            self.login_placeholder.hide()
            container.show()
            container.raise_()

            self.status_chip.setText(
                "WhatsApp visual"
            )

            self.tabs.setCurrentIndex(
                1
            )

            QTimer.singleShot(
                80,
                self._focus_login_window,
            )

        except Exception as exc:
            self._destroy_login_window_container()
            self._login_hwnd = None
            self.login_placeholder.show()
            self.login_placeholder.setText(
                "Não foi possível incorporar o Chrome do WhatsApp.\n\n"
                f"{exc}"
            )

    def open_login_external(
        self,
    ) -> None:
        hwnd = (
            self._login_hwnd
            or self._find_login_window()
        )

        if not hwnd:
            self.start_whatsapp_login()
            return

        self._destroy_login_window_container()
        self._login_hwnd = None

        try:
            SW_RESTORE = 9
            user32 = ctypes.windll.user32
            user32.SetParent(
                ctypes.c_void_p(hwnd),
                ctypes.c_void_p(0),
            )
            user32.ShowWindow(
                ctypes.c_void_p(hwnd),
                SW_RESTORE,
            )
            user32.SetForegroundWindow(
                ctypes.c_void_p(hwnd)
            )
        except Exception:
            pass

    def _embed_window(
        self,
        hwnd: int,
    ) -> None:
        if os.name != "nt":
            return

        try:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16

            get_style = getattr(
                user32,
                "GetWindowLongPtrW",
                user32.GetWindowLongW,
            )

            self._embedded_original_style = int(
                get_style(
                    ctypes.c_void_p(hwnd),
                    GWL_STYLE,
                )
            )

            self._destroy_window_container()

            native_window = QWindow.fromWinId(
                int(hwnd)
            )

            if native_window is None:
                raise RuntimeError(
                    "Qt não conseguiu criar o wrapper da janela Electron."
                )

            container = QWidget.createWindowContainer(
                native_window,
                self.browser_host,
            )

            container.setObjectName(
                "sheetStandaloneNativeContainer"
            )
            container.setFocusPolicy(
                Qt.FocusPolicy.StrongFocus
            )
            container.setMinimumSize(
                1,
                1,
            )

            self.browser_host_layout.addWidget(
                container,
                1,
            )

            self._native_window = (
                native_window
            )
            self._window_container = (
                container
            )
            self._embedded_hwnd = (
                int(hwnd)
            )

            self.placeholder.hide()
            container.show()
            container.raise_()

            self.status_chip.setText(
                "Integrado ao Central"
            )

            # O createWindowContainer gerencia tamanho, posição e foco do
            # HWND estrangeiro. Ainda fazemos uma ativação inicial para o
            # primeiro clique/teclado funcionar imediatamente.
            QTimer.singleShot(
                50,
                self._focus_embedded_window,
            )
            QTimer.singleShot(
                250,
                self._focus_embedded_window,
            )

        except Exception as exc:
            self._destroy_window_container()
            self._embedded_hwnd = None

            self.status_chip.setText(
                "Executando fora"
            )

            self.placeholder.show()
            self.placeholder.setText(
                "A Automação de Planilhas está funcionando, mas o Windows "
                "não permitiu incorporar a janela.\n\n"
                f"Detalhe: {exc}\n\n"
                "Use “ABRIR FORA”."
            )

    def _native_host_size(self) -> tuple[int, int]:
        return (
            max(
                1,
                int(self.browser_host.width()),
            ),
            max(
                1,
                int(self.browser_host.height()),
            ),
        )

    def _resize_embedded(self) -> None:
        # QWidget.createWindowContainer já acompanha automaticamente o layout.
        # Mantemos apenas a ativação/foco quando a página é redimensionada.
        if (
            self._window_container is not None
            and self._embedded_hwnd
        ):
            try:
                self._window_container.updateGeometry()
                self._window_container.show()
            except Exception:
                pass

    def _detach_window(
        self,
        *,
        show: bool,
    ) -> None:
        hwnd = (
            self._embedded_hwnd
            or self._find_tool_window()
        )

        if (
            os.name != "nt"
            or not hwnd
            or not self._is_window(hwnd)
        ):
            self._destroy_window_container()
            self._embedded_hwnd = None
            return

        # Remove primeiro o container Qt; depois devolve o HWND ao desktop.
        self._destroy_window_container()

        try:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16

            set_style = getattr(
                user32,
                "SetWindowLongPtrW",
                user32.SetWindowLongW,
            )

            user32.SetParent(
                ctypes.c_void_p(hwnd),
                ctypes.c_void_p(0),
            )

            if self._embedded_original_style is not None:
                set_style(
                    ctypes.c_void_p(hwnd),
                    GWL_STYLE,
                    int(
                        self._embedded_original_style
                    ),
                )

            if show:
                SW_RESTORE = 9
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020

                user32.SetWindowPos(
                    ctypes.c_void_p(hwnd),
                    ctypes.c_void_p(0),
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE
                    | SWP_NOSIZE
                    | SWP_NOZORDER
                    | SWP_FRAMECHANGED,
                )

                user32.ShowWindow(
                    ctypes.c_void_p(hwnd),
                    SW_RESTORE,
                )

                user32.SetForegroundWindow(
                    ctypes.c_void_p(hwnd)
                )

        except Exception:
            pass

        self._embedded_hwnd = None

        if show:
            self.placeholder.show()
            self.placeholder.setText(
                "A Automação de Planilhas está aberta em uma janela própria.\n\n"
                "Clique em “INTEGRAR” para trazê-la novamente para esta aba."
            )
            self.status_chip.setText(
                "Executando fora"
            )

    def _force_reembed(self) -> None:
        hwnd = (
            self._embedded_hwnd
            or self._find_tool_window()
        )

        if hwnd:
            self._embed_window(hwnd)
            return

        self.start_tool()

    def open_external(self) -> None:
        hwnd = (
            self._embedded_hwnd
            or self._find_tool_window()
        )

        if not hwnd:
            self.start_tool()

            QTimer.singleShot(
                1500,
                self.open_external,
            )
            return

        self._detach_window(
            show=True
        )

    def restart_tool(self) -> None:
        self.stop_tool()

        QTimer.singleShot(
            1300,
            self.start_tool,
        )

    def stop_tool(self) -> None:
        self._stopping = True
        self._window_timer.stop()

        hwnd = (
            self._embedded_hwnd
            or self._find_tool_window()
        )

        self._destroy_window_container()

        login_hwnd = (
            self._login_hwnd
            or self._find_login_window()
        )

        self._destroy_login_window_container()

        if (
            os.name == "nt"
            and login_hwnd
            and self._is_window(
                login_hwnd
            )
        ):
            try:
                WM_CLOSE = 0x0010
                ctypes.windll.user32.PostMessageW(
                    ctypes.c_void_p(
                        login_hwnd
                    ),
                    WM_CLOSE,
                    0,
                    0,
                )
            except Exception:
                pass

        self._login_hwnd = None

        if (
            os.name == "nt"
            and hwnd
            and self._is_window(hwnd)
        ):
            try:
                WM_CLOSE = 0x0010

                ctypes.windll.user32.PostMessageW(
                    ctypes.c_void_p(hwnd),
                    WM_CLOSE,
                    0,
                    0,
                )
            except Exception:
                pass

        self._embedded_hwnd = None
        self._embedded_original_style = None

        process = self.process

        if (
            process is not None
            and process.state()
            != QProcess.ProcessState.NotRunning
        ):
            process.terminate()

            if not process.waitForFinished(
                1800
            ):
                process.kill()
                process.waitForFinished(
                    1200
                )

        self.process = None
        self._launch_pid = 0

        self.placeholder.show()
        self.placeholder.setText(
            "Automação de Planilhas v1.0.4 encerrada.\n\n"
            "Clique em INICIAR para abrir novamente."
        )

        self.status_chip.setText(
            "Parado"
        )

        self._stopping = False

    def _is_tool_window_alive(self) -> bool:
        return bool(
            self._find_tool_window()
        )

    # ----------------------------------------------------------
    # BasePage / MainWindow integration
    # ----------------------------------------------------------

    def showEvent(
        self,
        event,
    ) -> None:
        super().showEvent(event)

        self._refresh_availability()

        # Abre automaticamente na primeira vez que a aba Planilhas é exibida.
        if (
            not self._started_once
            and self.exe_path.is_file()
        ):
            self._started_once = True

            QTimer.singleShot(
                150,
                self.start_tool,
            )

        elif self._embedded_hwnd:
            QTimer.singleShot(
                0,
                self._resize_embedded,
            )
            QTimer.singleShot(
                80,
                self._focus_embedded_window,
            )

    def resizeEvent(
        self,
        event,
    ) -> None:
        super().resizeEvent(event)

        QTimer.singleShot(
            0,
            self._resize_embedded,
        )

        if self._login_window_container is not None:
            try:
                self._login_window_container.updateGeometry()
            except Exception:
                pass

    def refresh(
        self,
        _state=None,
    ) -> None:
        if self._embedded_hwnd:
            self._resize_embedded()

    def shutdown(
        self,
    ) -> bool:
        try:
            self.stop_tool()
            return True
        except Exception:
            return False
