from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from monitor_noticias.collectors.news.latest import NewsLatestCollector, ROUTES
from monitor_noticias.collectors.news.veja_source import (
    VEJA_LATEST_ROUTE,
    VEJA_SOURCE,
    extend_news_catalog,
)
from monitor_noticias.matching import source_matches_strict
from monitor_noticias.ui.catalog import NATIONAL as CATALOG_NATIONAL, NEWS_SOURCES as CATALOG_NEWS_SOURCES

ROOT = Path(__file__).resolve().parents[2]


class FakeHttp:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.calls: list[str] = []

    def get_text(self, url: str, **_kwargs) -> str:
        self.calls.append(url)
        if url not in self.responses:
            raise RuntimeError(f"GET inesperado: {url}")
        return self.responses[url]


def test_veja_is_in_national_and_news_catalogs_with_direct_route():
    national, all_sources = extend_news_catalog(CATALOG_NATIONAL, CATALOG_NEWS_SOURCES)

    assert sum(source.id == "nacional-veja" for source in national) == 1
    assert sum(source.id == "nacional-veja" for source in all_sources) == 1
    assert VEJA_SOURCE in national
    assert VEJA_SOURCE in all_sources
    assert VEJA_SOURCE.group == "Jornais nacionais"
    veja_index = all_sources.index(VEJA_SOURCE)
    first_non_national = next(
        (index for index, source in enumerate(all_sources)
         if source.group != "Jornais nacionais"),
        len(all_sources),
    )
    assert veja_index < first_non_national
    assert ROUTES[VEJA_SOURCE.id] == VEJA_LATEST_ROUTE
    assert source_matches_strict("VEJA", VEJA_SOURCE)
    assert source_matches_strict("Revista Veja", VEJA_SOURCE)
    assert source_matches_strict("veja.abril.com.br", VEJA_SOURCE)


def test_veja_latest_collector_follows_article_link_and_ignores_external_hosts():
    extend_news_catalog(CATALOG_NATIONAL, CATALOG_NEWS_SOURCES)
    base_url, _allowed_hosts = ROUTES[VEJA_SOURCE.id]
    article_url = "https://veja.abril.com.br/brasil/2026/10/19/marinha-reforca-prontidao/"
    listing = """
    <html><body>
      <article><a href="/brasil/2026/10/19/marinha-reforca-prontidao/"
        aria-label="Marinha do Brasil reforça prontidão em operação naval">
        Marinha do Brasil reforça prontidão em operação naval
      </a><p>Informações sobre a operação da Marinha.</p></article>
      <article><a href="https://external.example/noticias/marinha/"
        aria-label="Marinha aparece em notícia de outro portal">
        Marinha aparece em notícia de outro portal
      </a></article>
    </body></html>
    """
    article = """
    <html><head>
      <meta property="og:title" content="Marinha do Brasil reforça prontidão em operação naval">
      <meta property="og:description" content="Informações sobre a operação da Marinha do Brasil.">
      <meta property="article:published_time" content="2026-10-19T16:00:00Z">
    </head><body></body></html>
    """
    http = FakeHttp({base_url: listing, article_url: article})

    captured_at = int(datetime(2026, 10, 19, 18, tzinfo=timezone.utc).timestamp() * 1000)
    from_ms = int(datetime(2026, 10, 19, 0, tzinfo=timezone.utc).timestamp() * 1000)
    outcome = NewsLatestCollector(http).collect(
        VEJA_SOURCE,
        ["Marinha"],
        [],
        from_ms,
        captured_at,
        captured_at,
    )

    assert not outcome.failed
    assert len(outcome.items) == 1
    assert outcome.items[0].source == "VEJA"
    assert outcome.items[0].link == article_url
    assert outcome.items[0].date == int(datetime(2026, 10, 19, 16, tzinfo=timezone.utc).timestamp() * 1000)
    assert http.calls == [base_url, article_url]


def test_application_composition_uses_extended_news_catalog():
    source = (ROOT / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    assert "NEWS_NATIONAL, NEWS_SOURCES = extend_news_catalog(NEWS_NATIONAL, NEWS_SOURCES)" in source
    assert "national_sources=NEWS_NATIONAL" in source
    assert "RuntimeNewsRunner(news_repository, prefs, NEWS_SOURCES)" in source
