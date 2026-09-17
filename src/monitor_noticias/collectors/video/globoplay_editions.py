from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus
import re
from bs4 import BeautifulSoup

from monitor_noticias.matching import canonical_key
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem, VideoSource
from monitor_noticias.networking import HttpClient
from .common import BROWSER_UA, VIDEO_LINK_RE, PROGRAM_LINK_RE, EMBED_TITLE_RE, EMBED_SUMMARY_RE, clean_text, clean_json_text, clean_trecho_title, useful_globo_title, normalize_embedded, normalize_program_page, normalize_direct_video_url, resolve_url
from .globoplay_trechos import KNOWN_PROGRAM_PAGES, _score

USER_AGENT=BROWSER_UA; REQUEST_TIMEOUT=14.0; MAX_HTML_BODY_BYTES=8*1024*1024
MAX_PROGRAM_LINKS_IN_HTML=80; MAX_VIDEO_LINKS_IN_HTML=120; EMBEDDED_CONTEXT_WINDOW=1800; MAX_TRECHOS_PER_SOURCE=48; MAX_DISCOVERY_ALIASES=4
DATE_RE=re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')
DISCOVERY_GENERIC_ALIASES={"globo","globoplay","jornalismo","noticias","noticia"}

@dataclass(slots=True)
class EditionRef:
    url:str
    publishedAt:int
    dateKey:str

def _parse_interval(value,captured):
    match=DATE_RE.search(value)
    if not match:return None
    try: day=datetime(int(match.group(3)),int(match.group(2)),int(match.group(1))).astimezone()
    except Exception:return None
    start=int(day.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()*1000)
    if start>captured:return None
    end=int(day.replace(hour=23,minute=59,second=59,microsecond=999000).timestamp()*1000)
    return start,min(end,captured),f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{int(match.group(3)):04d}"

def _looks_edition(value):
    normalized=normalize(value)
    return DATE_RE.search(value) is not None and any(token in normalized for token in ("edicao","integra","programa de hoje"))

class GloboplayEditionCollector:
    def __init__(self,http:HttpClient|None=None):self.http=http or HttpClient()
    def _fetch(self,url):
        text=self.http.get_text(url,headers={"User-Agent":USER_AGENT,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.7","Referer":"https://www.google.com/"},connect_timeout=REQUEST_TIMEOUT,read_timeout=REQUEST_TIMEOUT,max_body_bytes=MAX_HTML_BODY_BYTES)
        return BeautifulSoup(text,'html.parser')
    def _discovery_urls(self,source):
        if not source.searchUrlTemplate:return [source.landingUrl]
        state=source.state.strip() if len(source.state.strip())==2 and source.state.strip().lower()!="br" else ""
        primary=normalize(source.searchPrefix); queries=[]
        if source.searchPrefix.strip():queries.append(source.searchPrefix.strip())
        for alias in source.aliases:
            normalized=normalize(alias)
            if normalized and normalized!=primary and normalized not in DISCOVERY_GENERIC_ALIASES and len(queries)<1+MAX_DISCOVERY_ALIASES:queries.append(alias)
        out=[]
        for program in queries:
            url=source.searchUrlTemplate.replace("{query}",quote_plus(" ".join(x for x in (program,state) if x)))
            if url not in out:out.append(url)
        return out
    def _program_pages(self,source,doc,base):
        scored={}
        for anchor in doc.select('a[href]'):
            page=normalize_program_page(resolve_url(base,anchor.get('href','')))
            if not page:continue
            label=" • ".join(filter(None,[clean_text(anchor.get('aria-label','')),clean_text(anchor.get('title','')),clean_text(anchor.get_text(' ',strip=True)),clean_text(anchor.parent.get_text(' ',strip=True) if anchor.parent else '')]))[:1600]
            score=_score(source,page,label)
            if score>0:scored[page]=max(scored.get(page,-2**31),score)
        raw=normalize_embedded(str(doc))
        for i,match in enumerate(PROGRAM_LINK_RE.finditer(raw)):
            if i>=MAX_PROGRAM_LINKS_IN_HTML:break
            page=f"https://globoplay.globo.com/{match.group(1)}/t/{match.group(2)}";score=_score(source,page,'')
            if score>0:scored[page]=max(scored.get(page,-2**31),score)
        return [key for key,_ in sorted(scored.items(),key=lambda item:item[1],reverse=True)]
    def _direct_links(self,doc,base):
        out=[]
        for anchor in doc.select('a[href]'):
            direct=normalize_direct_video_url(resolve_url(base,anchor.get('href','')))
            if direct and direct not in out:out.append(direct)
        for i,match in enumerate(VIDEO_LINK_RE.finditer(normalize_embedded(str(doc)))):
            if i>=MAX_VIDEO_LINKS_IN_HTML:break
            direct=f"https://globoplay.globo.com/v/{match.group(1)}"
            if direct not in out:out.append(direct)
        return out
    def parse_editions(self,html,base,captured,from_,to):
        doc=BeautifulSoup(html,'html.parser') if isinstance(html,str) else html;out={}
        for anchor in doc.select('a[href]'):
            direct=normalize_direct_video_url(resolve_url(base,anchor.get('href','')))
            if not direct:continue
            context=" • ".join(filter(None,[clean_text(anchor.get('aria-label','')),clean_text(anchor.get('title','')),clean_text(anchor.get_text(' ',strip=True)),clean_text(anchor.parent.get_text(' ',strip=True) if anchor.parent else '')]))[:1600]
            if not _looks_edition(context):continue
            interval=_parse_interval(context,captured)
            if not interval or interval[1]<from_ or interval[0]>to:continue
            out[canonical_key(direct)]=EditionRef(direct,min(interval[1],to,captured),interval[2])
        raw=normalize_embedded(str(doc))
        for i,match in enumerate(VIDEO_LINK_RE.finditer(raw)):
            if i>=MAX_VIDEO_LINKS_IN_HTML:break
            start=max(0,match.start()-EMBEDDED_CONTEXT_WINDOW);end=min(len(raw),match.end()+EMBEDDED_CONTEXT_WINDOW);context=raw[start:end]
            if not _looks_edition(context):continue
            center=match.start()-start; intervals=[]
            for date_match in DATE_RE.finditer(context):
                interval=_parse_interval(date_match.group(0),captured)
                if interval:intervals.append((abs(date_match.start()-center),interval))
            if not intervals:continue
            interval=min(intervals,key=lambda item:item[0])[1]
            if interval[1]<from_ or interval[0]>to:continue
            direct=f"https://globoplay.globo.com/v/{match.group(1)}";out.setdefault(canonical_key(direct),EditionRef(direct,min(interval[1],to,captured),interval[2]))
        return sorted(out.values(),key=lambda item:item.publishedAt,reverse=True)
    def parse_trechos_from_edition(self,source,html,edition,captured):
        doc=BeautifulSoup(html,'html.parser') if isinstance(html,str) else html;out={}
        h1=clean_text(doc.select_one('h1').get_text(' ',strip=True)) if doc.select_one('h1') else ''
        detected=h1.split('.',1)[0].strip() if 2<=len(h1.split('.',1)[0].strip())<=80 else ''
        source_name=f"Globoplay • {detected}" if source.id=="video-globoplay-jornalismo" and detected else source.name
        def add(direct,raw_title,raw_summary):
            if canonical_key(direct)==canonical_key(edition.url):return
            title=clean_trecho_title(raw_title,source.searchPrefix)
            if not useful_globo_title(title) or _looks_edition(title):return
            summary=clean_text(raw_summary)
            if normalize(summary)==normalize(title):summary=''
            out.setdefault(canonical_key(direct),VideoItem(title=title[:220],sourceId=source.id,sourceName=source_name,publishedAt=edition.publishedAt,link=direct,summary=summary[:900],capturedAt=captured))
        for anchor in doc.select('a[href]'):
            direct=normalize_direct_video_url(resolve_url(edition.url,anchor.get('href','')))
            if not direct:continue
            values=[anchor.get('aria-label',''),anchor.get('title','')];img=anchor.select_one('img[alt]');values.append(img.get('alt','') if img else '');values.append(anchor.get_text(' ',strip=True))
            title=next((clean_trecho_title(clean_text(value),'') for value in values if useful_globo_title(clean_trecho_title(clean_text(value),'')) and not _looks_edition(value)),'')
            context=clean_text(anchor.parent.get_text(' ',strip=True) if anchor.parent else '')
            add(direct,title,context[len(title):].strip() if title and context.startswith(title) else context)
        raw=normalize_embedded(str(doc))
        for i,match in enumerate(VIDEO_LINK_RE.finditer(raw)):
            if i>=MAX_VIDEO_LINKS_IN_HTML:break
            direct=f"https://globoplay.globo.com/v/{match.group(1)}";start=max(0,match.start()-EMBEDDED_CONTEXT_WINDOW);end=min(len(raw),match.end()+EMBEDDED_CONTEXT_WINDOW);context=raw[start:end];center=match.start()-start
            def nearest(regex,low,high):
                values=[]
                for current in regex.finditer(context):
                    value=clean_json_text(current.group(1))
                    if low<=len(value)<=high and not value.lower().startswith(('http://','https://')) and '/v/' not in value:values.append((abs(current.start()-center),value))
                return min(values,key=lambda item:item[0])[1] if values else ''
            title=nearest(EMBED_TITLE_RE,6,260);summary=nearest(EMBED_SUMMARY_RE,8,900)
            if title:add(direct,title,summary)
        return list(out.values())[:MAX_TRECHOS_PER_SOURCE]
    def collect(self,source,captured,from_,to,on_error=lambda:None):
        if not source.searchPrefix.strip():return []
        pages=[];seed_docs=[]
        known=KNOWN_PROGRAM_PAGES.get(source.id)
        if known:pages.append(known)
        landing=normalize_program_page(source.landingUrl)
        if landing and landing not in pages:pages.append(landing)
        direct=normalize_direct_video_url(source.landingUrl)
        if direct:
            try:
                doc=self._fetch(direct);seed_docs.append((doc,direct))
                for page in self._program_pages(source,doc,direct):
                    if page not in pages:pages.append(page)
            except Exception:on_error()
        if not pages:
            for discovery in self._discovery_urls(source):
                if pages:break
                try:doc=self._fetch(discovery)
                except Exception:on_error();continue
                for page in self._program_pages(source,doc,discovery):
                    if page not in pages:pages.append(page)
                if not pages:
                    for seed in self._direct_links(doc,discovery)[:2]:
                        try:seed_doc=self._fetch(seed)
                        except Exception:on_error();continue
                        seed_docs.append((seed_doc,seed))
                        for page in self._program_pages(source,seed_doc,seed):
                            if page not in pages:pages.append(page)
        editions={}
        for doc,url in seed_docs:
            for edition in self.parse_editions(doc,url,captured,from_,to):editions.setdefault(canonical_key(edition.url),edition)
        for page in pages[:2]:
            try:doc=self._fetch(page)
            except Exception:on_error();continue
            for edition in self.parse_editions(doc,page,captured,from_,to):editions.setdefault(canonical_key(edition.url),edition)
        out={}
        for edition in sorted(editions.values(),key=lambda item:item.publishedAt,reverse=True)[:3]:
            try:doc=self._fetch(edition.url)
            except Exception:on_error();continue
            for item in self.parse_trechos_from_edition(source,doc,edition,captured):out.setdefault(canonical_key(item.link),item)
        return list(out.values())[:MAX_TRECHOS_PER_SOURCE]
