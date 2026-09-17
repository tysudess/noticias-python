from __future__ import annotations
from urllib.parse import quote_plus,urljoin
from bs4 import BeautifulSoup
from monitor_noticias.matching import canonical_key,is_specific_video_url,useful_title
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem
from monitor_noticias.networking import HttpClient
from .common import BROWSER_UA,clean_text,VIDEO_LINK_RE

MAX_HTML_BODY_BYTES=8*1024*1024

def _candidate_title(anchor):
    values=[anchor.get('aria-label',''),anchor.get('title','')];img=anchor.select_one('img[alt]');values.append(img.get('alt','') if img else '');values.append(anchor.get_text(' ',strip=True))
    return next((clean_text(value) for value in values if useful_title(clean_text(value))),'')

class WebsiteVideoCollector:
    def __init__(self,http:HttpClient|None=None):self.http=http or HttpClient()
    def _page(self,source,page_url,captured,fallback_summary):
        text=self.http.get_text(page_url,headers={"User-Agent":BROWSER_UA,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.7","Referer":"https://www.google.com/"},connect_timeout=14.0,read_timeout=14.0,max_body_bytes=MAX_HTML_BODY_BYTES);doc=BeautifulSoup(text,'html.parser');out={}
        for anchor in doc.select('a[href]'):
            absolute=urljoin(page_url,anchor.get('href','').strip())
            if not is_specific_video_url(source,absolute):continue
            title=_candidate_title(anchor);parent=clean_text(anchor.parent.get_text(' ',strip=True) if anchor.parent else '')
            if not parent or normalize(parent)==normalize(title) or len(parent)>480:summary=fallback_summary
            else:
                summary=parent[len(title):].strip() if title and parent.startswith(title) else parent
                if not summary:summary=fallback_summary
            out.setdefault(canonical_key(absolute),VideoItem(title=(title or f"Vídeo recente • {source.name}")[:220],sourceId=source.id,sourceName=source.name,publishedAt=0,link=absolute,summary=summary[:420],capturedAt=captured))
        if 'globoplay.globo.com' in source.landingUrl.lower():
            for match in VIDEO_LINK_RE.finditer(text):
                direct=f"https://globoplay.globo.com/v/{match.group(1)}";out.setdefault(canonical_key(direct),VideoItem(title=f"Vídeo recente • {source.name}",sourceId=source.id,sourceName=source.name,publishedAt=0,link=direct,summary=fallback_summary,capturedAt=captured))
        return list(out.values())[:80 if 'globoplay' in source.id else 40]
    def fetch_website(self,source,captured):return self._page(source,source.landingUrl,captured,source.group)
    def fetch_search_website(self,source,query,captured):
        effective=' '.join(value for value in [source.searchPrefix.strip(),query.strip()] if value);url=source.searchUrlTemplate.replace('{query}',quote_plus(effective));return self._page(source,url,captured,f"Resultado em {source.name}")
