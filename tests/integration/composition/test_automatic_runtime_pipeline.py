from __future__ import annotations

from datetime import datetime
import time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeNewsRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.database import NewsDb
from monitor_noticias.models import News
from monitor_noticias.repositories import NewsRepository


class FakeClock:
    def __init__(self, now):
        self.value = now

    def now_ms(self):
        return self.value

    def local_datetime(self):
        return datetime.fromtimestamp(self.value / 1000)


class FakeGoogle:
    def __init__(self, published_at):
        self.published_at = published_at

    def collect(self, query):
        return [
            News(
                title="Marinha em operação",
                source="Fonte",
                date=self.published_at,
                link="https://example.test/auto",
                snippet="Marinha",
                capturedAt=self.published_at,
            )
        ]


class FakeLatest:
    pass


class NoVideo:
    def search_videos(self, **kwargs):
        raise AssertionError


def test_automatic_tick_uses_real_runtime_runner_repository_and_database(tmp_path: Path):
    paths = AppPaths(tmp_path)
    paths.ensure_runtime_dirs()
    prefs = SharedPreferences(paths.data / "prefs" / "monitor_prefs.properties")
    db = NewsDb(paths.news_db)
    for term in db.listTerms():
        db.removeTerm(term)
    db.addTerm("MARINHA")
    prefs.update(
        desktop_automatic_monitoring=True,
        desktop_news_automatic=True,
        desktop_demand_automatic=False,
        desktop_video_automatic=False,
        desktop_auto_news_at=0,
    )

    now = int(time.time() * 1000)
    repository = NewsRepository(
        db,
        google=FakeGoogle(now),
        latest=FakeLatest(),
        national_sources=(),
    )
    runner = RuntimeNewsRunner(repository, prefs, ())
    service = AutomationService(
        AutomationSettings(prefs),
        runner,
        NoVideo(),
        clock=FakeClock(now),
    )

    service.tick()
    deadline = time.time() + 5
    while service.state.newsBusy and time.time() < deadline:
        time.sleep(0.01)

    assert not service.state.newsBusy
    assert db.listNews(10)[0].link == "https://example.test/auto"
    assert service.settings.last_news_auto_at == now
    service.close()
    db.close()
