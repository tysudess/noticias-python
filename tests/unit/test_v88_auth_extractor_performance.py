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


def test_extractor_uses_reliable_one_shot_process():
    speed = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
    )
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert '"MONITOR_NEWS_URL"' in speed
    assert '"MONITOR_RESULT_FILE"' in speed
    assert '"MONITOR_PERSISTENT"' in speed
    assert "env.remove(" in speed

    assert "process.stdin" not in node
    assert "executarPersistente" not in node
    assert "app.exit(0)" in node


def test_extractor_preserves_proxy_general_environment():
    speed = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
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
        assert key in speed
        assert key in node


def test_extractor_has_hard_timeout_and_atomic_result_write():
    speed = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
    )
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert "DEFAULT_UI_TIMEOUT_MS" in speed
    assert "CENTRAL_NEWS_HARD_TIMEOUT_MS" in speed
    assert "Tempo limite da extração" in speed

    assert "HARD_TIMEOUT_MS" in node
    assert "Promise.race" in node
    assert "fs.renameSync" in node
    assert "motor.extrairMateria(URL)" in node
