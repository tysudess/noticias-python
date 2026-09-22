from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import ProxySettings


class WhatsAppBrowserPage(QWidget):
    """Painel do Chrome dedicado usado pela Automação de Planilhas.

    Fase 1: o Chrome fica em uma janela real controlada pelo Central. Isso evita
    os riscos de reparenting de uma janela Chromium nativa dentro do Qt e,
    ao mesmo tempo, garante que login e automação usem exatamente o mesmo
    processo/perfil via remote debugging.
    """

    state_changed = Signal(str)

    OFF = "Desligado"
    QR = "Aguardando QR Code"
    CONNECTED = "Conectado"
    EXPIRED = "Sessão expirada"
    STARTING = "Iniciando"
    ERROR = "Erro"

    def __init__(
        self,
        app_root: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.app_root = Path(app_root)
        self.data_dir = self.app_root / "data"
        self.profile_dir = (
            self.data_dir
            / "whatsapp_chrome_profile"
        )
        self.status_file = (
            self.data_dir
            / "whatsapp_shared_status.json"
        )
        self.pid_file = (
            self.data_dir
            / "whatsapp_chrome.pid"
        )
        self._automation_page = None
        self._last_state = ""

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(
            self.refresh_status
        )
        self._timer.start()

        self.refresh_status()

    def set_automation_page(
        self,
        page,
    ) -> None:
        self._automation_page = page

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            18,
            14,
            18,
            14,
        )
        root.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("settingsCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        hero_layout.setSpacing(8)

        title = QLabel(
            "WhatsApp Web — sessão compartilhada"
        )
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700;"
        )
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "O Chrome portátil usa um perfil persistente em "
            "data/whatsapp_chrome_profile e remote debugging na porta 9223. "
            "A Automação de Planilhas se conecta a esse mesmo Chrome, sem "
            "criar outra sessão e sem apagar automaticamente o perfil."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("muted")
        hero_layout.addWidget(subtitle)

        root.addWidget(hero)

        status_card = QFrame()
        status_card.setObjectName("settingsCard")
        status_layout = QVBoxLayout(
            status_card
        )
        status_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        status_layout.setSpacing(10)

        status_title = QLabel(
            "Estado da sessão"
        )
        status_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        status_layout.addWidget(status_title)

        row = QHBoxLayout()

        self.state_chip = QLabel(
            self.OFF
        )
        self.state_chip.setObjectName(
            "chipGreen"
        )
        self.state_chip.setMinimumWidth(170)
        row.addWidget(self.state_chip)

        self.proxy_chip = QLabel(
            "Proxy: verificando..."
        )
        self.proxy_chip.setObjectName(
            "chipGreen"
        )
        row.addWidget(self.proxy_chip)

        self.profile_chip = QLabel(
            "Perfil persistente"
        )
        self.profile_chip.setObjectName(
            "chipGreen"
        )
        row.addWidget(self.profile_chip)

        row.addStretch(1)
        status_layout.addLayout(row)

        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setObjectName(
            "muted"
        )
        status_layout.addWidget(
            self.detail
        )

        root.addWidget(status_card)

        controls = QFrame()
        controls.setObjectName(
            "settingsCard"
        )
        controls_layout = QVBoxLayout(
            controls
        )
        controls_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        controls_layout.setSpacing(12)

        controls_title = QLabel(
            "Controles"
        )
        controls_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        controls_layout.addWidget(
            controls_title
        )

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.start_button = QPushButton(
            "▶  INICIAR WHATSAPP"
        )
        self.start_button.setObjectName(
            "settingsPrimary"
        )
        self.start_button.clicked.connect(
            self.start_whatsapp
        )
        buttons.addWidget(
            self.start_button
        )

        self.focus_button = QPushButton(
            "▣  ABRIR / FOCAR"
        )
        self.focus_button.setObjectName(
            "settingsSecondary"
        )
        self.focus_button.clicked.connect(
            self.focus_browser
        )
        buttons.addWidget(
            self.focus_button
        )

        self.reload_button = QPushButton(
            "↻  RECARREGAR"
        )
        self.reload_button.setObjectName(
            "settingsSecondary"
        )
        self.reload_button.clicked.connect(
            self.reload_browser
        )
        buttons.addWidget(
            self.reload_button
        )

        self.disconnect_button = QPushButton(
            "×  DESCONECTAR SESSÃO"
        )
        self.disconnect_button.clicked.connect(
            self.disconnect_session
        )
        buttons.addWidget(
            self.disconnect_button
        )

        buttons.addStretch(1)
        controls_layout.addLayout(
            buttons
        )

        note = QLabel(
            "Nesta primeira implementação o Chrome permanece como uma janela "
            "real controlada pelo Central. Isso é intencional: evita instabilidade "
            "ao incorporar uma janela Chromium externa no QStackedWidget. "
            "A sessão, entretanto, já é única e compartilhada com a Automação."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        controls_layout.addWidget(note)

        root.addWidget(controls)
        root.addStretch(1)

    def _read_pid(self) -> int:
        try:
            return int(
                self.pid_file
                .read_text(
                    encoding="utf-8",
                )
                .strip()
            )
        except Exception:
            return 0

    @staticmethod
    def _pid_alive(
        pid: int,
    ) -> bool:
        if pid <= 0:
            return False

        if sys.platform.startswith("win"):
            try:
                import ctypes

                PROCESS_QUERY_LIMITED_INFORMATION = (
                    0x1000
                )
                handle = (
                    ctypes.windll.kernel32.OpenProcess(
                        PROCESS_QUERY_LIMITED_INFORMATION,
                        False,
                        pid,
                    )
                )
                if handle:
                    ctypes.windll.kernel32.CloseHandle(
                        handle
                    )
                    return True
            except Exception:
                return False

        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False

    def _read_status(self) -> dict:
        try:
            raw = self.status_file.read_text(
                encoding="utf-8"
            )
            data = json.loads(raw)
            return (
                data
                if isinstance(data, dict)
                else {}
            )
        except Exception:
            return {}

    def _proxy_label(self) -> str:
        try:
            prefs = SharedPreferences(
                self.data_dir
                / "prefs"
                / "monitor_prefs.properties"
            )
            config = ProxySettings(
                prefs,
                data_dir=self.data_dir,
            ).load()

            if config.enabled and config.ready:
                return (
                    "Proxy ativo: "
                    f"{config.host}:{config.port}"
                )

            if config.enabled:
                return (
                    "Proxy ativo, mas incompleto"
                )

            return "Proxy desativado"
        except Exception:
            return "Proxy: indisponível"

    def refresh_status(self) -> None:
        pid = self._read_pid()
        alive = self._pid_alive(pid)
        payload = self._read_status()

        state_key = str(
            payload.get("state", "")
        ).strip().lower()

        mapping = {
            "starting": self.STARTING,
            "awaiting_qr": self.QR,
            "authenticated": self.STARTING,
            "connected": self.CONNECTED,
            "session_expired": self.EXPIRED,
            "expired": self.EXPIRED,
            "error": self.ERROR,
            "disconnected": self.OFF,
        }

        state = mapping.get(
            state_key,
            self.QR if alive else self.OFF,
        )

        self.state_chip.setText(
            state
        )
        self.proxy_chip.setText(
            self._proxy_label()
        )

        message = str(
            payload.get("message", "")
        ).strip()

        if state == self.CONNECTED:
            detail = (
                "WhatsApp conectado. A Automação de Planilhas usa este mesmo "
                "Chrome e este mesmo perfil."
            )
        elif state == self.EXPIRED:
            detail = (
                "WhatsApp precisa ser conectado novamente. Abra/focalize o "
                "Chrome, leia o novo QR Code e depois inicie a automação."
            )
        elif state == self.QR:
            detail = (
                "Leia o QR Code diretamente na janela real do WhatsApp Web."
            )
        elif state == self.STARTING:
            detail = (
                "Chrome compartilhado e motor do WhatsApp estão inicializando."
            )
        elif state == self.ERROR:
            detail = (
                message
                or "Falha na inicialização do WhatsApp."
            )
        else:
            detail = (
                "Chrome dedicado desligado. O perfil permanece salvo para a "
                "próxima abertura."
            )

        if message and state not in {
            self.ERROR,
            self.EXPIRED,
        }:
            detail += f"\n\n{message}"

        self.detail.setText(detail)

        if state != self._last_state:
            self._last_state = state
            self.state_changed.emit(
                state
            )

    def start_whatsapp(self) -> None:
        page = self._automation_page

        if page is None:
            QMessageBox.warning(
                self,
                "WhatsApp",
                "A Automação de Planilhas ainda não foi localizada.",
            )
            return

        launcher = getattr(
            page,
            "_launch_tool",
            None,
        )

        if callable(launcher):
            launcher("background")
        else:
            starter = getattr(
                page,
                "start_background_automation",
                None,
            )
            if callable(starter):
                starter()
            else:
                QMessageBox.warning(
                    self,
                    "WhatsApp",
                    "A Automação de Planilhas não possui um método de inicialização compatível.",
                )
                return

        self.state_chip.setText(
            self.STARTING
        )
        self.detail.setText(
            "Inicializando Chrome portátil compartilhado e conectando a Automação..."
        )

        QTimer.singleShot(
            1600,
            self.focus_browser,
        )

    def _find_browser_window(self):
        if not sys.platform.startswith(
            "win"
        ):
            return 0

        pid = self._read_pid()
        if pid <= 0:
            return 0

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            found = []

            EnumWindowsProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM,
            )

            @EnumWindowsProc
            def callback(hwnd, _lparam):
                if not user32.IsWindowVisible(
                    hwnd
                ):
                    return True

                window_pid = (
                    wintypes.DWORD()
                )
                user32.GetWindowThreadProcessId(
                    hwnd,
                    ctypes.byref(
                        window_pid
                    ),
                )

                if int(window_pid.value) == pid:
                    found.append(
                        int(hwnd)
                    )
                    return False

                return True

            user32.EnumWindows(
                callback,
                0,
            )

            return (
                found[0]
                if found
                else 0
            )

        except Exception:
            return 0

    def focus_browser(self) -> None:
        hwnd = self._find_browser_window()

        if not hwnd:
            if not self._pid_alive(
                self._read_pid()
            ):
                self.detail.setText(
                    "O Chrome ainda não está disponível. Clique em INICIAR WHATSAPP "
                    "se a automação estiver parada."
                )
            else:
                self.detail.setText(
                    "O Chrome está em execução, mas a janela ainda não ficou disponível."
                )
            return

        try:
            import ctypes

            user32 = ctypes.windll.user32

            SW_RESTORE = 9
            user32.ShowWindow(
                hwnd,
                SW_RESTORE,
            )
            user32.SetForegroundWindow(
                hwnd
            )
        except Exception as exc:
            self.detail.setText(
                "Não foi possível focar a janela do Chrome.\n\n"
                + str(exc)
            )

    def reload_browser(self) -> None:
        hwnd = self._find_browser_window()

        if not hwnd:
            self.focus_browser()
            return

        try:
            import ctypes

            user32 = ctypes.windll.user32

            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            VK_F5 = 0x74

            user32.SetForegroundWindow(
                hwnd
            )
            user32.PostMessageW(
                hwnd,
                WM_KEYDOWN,
                VK_F5,
                0,
            )
            user32.PostMessageW(
                hwnd,
                WM_KEYUP,
                VK_F5,
                0,
            )

            self.detail.setText(
                "Solicitação de recarregamento enviada ao WhatsApp Web."
            )
        except Exception as exc:
            self.detail.setText(
                "Não foi possível recarregar a janela.\n\n"
                + str(exc)
            )

    def _kill_dedicated_browser(
        self,
    ) -> None:
        pid = self._read_pid()
        if pid <= 0:
            return

        if sys.platform.startswith(
            "win"
        ):
            subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(pid),
                    "/T",
                    "/F",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(
                    getattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                        0,
                    )
                ),
            )
        else:
            try:
                os.kill(pid, 15)
            except Exception:
                pass

    def disconnect_session(
        self,
    ) -> None:
        answer = QMessageBox.question(
            self,
            "Desconectar sessão do WhatsApp",
            "Esta ação encerra o Chrome dedicado e apaga apenas o perfil "
            "data/whatsapp_chrome_profile.\n\n"
            "Na próxima inicialização será necessário ler um novo QR Code.\n\n"
            "Deseja continuar?",
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        if self._automation_page is not None:
            stopper = getattr(
                self._automation_page,
                "stop_tool",
                None,
            )
            if callable(stopper):
                try:
                    stopper()
                except Exception:
                    pass

        self._kill_dedicated_browser()

        for _ in range(12):
            if not self._pid_alive(
                self._read_pid()
            ):
                break
            time.sleep(0.15)

        last_error = None

        for attempt in range(8):
            try:
                if self.profile_dir.exists():
                    shutil.rmtree(
                        self.profile_dir
                    )
                self.profile_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                time.sleep(
                    0.25
                    + attempt * 0.15
                )

        for file_path in (
            self.pid_file,
            self.status_file,
        ):
            try:
                file_path.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

        if last_error is not None:
            QMessageBox.warning(
                self,
                "WhatsApp",
                "O Chrome foi encerrado, mas o perfil não pôde ser apagado completamente.\n\n"
                f"{last_error}",
            )
            return

        self._last_state = ""
        self.refresh_status()
        self.detail.setText(
            "Sessão removida. Clique em INICIAR WHATSAPP para gerar um novo QR Code."
        )

    def on_activated(self) -> None:
        self.refresh_status()

    def shutdown(self) -> None:
        """Fecha somente o Chrome dedicado; o perfil permanece salvo."""
        self._kill_dedicated_browser()
