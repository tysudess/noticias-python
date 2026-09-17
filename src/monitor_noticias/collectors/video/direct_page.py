from __future__ import annotations
import re
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from monitor_noticias.matching import canonicalize_url,is_specific_video_url,useful_title
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem
from monitor_noticias.networking import HttpClient
from .common import BROWSER_UA,clean_text,normalize_embedded

MAX_HTML_BODY_BYTES=8*1024*1024;MAX_ENRICHED_SUMMARY_LENGTH=1800
DATE_RE=re.compile(r'"(?:datePublished|uploadDate|dateCreated|publishedAt|publicationDate|publishedDate)"\s*:\s*"([^"]+)"',re.I)
JSON_TEXT_RE=re.compile(r'"(?:description|seoDescription|summary|headline|alternativeHeadline|caption|articleBody)"\s*:\s*"([^"]{2,700})"',re.I|re.S)

def _parse_iso(value,captured):
    try:
        millis=int(datetime.fromisoformat(value.strip().replace('Z','+00:00')).timestamp()*1000);return millis if 1<=millis<=captured else None
    except Exception:return None

def _canonical(doc,fallback):
    values=[];element=doc.select_one('link[rel="canonical"]');values.append(element.get('href','') if element else '');element=doc.select_one('meta[property="og:url"]');values.append(element.get('content','') if element else '');values.append(fallback)
    for value in values:
        if not value:continue
        canonical=canonicalize_url(urljoin(fallback,value))
        if canonical.startswith(('http://','https://')):return canonical
    return ''

def _published(doc,captured):
    values=[]
    for selector in ('meta[property="article:published_time"]','meta[property="og:published_time"]','meta[name="date"]','meta[itemprop="datePublished"]','time[datetime]'):
        element=doc.select_one(selector)
        if element:values += [element.get('content',''),element.get('datetime','')]
    for script in doc.select("script[type='application/ld+json'],script")[:80]:values += [match.group(1) for match in list(DATE_RE.finditer(normalize_embedded(script.string or script.get_text() or '')))[:6]]
    for value in values:
        parsed=_parse_iso(value,captured)
        if parsed:return parsed
    return None

def _has_video(doc):
    if doc.select_one('video,meta[property="og:video"],meta[property="og:video:url"],iframe[src*="youtube"],iframe[src*="player"]'):return True
    for script in doc.select('script')[:60]:
        raw=normalize_embedded(script.string or script.get_text() or '')
        if any(token.lower() in raw.lower() for token in ('VideoObject','contentUrl','embedUrl','videoId')):return True
    return False

class DirectVideoPageResolver:
    def __init__(self,http:HttpClient|None=None):self.http=http or HttpClient()
    def resolve(self,source,candidate,captured):
        if not is_specific_video_url(source,candidate.link):return None
        text=self.http.get_text(candidate.link,headers={"User-Agent":BROWSER_UA,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.7","Referer":"https://www.google.com/"},connect_timeout=14.0,read_timeout=14.0,max_body_bytes=MAX_HTML_BODY_BYTES);doc=BeautifulSoup(text,'html.parser');canonical=_canonical(doc,candidate.link)
        if not canonical:return None
        values=[]
        for selector,attribute in [('meta[property="og:title"]','content'),('meta[name="twitter:title"]','content'),('h1',None)]:
            element=doc.select_one(selector);values.append(element.get(attribute,'') if element and attribute else (element.get_text(' ',strip=True) if element else ''))
        values += [candidate.title,doc.title.get_text(' ',strip=True) if doc.title else ''];title=next((clean_text(value) for value in values if useful_title(clean_text(value))),'')
        if not useful_title(title):return None
        descriptions=[]
        for selector in ('meta[property="og:description"]','meta[name="twitter:description"]','meta[name="description"]','meta[itemprop="description"]'):
            element=doc.select_one(selector);descriptions.append(clean_text(element.get('content','')) if element else '')
        descriptions.append(candidate.summary);description=next((value for value in descriptions if value),'');structured=[]
        for script in doc.select("script[type='application/ld+json'],script")[:80]:structured.extend(clean_text(match.group(1)) for match in list(JSON_TEXT_RE.finditer(normalize_embedded(script.string or script.get_text() or '')))[:6])
        pieces=[]
        for value in [description,*structured[:6]]:
            if value and normalize(value) not in {normalize(item) for item in pieces}:pieces.append(value)
        summary=' • '.join(pieces)[:MAX_ENRICHED_SUMMARY_LENGTH];published=_published(doc,captured) or (candidate.publishedAt if candidate.publishedAt>0 else 0)
        if not is_specific_video_url(source,canonical) and not _has_video(doc):return None
        return VideoItem(title=title[:220],sourceId=source.id,sourceName=source.name,publishedAt=published,link=canonical,summary=summary,matchedTerm=candidate.matchedTerm,matchedDemand=candidate.matchedDemand,capturedAt=candidate.capturedAt)
