from __future__ import annotations

import ctypes
import os

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QCursor

from monitor_noticias.ui.spreadsheet_automation_page import (
    SpreadsheetAutomationPage,
)


_PATCHED = False


def _is_window(hwnd: int) -> bool:
    if os.name != "nt" or not hwnd:
        return False

    try:
        return bool(
            ctypes.windll.user32.IsWindow(
                ctypes.c_void_p(int(hwnd))
            )
        )
    except Exception:
        return False


def _window_class(hwnd: int) -> str:
    if os.name != "nt" or not hwnd:
        return ""

    try:
        buffer = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(
            ctypes.c_void_p(int(hwnd)),
            buffer,
            256,
        )
        return buffer.value or ""
    except Exception:
        return ""


def _find_chromium_keyboard_target(
    root_hwnd: int,
) -> int:
    """Encontra o child HWND que recebe WM_KEYDOWN/WM_CHAR no Chromium."""

    if (
        os.name != "nt"
        or not root_hwnd
        or not _is_window(root_hwnd)
    ):
        return int(root_hwnd or 0)

    user32 = ctypes.windll.user32
    candidates: list[
        tuple[int, int]
    ] = []

    enum_proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p,
    )

    @enum_proc_type
    def callback(
        hwnd,
        _lparam,
    ):
        try:
            class_name = (
                _window_class(
                    int(hwnd)
                )
            )
            lowered = (
                class_name.lower()
            )

            score = 0

            # Principal destino de teclado do Chromium/Electron.
            if (
                "chrome_renderwidgethosthwnd"
                in lowered
            ):
                score = 1000

            # Fallbacks para outras versões do Chromium.
            elif lowered.startswith(
                "chrome_widgetwin"
            ):
                score = 600

            elif "chrome" in lowered:
                score = 250

            if score:
                candidates.append(
                    (
                        score,
                        int(hwnd),
                    )
                )

        except Exception:
            pass

        return True

    try:
        user32.EnumChildWindows(
            ctypes.c_void_p(
                int(root_hwnd)
            ),
            callback,
            0,
        )
    except Exception:
        return int(root_hwnd)

    if not candidates:
        return int(root_hwnd)

    candidates.sort(
        reverse=True
    )

    return candidates[0][1]


def _force_keyboard_focus(
    page: SpreadsheetAutomationPage,
) -> None:
    """Entrega foco ao renderer Chromium incorporado."""

    if os.name != "nt":
        return

    hwnd = int(
        getattr(
            page,
            "_embedded_hwnd",
            0,
        )
        or 0
    )

    if not _is_window(hwnd):
        return

    container = getattr(
        page,
        "_window_container",
        None,
    )

    if container is not None:
        try:
            container.setFocus()
            container.activateWindow()
        except Exception:
            pass

    target = (
        _find_chromium_keyboard_target(
            hwnd
        )
        or hwnd
    )

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        current_thread = int(
            kernel32.GetCurrentThreadId()
            or 0
        )

        target_thread = int(
            user32.GetWindowThreadProcessId(
                ctypes.c_void_p(
                    int(target)
                ),
                None,
            )
            or 0
        )

        root_thread = int(
            user32.GetWindowThreadProcessId(
                ctypes.c_void_p(
                    int(hwnd)
                ),
                None,
            )
            or 0
        )

        attached_target = False
        attached_root = False

        try:
            if (
                current_thread
                and target_thread
                and current_thread
                != target_thread
            ):
                attached_target = bool(
                    user32.AttachThreadInput(
                        current_thread,
                        target_thread,
                        True,
                    )
                )

            if (
                current_thread
                and root_thread
                and current_thread
                != root_thread
                and root_thread
                != target_thread
            ):
                attached_root = bool(
                    user32.AttachThreadInput(
                        current_thread,
                        root_thread,
                        True,
                    )
                )

            user32.EnableWindow(
                ctypes.c_void_p(
                    int(hwnd)
                ),
                True,
            )
            user32.EnableWindow(
                ctypes.c_void_p(
                    int(target)
                ),
                True,
            )

            # O código antigo usava SetFocus(hwnd) na janela Electron externa.
            # Inputs HTML recebem teclado pelo RenderWidgetHost filho.
            user32.SetFocus(
                ctypes.c_void_p(
                    int(target)
                )
            )

            WM_SETFOCUS = 0x0007

            user32.PostMessageW(
                ctypes.c_void_p(
                    int(target)
                ),
                WM_SETFOCUS,
                0,
                0,
            )

        finally:
            if attached_root:
                user32.AttachThreadInput(
                    current_thread,
                    root_thread,
                    False,
                )

            if attached_target:
                user32.AttachThreadInput(
                    current_thread,
                    target_thread,
                    False,
                )

    except Exception:
        pass


class _EmbeddedKeyboardFocusHelper(
    QObject
):
    """Repara foco quando o clique ocorre dentro do Electron incorporado.

    O mouse é processado pela janela nativa do Chromium, então o QWidget pai
    não recebe MouseButtonPress de forma confiável. GetAsyncKeyState detecta
    o clique físico e QCursor confirma que ocorreu dentro da área Planilhas.
    """

    def __init__(
        self,
        page: SpreadsheetAutomationPage,
    ) -> None:
        super().__init__(page)

        self.page = page
        self._mouse_down = False

        self.timer = QTimer(self)
        self.timer.setInterval(35)
        self.timer.timeout.connect(
            self._poll
        )
        self.timer.start()

    def _inside_automation(self) -> bool:
        host = getattr(
            self.page,
            "browser_host",
            None,
        )

        if host is None:
            return False

        try:
            global_pos = QCursor.pos()
            local_pos = host.mapFromGlobal(
                global_pos
            )

            return host.rect().contains(
                local_pos
            )

        except Exception:
            return False

    def _poll(self) -> None:
        hwnd = int(
            getattr(
                self.page,
                "_embedded_hwnd",
                0,
            )
            or 0
        )

        if (
            not self.page.isVisible()
            or not _is_window(hwnd)
        ):
            self._mouse_down = False
            return

        try:
            pressed = bool(
                ctypes.windll.user32
                .GetAsyncKeyState(0x01)
                & 0x8000
            )
        except Exception:
            return

        just_pressed = (
            pressed
            and not self._mouse_down
        )

        self._mouse_down = pressed

        if (
            just_pressed
            and self._inside_automation()
        ):
            # Dá tempo para o Chromium selecionar primeiro o input clicado.
            QTimer.singleShot(
                20,
                lambda:
                    _force_keyboard_focus(
                        self.page
                    ),
            )

            QTimer.singleShot(
                90,
                lambda:
                    _force_keyboard_focus(
                        self.page
                    ),
            )


def install_spreadsheet_keyboard_focus_patch() -> None:
    """Corrige teclado/Ctrl+V no Electron incorporado da aba Planilhas."""

    global _PATCHED

    if _PATCHED:
        return

    original_init = (
        SpreadsheetAutomationPage.__init__
    )

    original_focus = (
        SpreadsheetAutomationPage
        ._focus_embedded_window
    )

    def patched_init(
        self,
        *args,
        **kwargs,
    ):
        original_init(
            self,
            *args,
            **kwargs,
        )

        self._central_keyboard_focus_helper = (
            _EmbeddedKeyboardFocusHelper(
                self
            )
        )

    def patched_focus(
        self,
    ) -> None:
        try:
            original_focus(
                self
            )
        except Exception:
            pass

        _force_keyboard_focus(
            self
        )

    SpreadsheetAutomationPage.__init__ = (
        patched_init
    )

    SpreadsheetAutomationPage._focus_embedded_window = (
        patched_focus
    )

    _PATCHED = True
