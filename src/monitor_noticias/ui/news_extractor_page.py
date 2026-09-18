from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


class NewsExtractorPage(QWidget):
    """Hospeda o Extrator de Matérias Electron dentro da aba no Windows."""

    back_requested = Signal()

    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_POPUP = 0x80000000
    WS_CHILD = 0x40000000
    SW_SHOW = 5

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self.exe = (
            self.app_root
            / "tools"
            / "news_extractor"
            / "ExtratorMateriasPortable-V1.25.19.exe"
        )
        self.process: subprocess.Popen | None = None
        self._hwnd: int | None = None
        self._pending_url = ""
        self._poll_count = 0

        self._poll = QTimer(self)
        self._poll.setInterval(120)
        self._poll.timeout.connect(self._try_embed)

        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top = QFrame()
        top.setObjectName("newsExtractorTop")
        row = QHBoxLayout(top)
        row.setContentsMargins(12, 9, 12, 9)
        row.setSpacing(8)

        title = QLabel("Extrator de Notícias")
        title.setStyleSheet(
            "color:#08245F;font-size:18px;font-weight:900;"
        )
        row.addWidget(title)

        self.url = QLineEdit()
        self.url.setPlaceholderText("Cole ou receba o link da matéria...")
        row.addWidget(self.url, 1)

        self.load_button = QPushButton("Abrir / carregar")
        self.load_button.clicked.connect(self.launch)
        row.addWidget(self.load_button)

        restart = QPushButton("Reiniciar extrator")
        restart.clicked.connect(self.restart)
        row.addWidget(restart)

        root.addWidget(top)

        self.status = QLabel(
            "O botão “Extrair matéria” da aba Notícias abrirá esta tela com o link preenchido."
        )
        self.status.setStyleSheet(
            "color:#6079A5;padding:2px 6px;font-size:10px;"
        )
        root.addWidget(self.status)

        self.host = QFrame()
        self.host.setObjectName("newsExtractorHost")
        self.host.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.host.setStyleSheet(
            "QFrame#newsExtractorHost{"
            "background:#08111f;border:1px solid #D5E5F5;border-radius:10px;}"
        )
        root.addWidget(self.host, 1)

    def refresh(self, _state=None) -> None:
        # Não reinicia nem recarrega a ferramenta a cada tick do Monitor.
        pass

    def open_url(self, url: str) -> None:
        self.url.setText(url or "")
        self._pending_url = url or ""

        # Para garantir que o Electron receba a nova URL na inicialização,
        # reinicia somente quando veio um link novo da aba Notícias.
        self.restart()

    def launch(self) -> None:
        self._pending_url = self.url.text().strip()

        if self.process is not None and self.process.poll() is None and self._hwnd:
            self.status.setText(
                "Extrator já está aberto. Use “Reiniciar extrator” para aplicar outro link."
            )
            return

        if not self.exe.is_file():
            self.status.setText(
                f"Extrator não encontrado no portable: {self.exe}"
            )
            return

        args = [str(self.exe)]

        if self._pending_url:
            args.append(f"--url={self._pending_url}")

        try:
            self.process = subprocess.Popen(args)
            self._hwnd = None
            self._poll_count = 0
            self.status.setText("Iniciando Extrator de Notícias...")
            self._poll.start()
        except Exception as exc:
            self.status.setText(f"Falha ao iniciar extrator: {exc}")

    def restart(self) -> None:
        self._stop_process()
        QTimer.singleShot(180, self.launch)

    def _stop_process(self) -> None:
        self._poll.stop()
        self._hwnd = None

        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=3)
                    except Exception:
                        self.process.kill()
            except Exception:
                pass

        self.process = None

    def _find_window(self) -> int | None:
        if sys.platform != "win32":
            return None

        user32 = ctypes.windll.user32
        result: list[int] = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        target_pid = self.process.pid if self.process else 0

        def callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.lower()

            by_pid = target_pid and pid.value == target_pid
            by_title = (
                "extrator de materias" in title
                or "extrator de matérias" in title
                or "extrator de noticias" in title
                or "extrator de notícias" in title
            )

            if by_pid or by_title:
                result.append(int(hwnd))
                return False

            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)
        return result[0] if result else None

    def _try_embed(self) -> None:
        self._poll_count += 1

        hwnd = self._find_window()

        if not hwnd:
            if self._poll_count > 200:
                self._poll.stop()
                self.status.setText(
                    "O extrator iniciou, mas a janela não pôde ser incorporada."
                )
            return

        self._poll.stop()

        try:
            user32 = ctypes.windll.user32
            host_hwnd = int(self.host.winId())

            user32.SetParent(hwnd, host_hwnd)

            style = user32.GetWindowLongW(hwnd, self.GWL_STYLE)
            style &= ~self.WS_CAPTION
            style &= ~self.WS_THICKFRAME
            style &= ~self.WS_POPUP
            style |= self.WS_CHILD

            user32.SetWindowLongW(hwnd, self.GWL_STYLE, style)
            user32.ShowWindow(hwnd, self.SW_SHOW)

            self._hwnd = hwnd
            self._resize_embedded()
            self.status.setText(
                "Extrator de Notícias incorporado ao Monitor."
            )
        except Exception as exc:
            self.status.setText(
                f"Extrator abriu, mas não foi possível incorporar: {exc}"
            )

    def _resize_embedded(self) -> None:
        if not self._hwnd or sys.platform != "win32":
            return

        try:
            ctypes.windll.user32.MoveWindow(
                self._hwnd,
                0,
                0,
                max(1, self.host.width()),
                max(1, self.host.height()),
                True,
            )
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_embedded()

    def shutdown(self) -> bool:
        self._stop_process()
        return True
