from __future__ import annotations
import re,time
from bs4 import BeautifulSoup
from monitor_noticias.matching.common import normalize
from monitor_noticias.matching import phrase_matches
from monitor_noticias.models import VideoItem
from monitor_noticias.networking import HttpClient
from .common import BROWSER_UA,normalize_embedded,parse_iso_ms

JARVIS_ENDPOINT="https://cloud-jarvis.globo.com/graphql";CONNECT_TIMEOUT=8.0;READ_TIMEOUT=12.0;DIRECT_PAGE_TIMEOUT=12.0
MAX_DIRECT_HTML_BYTES=4*1024*1024;RETRY_DELAY=.350;MAX_ATTEMPTS=2;MAX_QUERIES_PER_SCAN=28;MAX_DATE_ENRICHMENTS_PER_SCAN=48;TARGET_DATE_CONTEXT_CHARS=4000
USER_AGENT="Mozilla/5.0 (Linux; Android 14; Mobile) MonitorNoticias/3.0.10"
HEADERS={"Content-Type":"application/json; charset=utf-8","Accept":"application/json","Accept-Language":"pt-BR,pt;q=0.9","User-Agent":USER_AGENT,"x-platform-id":"web","x-device-id":"desktop","x-client-version":"2024.12-5"}
SEARCH_DOCUMENT="query MonitorGloboplaySearch($q:String!,$page:Int) { search { videos(query:$q,page:$page) { page nextPage total hasNextPage resources { id headline description duration title { headline originProgramId } } } } }"
DATE_RE=re.compile(r'"(?:datePublished|uploadDate|dateCreated|publishedAt|publicationDate|publishedDate|exhibitedAt)"\s*:\s*"([^"]+)"',re.I)
STOP={"de","do","da","dos","das","e","em","no","na","nos","nas","a","o","as","os"}
class Outcome:
    def __init__(self,candidatesBySourceId,failedQueries):self.candidatesBySourceId=candidatesBySourceId;self.failedQueries=failedQueries

def expand_queries(raw):
    out={}
    def add(value):
        cleaned=re.sub(r'\s+',' ',value).strip();key=normalize(cleaned)
        if len(cleaned)>=3 and key:out.setdefault(key,cleaned)
    for value in raw:
        normalized=normalize(value)
        if not normalized:continue
        tokens=normalized.split();token_set=set(tokens)
        if "7" in token_set and "setembro" in token_set:
            for query in ("7 setembro","desfiles 7 setembro","desfiles 7 setembro pais","comemoracoes 7 setembro","independencia 7 setembro"):add(query)
        else:
            add(value);compact=" ".join(token for token in tokens if token not in STOP)
            if compact and compact!=normalized:add(compact)
            if len(tokens)==1 and normalized.endswith("es") and len(normalized)>=7:add(normalized[:-2])
            elif len(tokens)==1 and normalized.endswith("s") and len(normalized)>=6:add(normalized[:-1])
    return list(out.values())[:MAX_QUERIES_PER_SCAN]

def source_matches_program(source,program_name):
    program=normalize(program_name)
    if not program:return False
    for candidate in [source.name,source.searchPrefix,*source.aliases]:
        current=normalize(candidate)
        if len(current)>=4 and (program==current or program.startswith(current+" ") or current.startswith(program+" ")):return True
    return False

class GloboplayJarvisCollector:
    def __init__(self,http=None,sleeper=time.sleep):self.http=http or HttpClient();self.sleeper=sleeper
    def _fetch_retry(self,query):
        payload={"operationName":"MonitorGloboplaySearch","variables":{"q":query,"page":1},"query":SEARCH_DOCUMENT}
        for attempt in range(MAX_ATTEMPTS):
            try:
                response=self.http.post_json(JARVIS_ENDPOINT,payload,headers=HEADERS,connect_timeout=CONNECT_TIMEOUT,read_timeout=READ_TIMEOUT)
                if response.get("errors") is None:return response
            except Exception:pass
            if attempt+1<MAX_ATTEMPTS:self.sleeper(RETRY_DELAY)
        return None
    def _fetch_published_at(self,video_id,url,captured):
        text=self.http.get_text(url,headers={"User-Agent":BROWSER_UA,"Accept-Language":"pt-BR,pt;q=0.9","Referer":"https://globoplay.globo.com/"},connect_timeout=DIRECT_PAGE_TIMEOUT,read_timeout=DIRECT_PAGE_TIMEOUT,max_body_bytes=MAX_DIRECT_HTML_BYTES)
        doc=BeautifulSoup(text,'html.parser')
        for selector in ('meta[property="article:published_time"]','meta[property="og:published_time"]','meta[itemprop="datePublished"]'):
            element=doc.select_one(selector)
            if element:
                parsed=parse_iso_ms(element.get('content',''),captured)
                if parsed:return parsed
        best=None;distance_best=2**31-1;patterns=[f'"id":{video_id}',f'"id":"{video_id}"',f'/v/{video_id}/']
        for script in doc.select("script[type='application/ld+json'],script")[:120]:
            raw=normalize_embedded(script.string or script.get_text() or '');markers=[]
            for marker in patterns:
                start=0
                while len(markers)<24:
                    position=raw.lower().find(marker.lower(),start)
                    if position<0:break
                    markers.append(position);start=position+len(marker)
            if not markers:continue
            for index,match in enumerate(DATE_RE.finditer(raw)):
                if index>=160:break
                parsed=parse_iso_ms(match.group(1),captured)
                if not parsed:continue
                distance=min(abs(match.start()-marker) for marker in markers)
                if distance<=TARGET_DATE_CONTEXT_CHARS and distance<distance_best:distance_best=distance;best=parsed
        return best
    def collect(self,raw_queries,sources,captured):
        if not sources:return Outcome({},0)
        buckets={source.id:{} for source in sources};failed=0
        for query in expand_queries(raw_queries):
            response=self._fetch_retry(query)
            if response is None:failed+=1;continue
            videos=(((response.get("data") or {}).get("search") or {}).get("videos") or {})
            for video in videos.get("resources") or []:
                video_id=str(video.get("id") or '').strip();headline=str(video.get("headline") or '').strip();description=str(video.get("description") or '').strip();title=video.get("title") or {};program=str(title.get("headline") or '').strip();program_id=str(title.get("originProgramId") or '').strip()
                if len(video_id)<5 or len(headline)<8 or not program:continue
                source=next((item for item in sources if source_matches_program(item,program)),None)
                if source is None:continue
                parts=[value for value in [description,f"Programa: {program}",f"Programa ID: {program_id}" if program_id else '',"Descoberto via Globoplay Jarvis"] if value]
                summary=" • ".join(dict.fromkeys(parts))[:1400]
                buckets[source.id].setdefault(video_id,VideoItem(title=headline[:220],sourceId=source.id,sourceName=source.name,publishedAt=0,link=f"https://globoplay.globo.com/v/{video_id}/",summary=summary,capturedAt=captured))
        budget=MAX_DATE_ENRICHMENTS_PER_SCAN;final={}
        for source_id,items in buckets.items():
            values=[]
            for video_id,item in items.items():
                body=f"{item.title} {item.summary}"
                if budget>0 and any(query.strip() and phrase_matches(body,query) for query in raw_queries):
                    budget-=1
                    try:published=self._fetch_published_at(video_id,item.link,captured)
                    except Exception:published=None
                    if published:item=VideoItem(title=item.title,sourceId=item.sourceId,sourceName=item.sourceName,publishedAt=published,link=item.link,summary=item.summary,matchedTerm=item.matchedTerm,matchedDemand=item.matchedDemand,capturedAt=item.capturedAt)
                values.append(item)
            final[source_id]=values
        return Outcome(final,failed)
