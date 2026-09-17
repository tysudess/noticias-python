from __future__ import annotations

import time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeNewsRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.database import NewsDb
from monitor_noticias.models import News
from monitor_noticias.repositories import NewsRepository


class MutableGoogle:
    def __init__(self, link: str, title: str) -> None:
        self.link = link
        self.title = title

    def collect(self, query):
        published_at = int(time.time() * 1000) - 1000
        return [
            News(
                title=self.title,
                source="Fonte Teste",
                date=published_at,
                link=self.link,
                snippet="Operação da Marinha",
                capturedAt=published_at,
            )
        ]


class FakeLatest:
    pass


class NoopVideoRunner:
    def search_videos(self, **kwargs):
        raise AssertionError("vídeo não deve executar neste teste")


def wait_idle(automation: AutomationService, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while automation.state.newsBusy and time.time() < deadline:
        time.sleep(0.01)
    assert not automation.state.newsBusy


def test_port005_new_duplicate_and_next_new_notification_contract(tmp_path: Path):
    paths = AppPaths(tmp_path)
    paths.ensure_runtime_dirs()
    prefs = SharedPreferences(paths.data / "prefs" / "monitor_prefs.properties")
    news_db = NewsDb(paths.news_db)
    for term in news_db.listTerms():
        news_db.removeTerm(term)
    news_db.addTerm("MARINHA")

    first_link = "https://example.test/portable-noticia-smoke-1"
    first_title = "Marinha realiza exercício naval smoke 1"
    second_link = "https://example.test/portable-noticia-smoke-2"
    second_title = "Marinha realiza exercício naval smoke 2"
    google = MutableGoogle(first_link, first_title)
    repository = NewsRepository(
        news_db,
        google=google,
        latest=FakeLatest(),
        national_sources=(),
    )
    runner = RuntimeNewsRunner(repository, prefs, ())
    events: list[tuple[str, str]] = []
    automation = AutomationService(
        AutomationSettings(prefs),
        runner,
        NoopVideoRunner(),
        notify=lambda title, body: events.append((title, body)),
    )
    try:
        assert automation.search_news() is True
        wait_idle(automation)
        assert len(events) == 1
        assert first_link in automation.state.newNewsLinks

        assert automation.search_news() is True
        wait_idle(automation)
        assert len(events) == 1
        assert not automation.state.newNewsLinks

        google.link = second_link
        google.title = second_title
        assert automation.search_news() is True
        wait_idle(automation)
        assert len(events) == 2
        assert second_link in automation.state.newNewsLinks

        stored_links = {item.link for item in news_db.listNews(10)}
        assert {first_link, second_link} <= stored_links
    finally:
        automation.close()
        news_db.close()
