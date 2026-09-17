from __future__ import annotations

import base64, json, re
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from .http_client import HttpClient

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
BATCH="https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je"

def is_google_news(url:str)->bool:
    try:return "news.google.com" in (urlsplit(url).hostname or "").lower()
    except Exception:return "news.google.com" in url.lower()

class GoogleNewsUrlResolver:
    def __init__(self,http:HttpClient|None=None)->None:self.http=http or HttpClient(); self.cache={}
    def resolve(self,input_:str)->str:
        if not is_google_news(input_):return input_
        if input_ in self.cache:return self.cache[input_]
        decoded=self._resolve(input_); resolved=decoded if decoded and decoded.startswith("http") and not is_google_news(decoded) else input_
        self.cache[input_]=resolved; return resolved
    def _resolve(self,input_:str):
        try:id_=urlsplit(input_).path.rstrip("/").split("/")[-1].strip()
        except Exception:return None
        if not id_:return None
        return self._legacy(id_) or self._signed(id_) or self._id_only(id_)
    def _legacy(self,id_:str):
        try:
            padded=id_+"="*((4-len(id_)%4)%4); text=base64.urlsafe_b64decode(padded).decode("latin1")
            starts=[i for i in (text.find("https://"),text.find("http://")) if i>=0]
            if not starts:return None
            start=min(starts); end=len(text)
            for i,ch in enumerate(text[start:],start):
                if ord(ch)<32 or ch=="\x00":end=i;break
            candidate=text[start:end].strip()
            return candidate if urlsplit(candidate).hostname and not is_google_news(candidate) else None
        except Exception:return None
    def _signed(self,id_:str):
        try:
            text=self.http.get_text(f"https://news.google.com/articles/{id_}?hl=pt-BR&gl=BR&ceid=BR:pt-419",headers={"User-Agent":UA},connect_timeout=15,read_timeout=15)
            soup=BeautifulSoup(text,"html.parser"); node=soup.select_one("c-wiz > div[data-n-a-sg][data-n-a-ts]") or soup.select_one(f"[data-n-a-id='{id_}'][data-n-a-sg][data-n-a-ts]") or soup.select_one("[data-n-a-sg][data-n-a-ts]")
            if node is None:return None
            sig=node.get("data-n-a-sg",""); ts=node.get("data-n-a-ts",""); article=node.get("data-n-a-id","") or id_
            if not sig or not ts:return None
            inner=json.dumps(["garturlreq",[["pt-BR","BR",["FINANCE_TOP_INDICES","WEB_TEST_1_0_0"],None,None,1,1,"BR:pt-419",None,480,None,None,None,None,None,0,5],"pt-BR","BR",1,[2,4,8],1,1,None,0,0,None,0],article,int(ts),sig],ensure_ascii=False,separators=(",",":"))
            return self._batch(inner)
        except Exception:return None
    def _id_only(self,id_:str):
        try:
            inner=json.dumps(["garturlreq",[["en-US","US",["FINANCE_TOP_INDICES","WEB_TEST_1_0_0"],None,None,1,1,"US:en",None,180,None,None,None,None,None,0,None,None,[1608992183,723341000]],"en-US","US",1,[2,3,4,8],1,0,"655000234",0,0,None,0],id_],separators=(",",":"))
            return self._batch(inner)
        except Exception:return None
    def _batch(self,inner:str):
        payload=json.dumps([[['Fbv4je',inner,None,'generic']]],separators=(",",":"))
        body=self.http.post_form_text(BATCH,{"f.req":payload},headers={"User-Agent":UA,"Content-Type":"application/x-www-form-urlencoded;charset=UTF-8","Referer":"https://news.google.com/"},connect_timeout=15,read_timeout=15)
        return self._extract(body)
    @staticmethod
    def _extract(body:str):
        guarded=body.split("\n\n",1)[-1].strip()
        try:
            outer=json.loads(guarded)
            for row in outer:
                if isinstance(row,list) and len(row)>2 and isinstance(row[2],str) and row[2]:
                    try:decoded=json.loads(row[2])
                    except Exception:continue
                    if isinstance(decoded,list) and len(decoded)>1 and isinstance(decoded[1],str) and decoded[1].startswith("http") and not is_google_news(decoded[1]):return decoded[1]
        except Exception:pass
        normalized=body.replace("\\/","/").replace("\\u003d","=").replace("\\u0026","&").replace("\\u0025","%")
        for candidate in re.findall(r'https?://[^\\"\s]+',normalized):
            candidate=candidate.rstrip(",]}\\")
            if not is_google_news(candidate) and "googleusercontent.com" not in candidate.lower() and "gstatic.com" not in candidate.lower():return candidate
        return None
