from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import time

import pytest
from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.extractor_page import ExtractorPage


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_download_worker_is_retained_until_qthread_finishes(app, tmp_path: Path, monkeypatch):
    page = ExtractorPage(tmp_path)
    output = tmp_path / "Videos" / "portable-worker-test.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"x" * 2048)

    def fake_download(url, quality, proxy, update):
        assert url == "https://example.test/video.mp4"
        assert proxy == ""
        update(50, "metade")
        return output

    monkeypatch.setattr(page.engine, "download", fake_download)
    page.url.setText("https://example.test/video.mp4")
    page.start_download()

    assert page._download_thread is not None
    assert page._download_worker is not None

    deadline = time.monotonic() + 5.0
    while page._download_thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert page._download_thread is None
    assert page._download_worker is None
    assert page.status.text() == "Download concluído: portable-worker-test.mp4"
    assert page.progress.value() == 100
    assert page.history.count() == 1
    assert page.shutdown()
