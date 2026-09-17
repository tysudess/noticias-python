from __future__ import annotations
from email.utils import parsedate_to_datetime
import re
import time
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from monitor_noticias.models import News
from monitor_noticias.networking import HttpClient

USER_AGENT = "Mozilla/5.0 MonitorNoticiasAndroid/3.0"
CONNECT_TIMEOUT = 8.0
READ_TIMEOUT = 10.0
BASE = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"

def _parse_date(value: str, now_ms: int | None = None) -> int:
    try:
        return int(parsedate_to_datetime(value).timestamp() * 1000)
    except Exception:
        return now_ms if now_ms is not None else int(time.time() * 1000)

def parse_google_news_xml(xml_text: str, *, now_ms: int | None = None) -> list[News]:
    root = ET.fromstring(xml_text)
    out: list[News] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "Google Notícias").strip()
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
            text = self.http.get_text(self.build_url(query), headers={"User-Agent": USER_AGENT}, connect_timeout=CONNECT_TIMEOUT, read_timeout=READ_TIMEOUT)
            return parse_google_news_xml(text)
        except Exception:
            return None
