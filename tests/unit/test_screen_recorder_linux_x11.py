from PySide6.QtCore import QRect

from monitor_noticias.ui.screen_recorder_linux_patch import (
    _screen_local_rect,
)


def test_x11_global_area_is_converted_to_screen_local_coordinates():
    screen = QRect(1920, 0, 1920, 1080)
    capture = QRect(2040, 80, 1280, 720)

    assert _screen_local_rect(screen, capture) == QRect(
        120,
        80,
        1280,
        720,
    )


def test_area_is_clipped_to_selected_monitor():
    screen = QRect(0, 0, 1920, 1080)
    capture = QRect(-100, -50, 400, 300)

    assert _screen_local_rect(screen, capture) == QRect(
        0,
        0,
        300,
        250,
    )
