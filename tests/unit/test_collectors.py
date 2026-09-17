from datetime import datetime, timezone
from monitor_noticias.collectors.news.google_news import GoogleNewsCollector
from monitor_noticias.collectors.news.latest import NewsLatestCollector
from monitor_noticias.collectors.video.globoplay_trechos import GloboplayTrechosCollector
from monitor_noticias.collectors.video.globoplay_editions import GloboplayEditionCollector
from monitor_noticias.collectors.video.globoplay_jarvis import GloboplayJarvisCollector, JARVIS_ENDPOINT
from monitor_noticias.collectors.video.youtube import YouTubeCollector
from monitor_noticias.collectors.video.website import WebsiteVideoCollector
from monitor_noticias.collectors.video.direct_page import DirectVideoPageResolver
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS
from monitor_noticias.models import MediaSource, VideoSource, VideoItem

class FakeHttp:
    def __init__(self,gets=None,posts=None):self.gets=gets or {};self.posts=list(posts or []);self.calls=[]
    def get_text(self,url,**kwargs):
        self.calls.append(('GET',url,kwargs));value=self.gets.get(url)
        if isinstance(value,Exception):raise value
        if value is None:raise RuntimeError('unexpected GET '+url)
        return value
    def post_json(self,url,payload,**kwargs):
        self.calls.append(('POST',url,kwargs,payload))
        if not self.posts:raise RuntimeError('unexpected POST')
        value=self.posts.pop(0)
        if isinstance(value,Exception):raise value
        return value

RSS='<rss><channel><item><title>Marinha em operação</title><link>https://x/a</link><pubDate>Sat, 12 Sep 2026 18:00:00 GMT</pubDate><description><![CDATA[<b>Texto</b> da notícia]]></description><source>Fonte X</source></item></channel></rss>'
def test_google_news_contract_and_error():
    url='https://news.google.com/rss/search?q=Marinha+do+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419';fake=FakeHttp(gets={url:RSS});items=GoogleNewsCollector(fake).collect('Marinha do Brasil')
    assert len(items)==1 and items[0].snippet=='Texto da notícia';assert fake.calls[0][2]['connect_timeout']==8.0 and fake.calls[0][2]['read_timeout']==10.0
    assert GoogleNewsCollector(FakeHttp(gets={'https://news.google.com/rss/search?q=x&hl=pt-BR&gl=BR&ceid=BR:pt-419':RuntimeError('x')})).collect('x') is None

LATEST='<html><body><div><a href="/politica/2026/09/noticia.html" aria-label="Marinha realiza grande operação naval no litoral">Marinha realiza grande operação naval no litoral</a> detalhes da Marinha</div></body></html>'
ARTICLE='<html><head><meta property="og:title" content="Marinha realiza grande operação naval no litoral"><meta property="og:description" content="Operação da Marinha do Brasil"><meta property="article:published_time" content="2026-09-12T18:00:00Z"></head></html>'
def test_latest_news_listing_article():
    base='https://www.cnnbrasil.com.br/ultimas-noticias/';article='https://www.cnnbrasil.com.br/politica/2026/09/noticia.html';fake=FakeHttp(gets={base:LATEST,article:ARTICLE});source=MediaSource(id='nacional-cnn',name='CNN Brasil',region='Nacional',state='BR',stateName='Brasil',group='CNN',aliases=['CNN']);cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000)
    out=NewsLatestCollector(fake).collect(source,['Marinha'],[],cap-86400000,cap,cap);assert not out.failed and len(out.items)==1 and out.items[0].matchedTerm=='Marinha';assert fake.calls[0][2]['read_timeout']==12.0

def test_latest_news_listing_failure_is_failed():
    base='https://www.cnnbrasil.com.br/ultimas-noticias/';source=MediaSource(id='nacional-cnn',name='CNN Brasil',region='Nacional',state='BR',stateName='Brasil',group='CNN');assert NewsLatestCollector(FakeHttp(gets={base:RuntimeError('x')})).collect(source,['Marinha'],[],0,10,10).failed

TRECHOS='<html><body><h2>Hoje, 12/09/2026</h2><a href="https://globoplay.globo.com/v/14938964/" aria-label="Marinha participa de operação no litoral">Marinha participa de operação no litoral</a></body></html>'
def test_globoplay_trechos_known_program():
    page='https://globoplay.globo.com/jornal-hoje/t/w7R6S8ssrm/cenas/';fake=FakeHttp(gets={page:TRECHOS});source=VideoSource(id='globoplay-jornal-hoje',name='Jornal Hoje',group='Globoplay',landingUrl='https://globoplay.globo.com/jornal-hoje/t/w7R6S8ssrm',searchPrefix='Jornal Hoje');cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000)
    out=GloboplayTrechosCollector(fake).collect(source,cap);assert len(out)==1 and out[0].link=='https://globoplay.globo.com/v/14938964';assert fake.calls[0][2]['read_timeout']==14.0

PROGRAM='<html><body><a href="/v/12345678/">Edição de 12/09/2026</a></body></html>';EDITION='<html><body><h1>Jornal Hoje.</h1><a href="/v/14938964/" aria-label="Marinha participa de operação no litoral">Marinha participa de operação no litoral</a></body></html>'
def test_globoplay_editions_program_to_trecho():
    program='https://globoplay.globo.com/jornal-hoje/t/w7R6S8ssrm';edition='https://globoplay.globo.com/v/12345678';fake=FakeHttp(gets={program:PROGRAM,edition:EDITION});source=VideoSource(id='globoplay-jornal-hoje',name='Jornal Hoje',group='Globoplay',landingUrl=program,searchPrefix='Jornal Hoje');cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000)
    out=GloboplayEditionCollector(fake).collect(source,cap,cap-86400000,cap);assert len(out)==1 and out[0].link=='https://globoplay.globo.com/v/14938964'

JARVIS={"data":{"search":{"videos":{"resources":[{"id":"14938964","headline":"Marinha participa de operação no litoral","description":"Detalhes","duration":120,"title":{"headline":"Jornal Hoje","originProgramId":"jh"}}]}}}};DIRECT='<html><head><meta property="article:published_time" content="2026-09-12T17:30:00Z"></head></html>'
def test_jarvis_retry_headers_and_enrichment():
    fake=FakeHttp(gets={'https://globoplay.globo.com/v/14938964/':DIRECT},posts=[{"errors":[{}]},JARVIS]);sleeps=[];source=VideoSource(id='globoplay-jornal-hoje',name='Jornal Hoje',group='Globoplay',landingUrl='x',searchPrefix='Jornal Hoje');cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000)
    out=GloboplayJarvisCollector(fake,sleeper=sleeps.append).collect(['Marinha'],[source],cap);assert out.failedQueries==0 and out.candidatesBySourceId[source.id][0].publishedAt>0;assert len([c for c in fake.calls if c[0]=='POST'])==2 and sleeps==[0.350];assert [c for c in fake.calls if c[0]=='POST'][0][1]==JARVIS_ENDPOINT

YT_HTML='<script>{"videoId":"abc123XYZ00","title":{"runs":[{"text":"Marinha realiza exercício naval"}]},"publishedTimeText":{"simpleText":"2 horas atrás"}}</script>';YT_RSS='<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/"><entry><title>Marinha realiza exercício naval</title><link href="https://www.youtube.com/watch?v=abc123XYZ00"/><published>2026-09-12T17:00:00Z</published><media:group><media:description>Descrição oficial</media:description></media:group></entry></feed>'
def test_youtube_page_and_feed_prefers_feed():
    page='https://www.youtube.com/channel/UCaGmdJSSiR7fkh2A-c6emsA/videos';feed='https://www.youtube.com/feeds/videos.xml?channel_id=UCaGmdJSSiR7fkh2A-c6emsA';fake=FakeHttp(gets={page:YT_HTML,feed:YT_RSS});cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000);out=YouTubeCollector(fake).collect(DESKTOP_VIDEO_EXTRAS[0],cap)
    assert len(out)==1 and out[0].publishedAt==int(datetime(2026,9,12,17,tzinfo=timezone.utc).timestamp()*1000);assert fake.calls[0][2]['read_timeout']==18.0 and fake.calls[1][2]['read_timeout']==16.0

def test_desktop_extras_exact():
    assert [item.id for item in DESKTOP_VIDEO_EXTRAS]==['youtube-g1','youtube-domingo-espetacular']

WEBSITE='<html><body><a href="/videos/noticia-importante-1234" title="Marinha participa de operação naval">Marinha participa de operação naval</a></body></html>'
def test_website_and_direct_page():
    source=VideoSource(id='video-cnn-brasil',name='CNN Brasil',group='CNN',landingUrl='https://x/videos',linkHints=['/videos/'],searchUrlTemplate='https://x/busca?q={query}',searchPrefix='CNN');search='https://x/busca?q=CNN+Marinha';out=WebsiteVideoCollector(FakeHttp(gets={search:WEBSITE})).fetch_search_website(source,'Marinha',1000);assert len(out)==1
    direct='<html><head><link rel="canonical" href="https://x/videos/noticia-importante-1234"><meta property="og:title" content="Marinha participa de operação naval"><meta property="og:description" content="Descrição detalhada"><meta property="article:published_time" content="2026-09-12T17:00:00Z"></head><body><video></video></body></html>';cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000);candidate=VideoItem(title='Marinha participa de operação naval',sourceId=source.id,sourceName=source.name,publishedAt=0,link='https://x/videos/noticia-importante-1234?utm=x',capturedAt=cap);resolved=DirectVideoPageResolver(FakeHttp(gets={candidate.link:direct})).resolve(source,candidate,cap);assert resolved and resolved.link=='https://x/videos/noticia-importante-1234' and resolved.publishedAt>0
