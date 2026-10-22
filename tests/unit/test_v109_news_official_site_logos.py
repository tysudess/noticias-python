from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from monitor_noticias.collectors.news.google_news import parse_google_news_xml
from monitor_noticias.networking.source_sites import (
    build_favicon_request_url,
    clear_source_sites_for_tests,
    get_source_site,
    normalize_site_url,
    resolve_source_site_url,
)


def test_google_news_rss_registers_the_official_publisher_url():
    clear_source_sites_for_tests()
    xml = '''<rss><channel><item>
      <title>Operação naval é anunciada</title>
      <link>https://news.google.com/rss/articles/abc123</link>
      <pubDate>Thu, 22 Oct 2026 14:00:00 GMT</pubDate>
      <description>Detalhes da operação naval.</description>
      <source url="https://www.folha.uol.com.br/poder/">Folha de S.Paulo</source>
    </item></channel></rss>'''

    news = parse_google_news_xml(xml, now_ms=1_800_000_000_000)

    assert len(news) == 1
    assert get_source_site(news[0].source) == "https://www.folha.uol.com.br/"
    assert resolve_source_site_url(news[0]) == "https://www.folha.uol.com.br/"


def test_direct_article_link_supplies_site_when_source_url_is_missing():
    clear_source_sites_for_tests()
    news = SimpleNamespace(
        source="Portal Regional",
        link="https://noticias.exemplo.com.br/politica/materia-123?utm_source=x",
    )

    assert resolve_source_site_url(news) == "https://noticias.exemplo.com.br/"


def test_google_news_wrapper_uses_known_publisher_fallback_for_old_history():
    clear_source_sites_for_tests()
    news = SimpleNamespace(
        source="G1",
        link="https://news.google.com/rss/articles/abc123",
    )

    assert resolve_source_site_url(news) == "https://g1.globo.com/"


def test_invalid_or_non_public_site_urls_are_rejected():
    assert normalize_site_url("javascript:alert(1)") == ""
    assert normalize_site_url("https://localhost/admin") == ""
    assert normalize_site_url("https://user:password@portal.example.com/path") == ""
    assert normalize_site_url("https://news.google.com/rss/articles/123") == ""


def test_favicon_request_uses_only_site_origin_and_requested_size():
    url = build_favicon_request_url("https://www.folha.uol.com.br/poder/noticia.html?secret=ignore")
    parsed = urlsplit(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.google.com"
    assert params["domain_url"] == ["https://www.folha.uol.com.br/"]
    assert params["sz"] == ["64"]
    assert "noticia.html" not in url


def test_existing_app_installs_the_async_favicon_painter():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    composition = (root / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    patch = (root / "src/monitor_noticias/ui/news_site_icons_patch.py").read_text(encoding="utf-8")

    assert "install_news_site_icons_patch()" in composition
    assert "QThreadPool" in patch
    assert "setMaxThreadCount(3)" in patch
    assert "NewsDelegate.paint = paint_with_official_site_icon" in patch
