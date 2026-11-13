from __future__ import annotations

from datetime import datetime, timezone

from monitor_noticias.collectors.news.latest import NewsLatestCollector, ROUTES
from monitor_noticias.models import MediaSource


ARTICLE_URL = (
    "https://www.naval.com.br/blog/2026/11/11/"
    "classe-udaloy-os-cacadores-de-submarinos-da-marinha-sovietica-e-russa/"
)
LISTING_URL = "https://www.naval.com.br/blog/"


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_text(self, url, **_kwargs):
        self.calls.append(url)
        if url not in self.responses:
            raise RuntimeError(f"GET inesperado: {url}")
        return self.responses[url]


def test_poder_naval_has_direct_latest_route():
    assert ROUTES["especializada-poder-naval"] == (
        LISTING_URL,
        {"naval.com.br"},
    )


def test_poder_naval_latest_collector_finds_article_from_site_listing():
    listing = f'''<html><body><article>
      <a href="{ARTICLE_URL}" title="Classe Udaloy: os caçadores de submarinos">
        Classe Udaloy: os caçadores de submarinos da Marinha soviética e russa
      </a>
      <p>A classe Udaloy foi desenvolvida para a guerra antissubmarino.</p>
    </article></body></html>'''
    article = '''<html><head>
      <meta property="og:title" content="Classe Udaloy: os caçadores de submarinos da Marinha soviética e russa">
      <meta property="og:description" content="A classe Udaloy foi desenvolvida para a guerra antissubmarino.">
      <meta property="article:published_time" content="2026-11-11T08:00:00-03:00">
    </head><body><h1>Classe Udaloy: os caçadores de submarinos</h1></body></html>'''
    collector = NewsLatestCollector(FakeHttp({LISTING_URL: listing, ARTICLE_URL: article}))
    source = MediaSource(
        id="especializada-poder-naval",
        name="Poder Naval",
        region="Nacional",
        state="BR",
        stateName="Brasil",
        group="Mídia especializada",
        aliases=["PoderNaval", "naval.com.br"],
    )
    captured = int(datetime(2026, 11, 13, 12, tzinfo=timezone.utc).timestamp() * 1000)

    outcome = collector.collect(
        source,
        ["Udaloy"],
        [],
        captured - 5 * 24 * 60 * 60 * 1000,
        captured,
        captured,
    )

    assert outcome.failed is False
    assert len(outcome.items) == 1
    assert outcome.items[0].source == "Poder Naval"
    assert outcome.items[0].link == ARTICLE_URL
    assert "Udaloy" in outcome.items[0].title
    assert collector.http.calls == [LISTING_URL, ARTICLE_URL]
