from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.extractor_page import ExtractorPage
from monitor_noticias.ui.video_editor_page import VideoEditorPage


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_video_editor_page_shutdown_current_embedded_editor(tmp_path: Path):
    _app()
    page = VideoEditorPage(tmp_path)

    # O editor deixou de abrir uma janela externa; agora vive incorporado
    # diretamente na página. O contrato de encerramento é shutdown().
    assert hasattr(page, "editor")
    assert page.shutdown() is True


def test_extractor_shutdown_terminates_tracked_helper_process(tmp_path: Path):
    _app()
    page = ExtractorPage(tmp_path)

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        ]
    )
    page._login_process = process

    try:
        assert page.shutdown(timeout_ms=3000) is True
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
