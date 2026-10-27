from __future__ import annotations

from datetime import datetime, timezone

from monitor_noticias.collectors.news.google_news import _parse_date, parse_google_news_xml
from monitor_noticias.collectors.news.latest import NewsLatestCollector
from monitor_noticias.models import Demand, MediaSource, News
from monitor_noticias.repositories.news_search import perform_news_search


def test_missing_or_invalid_google_pubdate_stays_unknown_not_current_time():
    xml = """<rss><channel><item>
      <title>Marinha em operação</title>
      <link>https://news.google.com/rss/articles/abc123</link>
      <pubDate>not a valid date</pubDate>
      <source url="https://example.com">Fonte A</source>
    </item></channel></rss>"""
    items = parse_google_news_xml(xml, now_ms=1_800_000_000_000)
    assert len(items) == 1
    assert items[0].date == 0
    assert _parse_date("", now_ms=1_800_000_000_000) == 0


def test_timezone_missing_from_pubdate_is_deterministic_utc():
    expected = int(datetime(2026, 9, 12, 18, tzinfo=timezone.utc).timestamp() * 1000)
    assert _parse_date("Sat, 12 Sep 2026 18:00:00", now_ms=123) == expected


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_text(self, url, **kwargs):
        self.calls.append(url)
        value = self.responses.get(url)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise RuntimeError(f"GET inesperado: {url}")
        return value


def test_latest_collector_does_not_invent_publication_time_when_article_has_no_date():
    base = "https://www.cnnbrasil.com.br/ultimas-noticias/"
    article_url = "https://www.cnnbrasil.com.br/politica/2026/09/noticia.html"
    listing = f'''<html><body><article><a href="{article_url}"
      aria-label="Marinha realiza grande operação naval no litoral">
      Marinha realiza grande operação naval no litoral
    </a><p>Detalhes da operação da Marinha.</p></article></body></html>'''
    article = '''<html><head>
      <meta property="og:title" content="Marinha realiza grande operação naval no litoral">
      <meta property="og:description" content="Detalhes da operação da Marinha.">
    </head><body></body></html>'''
    source = MediaSource(
        id="nacional-cnn", name="CNN Brasil", region="Nacional", state="BR",
        stateName="Brasil", group="CNN Brasil", aliases=["CNN"],
    )
    captured = int(datetime(2026, 9, 12, 20, tzinfo=timezone.utc).timestamp() * 1000)
    collector = NewsLatestCollector(FakeHttp({base: listing, article_url: article}))

    outcome = collector.collect(
        source, ["Marinha"], [], 0, captured, captured,
    )
    assert outcome.failed is False
    assert outcome.items == []


class FakeDb:
    def __init__(self):
        self.stored = {}

    def listTerms(self):
        return ["Marinha"]

    def listDemands(self):
        return []

    def listNews(self, _limit=2000):
        return list(self.stored.values())

    def insertNews(self, items):
        new = []
        for item in items:
            if item.link not in self.stored:
                new.append(item)
            self.stored[item.link] = item
        return new


class FakeGoogle:
    def __init__(self, news):
        self.news = news
        self.queries = []

    def collect(self, query):
        self.queries.append(query)
        return list(self.news)


class FakeLatest:
    def collect(self, *_args):
        from monitor_noticias.collectors.news.latest import Outcome
        return Outcome([])


class FakeRepo:
    def __init__(self, now):
        self.db = FakeDb()
        self.google = FakeGoogle([
            News(title="Marinha realiza operação naval", source="Fonte A", date=now - 1000,
                 link="https://fontea.example/noticia/1", snippet="Marinha"),
            News(title="Marinha realiza operação naval", source="Fonte B", date=now - 1000,
                 link="https://fonteb.example/noticia/2", snippet="Marinha"),
        ])
        self.latest = FakeLatest()
        self.national_sources = ()
        self.defaultTerms = ["Marinha"]
        self._now = now

    def now_ms(self):
        return self._now


def test_selected_source_filters_actual_google_results_not_only_ui_selection():
    now = int(datetime(2026, 9, 12, 20, tzinfo=timezone.utc).timestamp() * 1000)
    repo = FakeRepo(now)
    selected = MediaSource(
        id="custom-fonte-a", name="Fonte A", region="Nacional", state="BR",
        stateName="Brasil", group="Jornais", aliases=[],
    )

    result = perform_news_search(
        repo, now - 60 * 60 * 1000, now, (selected,), False, None, None,
    )

    assert len(repo.google.queries) >= 1
    assert all(item.source == "Fonte A" for item in result.items)
    assert [item.link for item in result.items] == ["https://fontea.example/noticia/1"]
