from __future__ import annotations

import time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeNewsRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.collectors.video.catalog import BASE_VIDEO_SOURCES, DEFAULT_IDS, VIDEO_SOURCES
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import News
from monitor_noticias.repositories import NewsRepository, VideoTermStore
from monitor_noticias.ui.runtime_controller import RuntimeUiController

class FakeGoogle:
    def __init__(self): self.calls=[]
    def collect(self, query):
        self.calls.append(query)
        # O repository congela o limite superior da janela antes de chamar o collector.
        # Mantém a fixture inequivocamente dentro dessa janela em runners mais lentos.
        published_at=int(time.time()*1000)-1000
        return [News(title="Marinha realiza exercício naval",source="Fonte Teste",date=published_at,link="https://example.test/noticia",snippet="Operação da Marinha",capturedAt=published_at)]
class FakeLatest: pass
class NoopVideoRunner:
    def search_videos(self,**kwargs): raise AssertionError("vídeo não deve executar neste teste")
class FakeProxy:
    def load(self):
        class C: status_label="Proxy desativado"
        return C()
class FakeStartup:
    def configure(self,_enabled): return True

def wait_idle(automation, timeout=5):
    deadline=time.time()+timeout
    while automation.state.newsBusy and time.time()<deadline: time.sleep(0.01)
    assert not automation.state.newsBusy

def test_complete_video_catalog_matches_kotlin_cardinality_and_defaults():
    assert len(BASE_VIDEO_SOURCES)==132
    assert len(VIDEO_SOURCES)==134
    assert len({source.id for source in VIDEO_SOURCES})==134
    assert {"youtube-g1","youtube-domingo-espetacular"} <= DEFAULT_IDS
    assert {"globoplay-jornal-nacional","video-r7-record","youtube-cnn-brasil"} <= {source.id for source in VIDEO_SOURCES}

def test_ui_to_repository_matching_sqlite_and_ui_refresh(tmp_path: Path):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs(); prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties")
    news_db=NewsDb(paths.news_db); video_db=VideoDb(paths.videos_db)
    for term in news_db.listTerms(): news_db.removeTerm(term)
    news_db.addTerm("MARINHA")
    fake_google=FakeGoogle(); repository=NewsRepository(news_db,google=fake_google,latest=FakeLatest(),national_sources=())
    runner=RuntimeNewsRunner(repository,prefs,())
    automation=AutomationService(AutomationSettings(prefs),runner,NoopVideoRunner())
    controller=RuntimeUiController(paths=paths,prefs=prefs,news_db=news_db,video_db=video_db,proxy=FakeProxy(),startup=FakeStartup(),automation=automation,news_sources=(),video_sources=(),specialized_sources=(),default_video_source_ids=set(),video_term_store=VideoTermStore(prefs))
    assert controller.search_news() is True
    wait_idle(automation); controller.sync_automation_state()
    stored=news_db.listNews(10)
    assert len(stored)==1 and stored[0].matchedTerm=="MARINHA"
    assert controller.state.news and controller.state.news[0].link=="https://example.test/noticia"
    assert "https://example.test/noticia" in controller.state.new_news_links
    assert fake_google.calls==["MARINHA"]
    controller.close()

def test_video_terms_persist_independently_across_reopen(tmp_path: Path):
    prefs_path=tmp_path/"data"/"prefs"/"monitor_prefs.properties"; prefs=SharedPreferences(prefs_path); store=VideoTermStore(prefs)
    values=store.load(["NOTICIA"]); assert "NOTICIA" in values
    store.add("TERMO SOMENTE VIDEO",["NOTICIA"])
    reopened=VideoTermStore(SharedPreferences(prefs_path)); assert "TERMO SOMENTE VIDEO" in reopened.load(["OUTRO"])
    assert "OUTRO" not in reopened.load(["OUTRO"])
