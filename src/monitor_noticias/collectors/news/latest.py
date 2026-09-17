from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

from monitor_noticias.matching import subject_matches
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import Demand, MediaSource, News
from monitor_noticias.networking import HttpClient

USER_AGENT = "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36 MonitorNoticias/4.0"
REQUEST_TIMEOUT = 12.0
MAX_BODY_BYTES = 3_500_000
MAX_MATCHED_PER_SOURCE = 20
FUTURE_TOLERANCE_MS = 10 * 60 * 1000
ROUTES = {
    "nacional-cnn": ("https://www.cnnbrasil.com.br/ultimas-noticias/", {"cnnbrasil.com.br"}),
    "nacional-metropoles": ("https://www.metropoles.com/ultimas-noticias", {"metropoles.com"}),
    "nacional-folha": ("https://www1.folha.uol.com.br/ultimas-noticias/", {"folha.uol.com.br"}),
    "nacional-r7": ("https://noticias.r7.com/", {"r7.com"}),
    "nacional-jovem-pan": ("https://jovempan.com.br/noticias/", {"jovempan.com.br"}),
    "nacional-o-globo": ("https://oglobo.globo.com/ultimas-noticias/", {"oglobo.globo.com"}),
}
GENERIC_TITLES = {"ultimas noticias", "noticias", "leia mais", "veja mais", "saiba mais", "pagina inicial"}
DATE_RE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I)

@dataclass(slots=True)
class Outcome:
    items: list[News]
    failed: bool = False

def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def _useful(value: str) -> bool:
    cleaned = _clean(value)
    return len(cleaned) >= 18 and normalize(cleaned) not in GENERIC_TITLES and sum(ch.isalnum() for ch in cleaned) >= 12

def _canonical(value: str) -> str:
    try:
        uri = urlsplit(value); host = (uri.hostname or "").lower().removeprefix("www.")
        if not host:
            return value.split("#", 1)[0].split("?", 1)[0]
        path = (uri.path or "").rstrip("/") or "/"
        return f"{(uri.scheme or 'https').lower()}://{host}{path}"
    except Exception:
        return value.split("#", 1)[0].split("?", 1)[0].rstrip("/")

def _looks_article(value: str) -> bool:
    try:
        path = (urlsplit(value).path or "").lower()
    except Exception:
        return False
    if not path or path == "/" or any(x in path for x in ("/ultimas-noticias", "/busca", "/login", "/assine")):
        return False
    return path.count("/") >= 2 or path.endswith((".html", ".shtml", ".ghtml"))

def _vehicle_matches(source: MediaSource, vehicle: str) -> bool:
    if not vehicle.strip():
        return True
    wanted = normalize(vehicle)
    for alias in [source.name, *source.aliases]:
        actual = normalize(alias)
        if actual == wanted or actual.replace(" ", "") == wanted.replace(" ", ""):
            return True
        if len(wanted) >= 5 and (actual.startswith(wanted) or wanted.startswith(actual)):
            return True
    return False

def _parse_iso(value: str) -> int | None:
    try:
        return int(datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return None

def _published(soup: BeautifulSoup, captured_at: int) -> int | None:
    values: list[str] = []
    for el in soup.select('meta[property="article:published_time"],meta[name="date"],meta[itemprop="datePublished"],time[datetime]'):
        values.extend([el.get("content", ""), el.get("datetime", "")])
    values += DATE_RE.findall(str(soup))[:8]
    for value in values:
        parsed = _parse_iso(value)
        if parsed is not None and 1 <= parsed <= captured_at + FUTURE_TOLERANCE_MS:
            return min(parsed, captured_at)
    return None

class NewsLatestCollector:
    def __init__(self, http: HttpClient | None = None):
        self.http = http or HttpClient()

    def fetch(self, url: str) -> BeautifulSoup:
        text = self.http.get_text(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7", "Referer": "https://www.google.com/"}, connect_timeout=REQUEST_TIMEOUT, read_timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_BODY_BYTES)
        return BeautifulSoup(text, "html.parser")

    def collect(self, source: MediaSource, terms: list[str], demands: list[Demand], from_: int, to: int, captured_at: int) -> Outcome:
        route = ROUTES.get(source.id)
        if not route:
            return Outcome([])
        base, hosts = route
        try:
            listing = self.fetch(base)
        except Exception:
            return Outcome([], True)
        candidates: dict[str, tuple[str, str, str]] = {}
        for anchor in listing.select("a[href]"):
            link = urljoin(base, anchor.get("href", "").strip())
            host = (urlsplit(link).hostname or "").lower().removeprefix("www.")
            if not host or not any(host == allowed or host.endswith("." + allowed) for allowed in hosts):
                continue
            if _canonical(link) == _canonical(base) or not _looks_article(link):
                continue
            choices = [anchor.get("aria-label", ""), anchor.get("title", "")]
            img = anchor.select_one("img[alt]"); choices.append(img.get("alt", "") if img else ""); choices.append(anchor.get_text(" ", strip=True))
            title = next((_clean(x) for x in choices if _useful(_clean(x))), "")
            if not _useful(title):
                continue
            parent = _clean(anchor.parent.get_text(" ", strip=True) if anchor.parent else "")
            snippet = parent[len(title):].strip()[:700] if parent.startswith(title) else parent[:700]
            body = f"{title} {snippet}"
            if not (any(subject_matches(body, term) for term in terms) or any(_vehicle_matches(source, demand.vehicle) and subject_matches(body, demand.subject) for demand in demands)):
                continue
            candidates.setdefault(_canonical(link), (title, snippet, link))
        out: list[News] = []
        for title, snippet, link in list(candidates.values())[:MAX_MATCHED_PER_SOURCE]:
            try:
                article = self.fetch(link)
            except Exception:
                article = None
            if article:
                title_values: list[str] = []
                for selector, attr in [('meta[property="og:title"]', "content"), ('meta[name="twitter:title"]', "content"), ("h1", None)]:
                    el = article.select_one(selector); title_values.append(el.get(attr, "") if el and attr else (el.get_text(" ", strip=True) if el else ""))
                title_values.append(article.title.get_text(" ", strip=True) if article.title else "")
                article_title = next((_clean(x) for x in title_values if _useful(_clean(x))), title)
                desc_values = []
                for selector in ('meta[property="og:description"]', 'meta[name="twitter:description"]', 'meta[name="description"]'):
                    el = article.select_one(selector); desc_values.append(_clean(el.get("content", "")) if el else "")
                article_snippet = next((x for x in desc_values if x), snippet)
                published = _published(article, captured_at) or captured_at
            else:
                article_title, article_snippet, published = title, snippet, captured_at
            body = f"{article_title} {article_snippet}"
            matched_terms = [term for term in terms if subject_matches(body, term)]
            demand = next((d for d in demands if _vehicle_matches(source, d.vehicle) and subject_matches(body, d.subject)), None)
            if not matched_terms and demand is None:
                continue
            if not (from_ <= published <= to):
                continue
            out.append(News(title=article_title[:260], source=source.name, date=published, link=link, snippet=article_snippet[:700], important=demand is not None, demand=demand is not None, matchedTerm=", ".join(dict.fromkeys(matched_terms)), matchedDemand=(f"{demand.vehicle} • {demand.subject}" if demand else ""), capturedAt=captured_at))
        unique = {_canonical(item.link): item for item in out}
        return Outcome(sorted(unique.values(), key=lambda item: item.date, reverse=True))
