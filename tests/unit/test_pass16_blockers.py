from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from monitor_noticias.extractor import login_helper
from monitor_noticias.ui import extractor_page as extractor_ui
from monitor_noticias.ui.extractor_page import ExtractorPage


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_bundled_globoplay_helper_materializes_resource_to_runtime(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(login_helper, "MIN_HELPER_SIZE", 8)
    source = tmp_path / "resources" / "globoplay-login-helper" / "GloboplayLoginHelper.exe"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"0123456789abcdef")

    target = login_helper.resolve_bundled_helper(tmp_path)

    assert target == tmp_path / "data" / "extractor" / "runtime" / "GloboplayLoginHelper.exe"
    assert target.read_bytes() == source.read_bytes()


def test_bundled_globoplay_helper_does_not_fallback_to_external_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(login_helper, "MIN_HELPER_SIZE", 1)
    external = tmp_path / "data" / "extractor" / "runtime" / "GloboplayLoginHelper.exe"
    external.parent.mkdir(parents=True)
    external.write_bytes(b"already-there")

    try:
        login_helper.resolve_bundled_helper(tmp_path)
    except FileNotFoundError as exc:
        assert "/globoplay-login-helper/GloboplayLoginHelper.exe ausente" in str(exc)
    else:
        raise AssertionError("O runtime não pode substituir o resource empacotado da baseline Kotlin.")


def test_extractor_page_login_runs_resolved_helper_and_saves_returned_cookies(tmp_path: Path, monkeypatch):
    app = _app()
    page = ExtractorPage(tmp_path)
    helper = tmp_path / "data" / "extractor" / "runtime" / "GloboplayLoginHelper.exe"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_bytes(b"fixture-helper")
    monkeypatch.setattr(extractor_ui, "resolve_bundled_helper", lambda _root: helper)

    calls: list[tuple[list[str], str]] = []

    class FakeProcess:
        def __init__(self, argv, cwd=None, **_kwargs):
            self.argv = [str(x) for x in argv]
            self.cwd = str(cwd)
            output = Path(self.argv[self.argv.index("--output") + 1])
            output.write_text(
                "# Netscape HTTP Cookie File\n.globo.com\tTRUE\t/\tTRUE\t1999999999\tGLBID\tfixture-value\n",
                encoding="utf-8",
            )
            calls.append((self.argv, self.cwd))

        def wait(self):
            return 0

        def poll(self):
            return 0

    saved: list[str] = []
    monkeypatch.setattr(extractor_ui.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(page.session_store, "save_netscape_cookies", lambda text: saved.append(text))

    page.open_globoplay_login()
    assert page._login_waiter is not None
    page._login_waiter.join(timeout=2)
    for _ in range(5):
        app.processEvents()

    assert len(calls) == 1
    argv, cwd = calls[0]
    assert argv[0] == str(helper)
    assert argv[1] == "--output"
    assert "--profile-dir" in argv
    assert cwd == str(tmp_path)
    assert saved and "GLBID\tfixture-value" in saved[0]
    assert "Sessão Globoplay salva com segurança (1 cookies)." in page.settings_status.text()
