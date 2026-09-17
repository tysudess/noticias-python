from pathlib import Path
from datetime import datetime,timezone
from monitor_noticias.collectors.news.google_news import parse_google_news_xml
from monitor_noticias.collectors.video.globoplay_jarvis import expand_queries,source_matches_program
from monitor_noticias.collectors.video.youtube import parse_videos_tab
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS
from monitor_noticias.models import VideoSource

FIX=Path(__file__).parents[1]/'fixtures'/'collectors'
def test_google_fixture_kotlin_expected_fields():
    items=parse_google_news_xml((FIX/'google_news.xml').read_text(encoding='utf-8'));assert [(x.title,x.source,x.link,x.snippet) for x in items]==[('Marinha em operação','Fonte X','https://x/a','Texto da notícia')]
def test_jarvis_query_expansion_kotlin_golden():
    assert expand_queries(['comemorações 7 setembro'])==['7 setembro','desfiles 7 setembro','desfiles 7 setembro pais','comemoracoes 7 setembro','independencia 7 setembro'];assert expand_queries(['Militares'])[:2]==['Militares','militar']
def test_jarvis_program_boundary_golden():
    source=VideoSource(id='jh',name='Jornal Hoje',group='Globoplay',landingUrl='x',searchPrefix='Jornal Hoje',aliases=['JH']);assert source_matches_program(source,'Jornal Hoje') and source_matches_program(source,'Jornal Hoje Edição') and not source_matches_program(source,'Jornal Nacional')
def test_youtube_relative_time_and_canonical_golden():
    html='<script>{"videoId":"abc123XYZ00","title":{"runs":[{"text":"Marinha realiza exercício naval"}]},"publishedTimeText":{"simpleText":"2 horas atrás"}}</script>';cap=int(datetime(2026,9,12,20,tzinfo=timezone.utc).timestamp()*1000);item=parse_videos_tab(DESKTOP_VIDEO_EXTRAS[0],html,cap)[0];assert item.link=='https://www.youtube.com/watch?v=abc123XYZ00' and item.publishedAt==cap-2*60*60*1000
