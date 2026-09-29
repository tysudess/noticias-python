from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_auth_client_reuses_http_session():
    source = _read(
        "src/monitor_noticias/auth/client.py"
    )

    assert "self._session = requests.Session()" in source
    assert "self._request_lock = threading.RLock()" in source
    assert '"Connection": "keep-alive"' in source
    assert "def request_timeout" in source
    assert "AUTH timing:" in source


def test_auth_keeps_remote_validation():
    source = _read(
        "src/monitor_noticias/auth/client.py"
    )

    assert '"action": "validate"' in source
    assert '"token": token' in source
    assert '"device_id": self.device.device_id' in source


def test_extractor_uses_persistent_worker():
    page = _read(
        "src/monitor_noticias/ui/news_extractor_page.py"
    )
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert 'env.insert("MONITOR_PERSISTENT", "1")' in page
    assert "process.stdin" in node
    assert "executarPersistente" in node
    assert "CENTRAL_RESULT " in node


def test_extractor_preserves_proxy_general_environment():
    page = _read(
        "src/monitor_noticias/ui/news_extractor_page.py"
    )
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    for key in (
        "CENTRAL_PROXY_ENABLED",
        "CENTRAL_PROXY_HOST",
        "CENTRAL_PROXY_PORT",
        "CENTRAL_PROXY_USERNAME",
        "CENTRAL_PROXY_PASSWORD",
    ):
        assert key in page
        assert key in node


def test_extractor_has_quality_guard_and_safe_result_write():
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert "resultadoSuspeito" in node
    assert "pontuarMateria" in node
    assert "segundaLeituraUsada" in node
    assert "fs.renameSync" in node
    assert "erroNaoDeveRepetir" in node
