from __future__ import annotations

import ctypes
import os
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QTimer,
    Qt,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        self._launch_pid: int = 0
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

        self.browser_host = QFrame()
        self.browser_host.setObjectName(
            "sheetStandaloneHost"
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

        self.root.addWidget(
            self.browser_host,
            1,
        )

        note = QLabel(
            "Esta aba usa exatamente o executável standalone enviado, "
            "sem o motor Node/WhatsApp desenvolvido anteriormente no Central. "
            "Se a incorporação da janela não funcionar em algum computador, "
            "use “ABRIR FORA”: o aplicativo continua sendo o mesmo."
        )
        note.setObjectName(
            "sheetStandaloneMuted"
        )
        note.setWordWrap(True)
        self.root.addWidget(note)

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

    def start_tool(self) -> None:
        if not self.exe_path.is_file():
            QMessageBox.warning(
                self,
                "Automação de Planilhas",
                "O executável standalone não foi encontrado:\n"
                f"{self.exe_path}",
            )
            return

        # Se já existir uma janela do aplicativo, apenas incorpora novamente.
        existing = self._find_tool_window()

        if existing:
            self._embed_window(existing)
            return

        if (
            self.process is not None
            and self.process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self._start_window_poll()
            return

        self._stopping = False
        self._poll_count = 0

        self.placeholder.show()
        self.placeholder.setText(
            "Iniciando AutomacaoPlanilhas v1.0.4...\n\n"
            "A primeira abertura pode levar alguns segundos."
        )

        process = QProcess(self)
        process.setWorkingDirectory(
            str(self.tool_dir)
        )
        process.setProcessEnvironment(
            QProcessEnvironment.systemEnvironment()
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
        hwnd = self._embedded_hwnd

        if hwnd and self._is_window(hwnd):
            self._resize_embedded()
            return

        if hwnd:
            self._embedded_hwnd = None
            self._embedded_original_style = None

        candidate = self._find_tool_window()

        if candidate:
            self._embed_window(candidate)
            self._window_timer.stop()
            return

        self._poll_count += 1

        if self._poll_count > 240:
            self._window_timer.stop()
            self.status_chip.setText(
                "Janela não localizada"
            )
            self.placeholder.setText(
                "O aplicativo foi iniciado, mas a janela não pôde ser "
                "incorporada automaticamente.\n\n"
                "Clique em “ABRIR FORA” para usá-lo como janela normal."
            )

    # ----------------------------------------------------------
    # Win32: encontra e incorpora o Electron inteiro
    # ----------------------------------------------------------

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

    def _embed_window(
        self,
        hwnd: int,
    ) -> None:
        if os.name != "nt":
            return

        try:
            user32 = ctypes.windll.user32

            GWL_STYLE = -16

            WS_CHILD = 0x40000000
            WS_VISIBLE = 0x10000000
            WS_POPUP = 0x80000000
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_MINIMIZEBOX = 0x00020000
            WS_MAXIMIZEBOX = 0x00010000
            WS_SYSMENU = 0x00080000

            get_style = getattr(
                user32,
                "GetWindowLongPtrW",
                user32.GetWindowLongW,
            )
            set_style = getattr(
                user32,
                "SetWindowLongPtrW",
                user32.SetWindowLongW,
            )

            style = int(
                get_style(
                    ctypes.c_void_p(hwnd),
                    GWL_STYLE,
                )
            )

            self._embedded_original_style = (
                style
            )

            style &= ~(
                WS_POPUP
                | WS_CAPTION
                | WS_THICKFRAME
                | WS_MINIMIZEBOX
                | WS_MAXIMIZEBOX
                | WS_SYSMENU
            )

            style |= (
                WS_CHILD
                | WS_VISIBLE
            )

            set_style(
                ctypes.c_void_p(hwnd),
                GWL_STYLE,
                style,
            )

            host_hwnd = int(
                self.browser_host.winId()
            )

            result = user32.SetParent(
                ctypes.c_void_p(hwnd),
                ctypes.c_void_p(host_hwnd),
            )

            # SetParent pode retornar 0 tanto em falha quanto quando o parent
            # anterior era desktop. Confirmamos pelo parent atual.
            parent_now = user32.GetParent(
                ctypes.c_void_p(hwnd)
            )

            if int(parent_now or 0) != host_hwnd:
                raise RuntimeError(
                    "O Windows não aceitou incorporar a janela."
                )

            self._embedded_hwnd = (
                int(hwnd)
            )

            self.placeholder.hide()
            self.status_chip.setText(
                "Integrado ao Central"
            )

            self._resize_embedded()

        except Exception as exc:
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

    def _resize_embedded(self) -> None:
        hwnd = self._embedded_hwnd

        if (
            os.name != "nt"
            or not hwnd
            or not self._is_window(hwnd)
        ):
            return

        try:
            ctypes.windll.user32.MoveWindow(
                ctypes.c_void_p(hwnd),
                0,
                0,
                max(
                    1,
                    self.browser_host.width()
                ),
                max(
                    1,
                    self.browser_host.height()
                ),
                True,
            )
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
            self._embedded_hwnd = None
            return

        try:
            user32 = ctypes.windll.user32
            GWL_STYLE = -16

            get_style = getattr(
                user32,
                "GetWindowLongPtrW",
                user32.GetWindowLongW,
            )
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

    def resizeEvent(
        self,
        event,
    ) -> None:
        super().resizeEvent(event)

        QTimer.singleShot(
            0,
            self._resize_embedded,
        )

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
