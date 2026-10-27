from __future__ import annotations

from datetime import timezone
from email.utils import parsedate_to_datetime
import re
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from monitor_noticias.models import News
from monitor_noticias.networking import HttpClient
from monitor_noticias.networking.source_sites import register_source_site

USER_AGENT = "Mozilla/5.0 MonitorNoticiasAndroid/3.0"
CONNECT_TIMEOUT = 8.0
READ_TIMEOUT = 10.0
BASE = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def _parse_date(value: str, now_ms: int | None = None) -> int:
    """Parse the publication date without inventing a capture-time fallback.

    ``now_ms`` remains accepted for compatibility with older callers, but an
    absent or malformed pubDate is represented as 0 (unknown). If a feed omits
    its timezone, treat it as UTC so Windows and Ubuntu produce the same value.
    """
    del now_ms
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError, OSError):
        return 0


def parse_google_news_xml(xml_text: str, *, now_ms: int | None = None) -> list[News]:
    root = ET.fromstring(xml_text)
    out: list[News] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_element = item.find("source")
        source = (
            (source_element.text or "Google Notícias").strip()
            if source_element is not None
            else "Google Notícias"
        )
        # O RSS do Google Notícias informa o endereço do veículo no atributo
        # source@url. Registramos a origem oficial em memória para mostrar seu
        # favicon sem fazer uma requisição adicional por cada notícia.
        if source_element is not None:
            register_source_site(source, source_element.get("url", ""))
        desc = re.sub(r"<[^>]*>", "", item.findtext("description") or "").strip()
        date = _parse_date(item.findtext("pubDate") or "", now_ms)
        if title and link:
            out.append(News(title=title, source=source, date=date, link=link, snippet=desc[:500]))
    return out


class GoogleNewsCollector:
    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient()

    def build_url(self, query: str) -> str:
        return BASE.format(q=quote_plus(query, encoding="utf-8"))

    def collect(self, query: str) -> list[News] | None:
        try:
            text = self.http.get_text(
                self.build_url(query),
                headers={"User-Agent": USER_AGENT},
                connect_timeout=CONNECT_TIMEOUT,
                read_timeout=READ_TIMEOUT,
            )
            return parse_google_news_xml(text)
        except Exception:
            return None
