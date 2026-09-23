from PySide6.QtCore import QRect

from monitor_noticias.ui.screen_recorder_linux_patch import _display_input


def test_x11_display_input(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0.0")

    assert (
        _display_input(
            QRect(120, 80, 1280, 720)
        )
        == ":0.0+120,80"
    )
