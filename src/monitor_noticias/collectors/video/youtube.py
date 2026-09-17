from __future__ import annotations
from datetime import datetime
import re
from bs4 import BeautifulSoup

from monitor_noticias.matching import canonical_key, canonicalize_url, is_youtube_video_url, useful_title
from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem, VideoSource
from monitor_noticias.networking import HttpClient
from .common import BROWSER_UA, clean_text

MAX_HTML_BODY_BYTES = 8 * 1024 * 1024
MAX_YOUTUBE_ITEMS_PER_SCAN = 40
KNOWN_CHANNEL_IDS = {"youtube-g1":"UCaGmdJSSiR7fkh2A-c6emsA","youtube-domingo-espetacular":"UCP-Vg2PcmLiWpEdvMI1R35w"}
CHANNEL_ID_RES=[re.compile(r'"channelId":"(UC[0-9A-Za-z_-]{20,})"'),re.compile(r'"externalId":"(UC[0-9A-Za-z_-]{20,})"'),re.compile(r'"browseId":"(UC[0-9A-Za-z_-]{20,})"')]

def _relative_ms(raw,captured):
    text=normalize(raw);number=next((int(token) for token in text.split() if token.isdigit()),None)
    if number is None:return captured
    if "minuto" in text or "minute" in text:delta=number*60_000
    elif "hora" in text or "hour" in text:delta=number*60*60_000
    elif "dia" in text or "day" in text:delta=number*24*60*60_000
    elif "semana" in text or "week" in text:delta=number*7*24*60*60_000
    elif "mes" in text or "month" in text:delta=number*30*24*60*60_000
    elif "ano" in text or "year" in text:delta=number*365*24*60*60_000
    else:delta=0
    return max(captured-delta,1)

def _json_text(block,field):
    position=block.find(field)
    if position<0:return ''
    section=block[position:position+1800];markers=[(section.find('"simpleText":"'),len('"simpleText":"')),(section.find('"text":"'),len('"text":"'))];markers=[item for item in markers if item[0]>=0]
    if not markers:return ''
    marker,length=min(markers,key=lambda item:item[0]);index=marker+length;out=[];escaped=False
    while index<len(section):
        char=section[index]
        if escaped:out.append(' ' if char in 'nrt' else ('"' if char=='"' else ('\\' if char=='\\' else ('/' if char=='/' else char))));escaped=False
        elif char=='\\':escaped=True
        elif char=='"':break
        else:out.append(char)
        index+=1
    return clean_text(''.join(out))

def parse_videos_tab(source,html,captured):
    if not html:return []
    out={};needle='"videoId":"';cursor=0
    while cursor<len(html) and len(out)<MAX_YOUTUBE_ITEMS_PER_SCAN:
        marker=html.find(needle,cursor)
        if marker<0:break
        start=marker+len(needle);end=html.find('"',start)
        if end<0:break
        video_id=html[start:end];cursor=end+1
        if len(video_id)<6:continue
        block=html[end:min(len(html),end+5200)];title=_json_text(block,'"title"')
        if not useful_title(title):continue
        published_text=_json_text(block,'"publishedTimeText"');link=canonicalize_url(f"https://www.youtube.com/watch?v={video_id}")
        out.setdefault(canonical_key(link),VideoItem(title=title[:220],sourceId=source.id,sourceName=source.name,publishedAt=_relative_ms(published_text,captured),link=link,summary=f"Canal oficial • {source.group} • Aba Vídeos",capturedAt=captured))
    return list(out.values())[:MAX_YOUTUBE_ITEMS_PER_SCAN]

def parse_feed(source,xml,captured):
    soup=BeautifulSoup(xml,'xml');out=[]
    for entry in soup.find_all('entry'):
        title=clean_text(entry.find('title').get_text() if entry.find('title') else '');link_el=entry.find('link',href=True);link=canonicalize_url(link_el.get('href','') if link_el else '')
        if not useful_title(title) or not is_youtube_video_url(link):continue
        try:published=int(datetime.fromisoformat((entry.find('published').get_text() if entry.find('published') else '').replace('Z','+00:00')).timestamp()*1000)
        except Exception:published=captured
        description=''
        for tag in entry.find_all():
            if tag.name and str(tag.name).lower().endswith('description'):
                description=clean_text(tag.get_text())
                if description:break
        summary=' • '.join(dict.fromkeys(value for value in [description,f"Canal oficial • {source.group}"] if value))[:1000]
        out.append(VideoItem(title=title[:220],sourceId=source.id,sourceName=source.name,publishedAt=published,link=link,summary=summary,capturedAt=captured))
    return out

class YouTubeCollector:
    def __init__(self,http:HttpClient|None=None):self.http=http or HttpClient()
    def collect(self,source:VideoSource,captured:int):
        handle=source.youtubeHandle.removeprefix('@').strip();known=KNOWN_CHANNEL_IDS.get(source.id,'')
        if known:videos_url=f"https://www.youtube.com/channel/{known}/videos"
        elif handle:videos_url=f"https://www.youtube.com/@{handle}/videos"
        elif '/videos' in source.landingUrl.lower():videos_url=source.landingUrl
        else:videos_url=source.landingUrl.rstrip('/')+'/videos'
        html=self.http.get_text(videos_url,headers={"User-Agent":BROWSER_UA,"Accept-Language":"pt-BR,pt;q=0.9,en;q=0.7","Referer":"https://www.youtube.com/"},connect_timeout=18.0,read_timeout=18.0,max_body_bytes=MAX_HTML_BODY_BYTES)
        tab=parse_videos_tab(source,html,captured);channel_id=known
        if not channel_id:
            for regex in CHANNEL_ID_RES:
                match=regex.search(html)
                if match:channel_id=match.group(1);break
        feed=[]
        if channel_id:
            try:
                xml=self.http.get_text(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",headers={"User-Agent":BROWSER_UA},connect_timeout=16.0,read_timeout=16.0,max_body_bytes=MAX_HTML_BODY_BYTES);feed=parse_feed(source,xml,captured)
            except Exception:feed=[]
        out={}
        for item in feed+tab:out.setdefault(canonical_key(item.link),item)
        return list(out.values())[:MAX_YOUTUBE_ITEMS_PER_SCAN]
