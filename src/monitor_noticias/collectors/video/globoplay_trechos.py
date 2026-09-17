from __future__ import annotations
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from monitor_noticias.matching import canonical_key
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem, VideoSource
from monitor_noticias.networking import HttpClient
from .common import *

USER_AGENT = BROWSER_UA
REQUEST_TIMEOUT = 14.0
MAX_HTML_BODY_BYTES = 8 * 1024 * 1024
MAX_PROGRAM_PAGES_PER_SOURCE = 2
MAX_SEED_VIDEOS = 2
MAX_TRECHOS_PER_SOURCE = 48
MAX_PROGRAM_LINKS_IN_HTML = 80
MAX_VIDEO_LINKS_IN_HTML = 120
EMBEDDED_CONTEXT_WINDOW = 1800
KNOWN_PROGRAM_PAGES = {
    "globoplay-bom-dia-brasil": "https://globoplay.globo.com/bom-dia-brasil/t/6Qg1RywhG5",
    "globoplay-hora-1": "https://globoplay.globo.com/hora-1/t/s1Zp7Mf9Mn",
    "globoplay-jornal-hoje": "https://globoplay.globo.com/jornal-hoje/t/w7R6S8ssrm",
    "globoplay-jornal-nacional": "https://globoplay.globo.com/jornal-nacional/t/QgkQnhBNnR",
    "globoplay-jornal-da-globo": "https://globoplay.globo.com/jornal-da-globo/t/N6jszcBg6m",
    "globoplay-sp1": "https://globoplay.globo.com/sp1/t/MvdbFs2kN8",
    "globoplay-sp2": "https://globoplay.globo.com/sp2/t/xbFtFNTP81",
    "globoplay-bom-dia-es": "https://globoplay.globo.com/bom-dia-es/t/DLBLDnCVGs",
    "globoplay-tj1-tapajos": "https://globoplay.globo.com/jornal-tapajos-1a-edicao/t/hTwfdtmDCQ",
}

def _score(source: VideoSource, url: str, label: str) -> int:
    candidate = normalize(url + " " + label); wanted = normalize(source.searchPrefix)
    if not wanted: return 0
    candidate_tokens = set(candidate.split())
    wanted_tokens = [x for x in wanted.split() if len(x) >= 2 and x not in {"de","do","da","dos","das","e","em","no","na","nos","nas","a","o","as","os"}]
    if not wanted_tokens: return 0
    score = sum(10 for token in wanted_tokens if token in candidate_tokens)
    if wanted in candidate: score += 50
    for alias in source.aliases:
        normalized = normalize(alias)
        if len(normalized) >= 4 and normalized in candidate: score += 8
    return score

class GloboplayTrechosCollector:
    def __init__(self, http: HttpClient | None = None): self.http = http or HttpClient()

    def _fetch(self, url: str) -> BeautifulSoup:
        text = self.http.get_text(url, headers={"User-Agent":USER_AGENT,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.7","Referer":"https://www.google.com/"}, connect_timeout=REQUEST_TIMEOUT, read_timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_HTML_BODY_BYTES)
        return BeautifulSoup(text, 'html.parser')

    def _discovery_url(self, source: VideoSource) -> str:
        if not source.searchUrlTemplate: return source.landingUrl
        state = source.state.strip() if len(source.state.strip()) == 2 and source.state.strip().lower() != "br" else ""
        query = " ".join(x for x in [source.searchPrefix.strip(), state] if x)
        return source.searchUrlTemplate.replace("{query}", quote_plus(query))

    def _program_pages(self, source: VideoSource, doc: BeautifulSoup, base: str) -> list[str]:
        found: dict[str,int] = {}
        for anchor in doc.select('a[href]'):
            page = normalize_program_page(resolve_url(base, anchor.get('href','')))
            if page:
                score = _score(source, page, anchor.get_text(' ', strip=True))
                if score > 0: found[page] = max(found.get(page, -(2**31)), score)
        html = normalize_embedded(str(doc))
        for i, match in enumerate(PROGRAM_LINK_RE.finditer(html)):
            if i >= MAX_PROGRAM_LINKS_IN_HTML: break
            page = f"https://globoplay.globo.com/{match.group(1)}/t/{match.group(2)}"; score = _score(source, page, "")
            if score > 0: found[page] = max(found.get(page, -(2**31)), score)
        return [key for key, _ in sorted(found.items(), key=lambda item: item[1], reverse=True)]

    def _direct_links(self, doc: BeautifulSoup, base: str) -> list[str]:
        out: list[str] = []
        for anchor in doc.select('a[href]'):
            direct = normalize_direct_video_url(resolve_url(base, anchor.get('href','')))
            if direct and direct not in out: out.append(direct)
        for i, match in enumerate(VIDEO_LINK_RE.finditer(normalize_embedded(str(doc)))):
            if i >= MAX_VIDEO_LINKS_IN_HTML: break
            direct = f"https://globoplay.globo.com/v/{match.group(1)}"
            if direct not in out: out.append(direct)
        return out

    def parse_trechos(self, source: VideoSource, html, page_url: str, captured_at: int) -> list[VideoItem]:
        doc = BeautifulSoup(html, 'html.parser') if isinstance(html, str) else html
        out: dict[str, VideoItem] = {}
        def add(direct: str, raw_title: str, raw_summary: str, published: int = 0):
            title = clean_trecho_title(raw_title, source.searchPrefix)
            if not useful_globo_title(title): title = f"Trecho recente • {source.searchPrefix or source.name}"
            contextual = clean_text(raw_summary); parts=[]
            for value in [source.searchPrefix, contextual]:
                if value and normalize(value) != normalize(title) and normalize(value) not in {normalize(x) for x in parts}: parts.append(value)
            item = VideoItem(title=title[:220], sourceId=source.id, sourceName=source.name, publishedAt=published, link=direct, summary=" • ".join(parts)[:900], capturedAt=captured_at)
            key = canonical_key(direct)
            if key not in out or candidate_quality(item) > candidate_quality(out[key]): out[key] = item
        section = None
        for element in doc.select('h1,h2,h3,h4,a[href]'):
            if element.name and element.name.lower().startswith('h'):
                section = parse_day_upper(element.get_text(' ', strip=True), captured_at); continue
            direct = normalize_direct_video_url(resolve_url(page_url, element.get('href','')))
            if not direct: continue
            values=[element.get('aria-label',''),element.get('title','')]; img=element.select_one('img[alt]'); values.append(img.get('alt','') if img else ''); values.append(element.get_text(' ',strip=True))
            raw_title = next((clean_text(x) for x in values if clean_text(x)), '')
            parent = clean_text(element.parent.get_text(' ',strip=True) if element.parent else '')
            add(direct, raw_title, parent, section or 0)
        raw_html = normalize_embedded(str(doc))
        for i, match in enumerate(VIDEO_LINK_RE.finditer(raw_html)):
            if i >= MAX_VIDEO_LINKS_IN_HTML: break
            direct=f"https://globoplay.globo.com/v/{match.group(1)}"; start=max(0,match.start()-EMBEDDED_CONTEXT_WINDOW); end=min(len(raw_html),match.end()+EMBEDDED_CONTEXT_WINDOW); context=raw_html[start:end]; center=match.start()-start
            nearest=[]
            for regex, low, high in ((EMBED_TITLE_RE,6,260),(EMBED_SUMMARY_RE,8,900)):
                choices=[]
                for m in regex.finditer(context):
                    value=clean_json_text(m.group(1))
                    if low <= len(value) <= high and not value.lower().startswith(('http://','https://')) and '/v/' not in value: choices.append((abs(m.start()-center),value))
                nearest.append(min(choices, key=lambda x:x[0])[1] if choices else '')
            title, summary = nearest
            if normalize(title) == normalize(source.searchPrefix): title=''
            dates=[(abs(m.start()-center),parse_iso_ms(m.group(1),captured_at)) for m in EMBED_DATE_RE.finditer(context)]; dates=[x for x in dates if x[1] is not None]
            published=min(dates, key=lambda x:x[0])[1] if dates else (parse_day_upper(context,captured_at) or 0)
            add(direct,title,summary,published)
        return list(out.values())[:MAX_TRECHOS_PER_SOURCE]

    def collect(self, source: VideoSource, captured_at: int, on_error=lambda: None) -> list[VideoItem]:
        if not source.searchPrefix.strip(): return []
        program_pages: dict[str,int] = {}
        if source.id in KNOWN_PROGRAM_PAGES: program_pages[KNOWN_PROGRAM_PAGES[source.id]] = 2**31-1
        landing = normalize_program_page(source.landingUrl)
        if landing: program_pages[landing] = 2**31-2
        if not program_pages and normalize_direct_video_url(source.landingUrl):
            try:
                doc=self._fetch(source.landingUrl)
                for page in self._program_pages(source,doc,source.landingUrl): program_pages[page]=_score(source,page,'')
            except Exception: on_error()
        if not program_pages:
            discovery=self._discovery_url(source)
            try: doc=self._fetch(discovery)
            except Exception: on_error(); doc=None
            if doc:
                for page in self._program_pages(source,doc,discovery): program_pages[page]=_score(source,page,'')
                if not program_pages:
                    for seed in self._direct_links(doc,discovery)[:MAX_SEED_VIDEOS]:
                        try: seed_doc=self._fetch(seed)
                        except Exception: on_error(); continue
                        for page in self._program_pages(source,seed_doc,seed): program_pages[page]=_score(source,page,'')
        out: dict[str,VideoItem] = {}
        for page,_ in sorted(program_pages.items(), key=lambda item:item[1], reverse=True)[:MAX_PROGRAM_PAGES_PER_SOURCE]:
            url=page.rstrip('/')+'/cenas/'
            try: doc=self._fetch(url)
            except Exception: on_error(); continue
            for item in self.parse_trechos(source,doc,url,captured_at): out.setdefault(canonical_key(item.link),item)
        return list(out.values())[:MAX_TRECHOS_PER_SOURCE]
