from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.extractor_page import ExtractorPage
from monitor_noticias.ui.video_editor_page import VideoEditorPage


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_video_editor_page_shutdown_stops_and_closes_tracked_windows(tmp_path: Path):
    _app()
    page = VideoEditorPage(tmp_path)
    page.open_editor()
    assert page._windows
    window = page._windows[0]
    window.show()
    assert window.isVisible()

    assert page.shutdown() is True
    assert not window.isVisible()


def test_extractor_shutdown_terminates_tracked_helper_process(tmp_path: Path):
    _app()
    page = ExtractorPage(tmp_path)
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    page._login_process = process

    try:
        assert page.shutdown(timeout_ms=3000) is True
        deadline = time.time() + 3
        while process.poll() is None and time.time() < deadline:
            time.sleep(0.02)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
