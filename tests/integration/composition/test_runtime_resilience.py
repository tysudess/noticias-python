from __future__ import annotations

import threading, time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeNewsRunner, RuntimeVideoRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import News
from monitor_noticias.repositories import NewsRepository, VideoRepository, VideoTermStore

class PartialGoogle:
    def collect(self,query):
        if query=="FALHA": return None
        # O limite superior da busca é fixado antes das chamadas ao collector.
        # A fixture de sucesso deve ficar inequivocamente dentro da janela testada.
        published_at=int(time.time()*1000)-1000
        return [News(title="Marinha em operação",source="Fonte",date=published_at,link="https://example.test/ok",snippet="MARINHA",capturedAt=published_at)]
class BlockingGoogle:
    def __init__(self): self.started=threading.Event(); self.release=threading.Event()
    def collect(self,query):
        self.started.set(); self.release.wait(3)
        now=int(time.time()*1000)
        return [News(title="Marinha em operação",source="Fonte",date=now,link="https://example.test/cancel",snippet="MARINHA",capturedAt=now)]
class FakeLatest: pass
class NoVideo:
    def search_videos(self,**kwargs): raise AssertionError
class NeverUsed:
    def __getattr__(self,name): raise AssertionError(f"não deveria coletar: {name}")

def _news_repo(tmp_path,google):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs(); prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties"); db=NewsDb(paths.news_db)
    for term in db.listTerms(): db.removeTerm(term)
    return paths,prefs,db,NewsRepository(db,google=google,latest=FakeLatest(),national_sources=())

def test_partial_source_error_continues_and_persists_success(tmp_path: Path):
    paths,prefs,db,repo=_news_repo(tmp_path,PartialGoogle()); db.addTerm("FALHA"); db.addTerm("MARINHA")
    result=repo.search((),True)
    assert result.errors==1 and result.newCount==1
    assert db.listNews(10)[0].link=="https://example.test/ok"; db.close()

def test_cancelled_real_runner_returns_idle_and_does_not_persist(tmp_path: Path):
    google=BlockingGoogle(); paths,prefs,db,repo=_news_repo(tmp_path,google); db.addTerm("MARINHA")
    runner=RuntimeNewsRunner(repo,prefs,()); service=AutomationService(AutomationSettings(prefs),runner,NoVideo())
    assert service.search_news(); assert google.started.wait(1)
    service.stop_news_search(); google.release.set()
    deadline=time.time()+5
    while service.state.newsBusy and time.time()<deadline: time.sleep(0.01)
    assert not service.state.newsBusy and "interrompida" in service.state.status.lower()
    assert db.listNews(10)==[]
    service.close(); db.close()

def test_empty_video_selection_processes_no_source(tmp_path: Path):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs(); prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties")
    prefs.update(desktop_video_source_ids=set(),desktop_video_sources_v6_migrated=True)
    news=NewsDb(paths.news_db); videos=VideoDb(paths.videos_db); terms=VideoTermStore(prefs); terms.save(["MARINHA"])
    repo=VideoRepository(news,videos,terms,youtube=NeverUsed(),website=NeverUsed(),direct=NeverUsed(),editions=NeverUsed(),trechos=NeverUsed(),jarvis=NeverUsed())
    result=RuntimeVideoRunner(repo,prefs).search_videos(token=type("T",(),{"raise_if_cancelled":lambda self:None})(),progress=lambda _p:None)
    assert result.items==() and videos.listAll()==[]
    news.close(); videos.close()
