from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v91_does_not_reuse_electron_over_stdin():
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert "readline" not in node
    assert "process.stdin" not in node
    assert "executarPersistente" not in node


def test_v91_launches_each_url_through_environment():
    patch = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
    )

    assert 'env.insert(\n            "MONITOR_NEWS_URL"' in patch
    assert 'env.insert(\n            "MONITOR_RESULT_FILE"' in patch
    assert 'env.remove(\n                "MONITOR_PERSISTENT"' in patch


def test_v91_has_two_timeout_layers():
    patch = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
    )
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert "DEFAULT_UI_TIMEOUT_MS = 50_000" in patch
    assert '"CENTRAL_NEWS_HARD_TIMEOUT_MS": "38000"' in patch
    assert "HARD_TIMEOUT_MS" in node
    assert "Promise.race" in node


def test_v91_never_repeats_the_whole_article_automatically():
    node = _read(
        "tools/news_extractor/monitor-main.js"
    )

    assert node.count("motor.extrairMateria(URL)") == 1
    assert "segundaLeituraUsada" not in node


def test_v91_drains_child_stdout_to_avoid_pipe_deadlock():
    patch = _read(
        "src/monitor_noticias/ui/news_extractor_speed_patch.py"
    )

    assert "readyReadStandardOutput.connect" in patch
    assert "readAllStandardOutput" in patch
