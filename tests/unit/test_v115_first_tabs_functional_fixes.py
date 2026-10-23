from __future__ import annotations

from datetime import datetime

from monitor_noticias.ui.first_tabs_functional_patch import (
    _news_count_period, _news_list_period, _video_count_all,
    _video_count_captured_period, classify_execution,
    local_day_start_ms, normalize_news_window,
)


class FakeQuery:
    def __init__(self, row): self.row = row
    def fetchone(self): return (self.row,)


class FakeRaw:
    def __init__(self, result=0): self.result = result; self.last_sql = ""; self.last_args = ()
    def execute(self, sql, args=()):
        self.last_sql = sql; self.last_args = tuple(args); return FakeQuery(self.result)


class FakeDb:
    def __init__(self, result=0):
        from threading import RLock
        self._lock = RLock()
        self._db = type("Wrapper", (), {"raw": FakeRaw(result)})()


def test_news_window_defaults_to_last_24_hours_and_normalizes_order():
    now = 1_800_000_000_000
    assert normalize_news_window(None, None, now_ms=now) == (now - 86_400_000, now)
    assert normalize_news_window(300, 100, now_ms=now) == (100, 300)
    assert normalize_news_window(100, 300, now_ms=now) == (100, 300)
    assert normalize_news_window(100, None, now_ms=now) == (now - 86_400_000, now)


def test_local_day_starts_at_midnight_local_time():
    current = datetime(2026, 10, 23, 14, 35, 42, 987000)
    expected = int(datetime(2026, 10, 23, 0, 0).timestamp() * 1000)
    assert local_day_start_ms(current) == expected


def test_execution_classification_does_not_treat_idle_as_success():
    assert classify_execution("Pronto") == "idle"
    assert classify_execution("") == "idle"
    assert classify_execution("Buscando notícias...", busy=True) == "running"


def test_execution_classification_identifies_failure_cancellation_and_partial():
    assert classify_execution("Falha na busca de notícias: timeout", duration_ms=120) == "failure"
    assert classify_execution("Busca de vídeos interrompida pelo usuário", duration_ms=120) == "cancelled"
    assert classify_execution("✓ 4 notícias • 2 falhas", duration_ms=120) == "partial"
    assert classify_execution("✓ 8 relevantes", duration_ms=120) == "completed"


def test_execution_classification_uses_progress_errors_and_unstable_sources():
    progress = type("Progress", (), {"errors": 2, "startedAt": 1, "finishedAt": 2, "completed": 4, "total": 4})()
    assert classify_execution("Pronto", progress, duration_ms=10) == "partial"
    assert classify_execution("✓ 8 relevantes • 0 fontes instáveis", duration_ms=10, unstable_sources=("Portal X",)) == "partial"


def test_news_period_query_uses_inclusive_database_window():
    db = FakeDb()
    called = {}
    db._queryNews = lambda where, args, limit: called.update(where=where, args=args, limit=limit) or ["row"]
    assert _news_list_period(db, 100, 300, 200) == ["row"]
    assert called == {"where": "date>=? AND date<=?", "args": (100, 300), "limit": 200}


def test_count_helpers_use_sql_counts_not_materializing_entire_lists():
    news = FakeDb(result=12)
    video = FakeDb(result=41)
    assert _news_count_period(news, 100, 200) == 12
    assert news._db.raw.last_sql == "SELECT COUNT(*) FROM news WHERE date>=? AND date<=?"
    assert news._db.raw.last_args == (100, 200)
    assert _video_count_all(video) == 41
    assert video._db.raw.last_sql == "SELECT COUNT(*) FROM videos"
    assert _video_count_captured_period(video, 10, 20) == 41
    assert video._db.raw.last_sql == "SELECT COUNT(*) FROM videos WHERE captured_at>=? AND captured_at<=?"
    assert video._db.raw.last_args == (10, 20)


def test_composition_installs_patch_and_preserves_existing_integrations():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    source = (root / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    assert "install_first_tabs_functional_patch()" in source
    for integration in ("install_video_defense_term_patch", "install_video_preview_layout_patch",
                        "install_video_timeline_side_controls_patch", "install_admin_user_management_patch"):
        assert integration in source


def test_progress_signature_tracks_found_new_and_error_counts():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    source = (root / "src/monitor_noticias/ui/first_tabs_functional_patch.py").read_text(encoding="utf-8")
    for field in ("found", "newCount", "errors", "finishedAt"):
        assert f'"{field}"' in source
