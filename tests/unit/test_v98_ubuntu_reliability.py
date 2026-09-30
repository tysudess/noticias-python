from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "monitor_noticias"


def test_proxy_password_does_not_probe_exists_before_load():
    text = (SRC / "networking" / "proxy.py").read_text(encoding="utf-8")
    start = text.index("    def _load_password(self) -> str:")
    end = text.index("\n    def load(self) -> ProxyConfig:", start)
    body = text[start:end]

    assert "self.secret_store.load()" in body
    assert "self.secret_store.exists()" not in body


def test_linux_auth_patch_has_no_warmup_request():
    text = (
        SRC / "auth" / "linux_auth_transport_patch.py"
    ).read_text(encoding="utf-8")

    assert "session.get(" not in text
    assert "warm_auth" not in text
    assert "ConnectTimeout" in text
    assert "ReadTimeout" in text


def test_covers_linux_teardown_does_not_create_replacement_page():
    text = (
        SRC / "ui" / "covers_linux_stability_patch.py"
    ).read_text(encoding="utf-8")

    assert "view.setPage(QWebEnginePage" not in text
    assert "view.deleteLater()" in text
    assert "profile.setParent(app)" in text
    assert "requests_verify(config)" in text
    assert "faulthandler.enable" in text


def test_recorder_has_real_x11_preflight_and_video_only_audio_fallback():
    text = (
        SRC / "ui" / "screen_recorder_linux_patch.py"
    ).read_text(encoding="utf-8")

    assert '"-f",\n        "x11grab"' in text
    assert '"-frames:v",\n        "1"' in text
    assert "continuando sem áudio" in text
    assert "_probe_x11_capture" in text


def test_portable_diagnostic_checks_x11grab():
    text = (
        ROOT / "portable" / "linux" / "TESTAR-PORTABLE.sh"
    ).read_text(encoding="utf-8")

    assert "-devices" in text
    assert "x11grab" in text
    assert "-frames:v 1" in text
