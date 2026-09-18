from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from monitor_noticias.ui.url_tools import resolve_article_url


class NewsExtractorPage(QWidget):
    back_requested = Signal()

    GWL_STYLE = -16
    GWL_EXSTYLE = -20

    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_POPUP = 0x80000000
    WS_CHILD = 0x40000000

    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080

    SW_HIDE = 0
    SW_SHOW = 5
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self.exe = (
            self.app_root
            / "tools"
            / "news_extractor"
            / "ExtratorMateriasPortable-V1.25.19.exe"
        )

        self.process = None
        self._hwnd = None
        self._pending_url = ""
        self._poll_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.host = QFrame()
        self.host.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.host.setStyleSheet("background:#08111f;border:0;")
        root.addWidget(self.host, 1)

        self.message = QLabel("Carregando Extrator de Notícias...", self.host)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setStyleSheet(
            "color:#91A2B9;background:#08111F;font-size:14px;"
        )
        self.message.setGeometry(self.host.rect())

        self._poll = QTimer(self)
        self._poll.setInterval(80)
        self._poll.timeout.connect(self._try_embed)

        self._fit_timer = QTimer(self)
        self._fit_timer.setInterval(300)
        self._fit_timer.timeout.connect(self._resize_embedded)

    def refresh(self, _state=None) -> None:
        if self.process is None:
            self.launch()

    def open_url(self, url: str) -> None:
        raw = str(url or "").strip()

        # Mesma resolução usada por Abrir matéria / Copiar link.
        direct = resolve_article_url(raw)
        self._pending_url = str(direct or raw).strip()

        self.restart()

    def launch(self) -> None:
        if self.process is not None and self.process.poll() is None:
            if self._hwnd:
                self._resize_embedded()
            return

        if not self.exe.is_file():
            self._show_message(
                "Extrator de Notícias não encontrado no portable:\n"
                f"{self.exe}"
            )
            return

        env = os.environ.copy()
        env["MONITOR_EMBEDDED"] = "1"

        if self._pending_url:
            env["MONITOR_NEWS_URL"] = self._pending_url
        else:
            env.pop("MONITOR_NEWS_URL", None)

        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            self.process = subprocess.Popen(
                [str(self.exe)],
                env=env,
                creationflags=creationflags,
            )

            self._hwnd = None
            self._poll_count = 0
            self._show_message("Carregando Extrator de Notícias...")
            self._poll.start()

        except Exception as exc:
            self._show_message(f"Falha ao iniciar Extrator de Notícias:\n{exc}")

    def restart(self) -> None:
        self._stop_process()
        QTimer.singleShot(180, self.launch)

    def _show_message(self, text: str) -> None:
        self.message.setText(text)
        self.message.setGeometry(self.host.rect())
        self.message.raise_()
        self.message.show()

    def _stop_process(self) -> None:
        self._poll.stop()
        self._fit_timer.stop()
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

    def _find_window(self):
        if sys.platform != "win32":
            return None

        user32 = ctypes.windll.user32
        matches = []
        target_pid = self.process.pid if self.process else 0

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )

        def callback(hwnd, _lparam):
            if not user32.IsWindow(hwnd):
                return True

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            length = user32.GetWindowTextLengthW(hwnd)
            title = ""

            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()

            by_pid = bool(target_pid and pid.value == target_pid)
            by_title = (
                "extrator de matérias" in title
                or "extrator de materias" in title
                or "extrator de notícias" in title
                or "extrator de noticias" in title
            )

            if by_pid or by_title:
                matches.append(int(hwnd))
                return False

            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)
        return matches[0] if matches else None

    def _try_embed(self) -> None:
        self._poll_count += 1
        hwnd = self._find_window()

        if not hwnd:
            if self._poll_count >= 400:
                self._poll.stop()
                self._show_message(
                    "O Extrator iniciou, mas não foi possível incorporá-lo ao Monitor."
                )
            return

        try:
            user32 = ctypes.windll.user32
            host_hwnd = int(self.host.winId())

            user32.ShowWindow(hwnd, self.SW_HIDE)
            user32.SetParent(hwnd, host_hwnd)

            style = user32.GetWindowLongW(hwnd, self.GWL_STYLE)
            style &= ~self.WS_CAPTION
            style &= ~self.WS_THICKFRAME
            style &= ~self.WS_POPUP
            style |= self.WS_CHILD
            user32.SetWindowLongW(hwnd, self.GWL_STYLE, style)

            exstyle = user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
            exstyle &= ~self.WS_EX_APPWINDOW
            exstyle |= self.WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, exstyle)

            self._hwnd = hwnd
            self._resize_embedded()
            user32.ShowWindow(hwnd, self.SW_SHOW)

            self._poll.stop()
            self.message.hide()
            self._fit_timer.start()

        except Exception as exc:
            self._poll.stop()
            self._show_message(
                "O Extrator abriu, mas não foi possível incorporá-lo ao Monitor:\n"
                f"{exc}"
            )

    def _resize_embedded(self) -> None:
        if not self._hwnd or sys.platform != "win32":
            return

        try:
            user32 = ctypes.windll.user32
            rect = ctypes.wintypes.RECT()
            host_hwnd = int(self.host.winId())

            if user32.GetClientRect(host_hwnd, ctypes.byref(rect)):
                width = max(1, int(rect.right - rect.left))
                height = max(1, int(rect.bottom - rect.top))
            else:
                width = max(1, self.host.width())
                height = max(1, self.host.height())

            user32.SetWindowPos(
                self._hwnd,
                0,
                0,
                0,
                width,
                height,
                self.SWP_NOZORDER
                | self.SWP_NOACTIVATE
                | self.SWP_FRAMECHANGED
                | self.SWP_SHOWWINDOW,
            )
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.message.setGeometry(self.host.rect())
        if self._hwnd:
            QTimer.singleShot(0, self._resize_embedded)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.process is None:
            QTimer.singleShot(0, self.launch)
        elif self._hwnd:
            QTimer.singleShot(0, self._resize_embedded)

    def shutdown(self) -> bool:
        self._stop_process()
        return True
