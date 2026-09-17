from __future__ import annotations

import time
from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeVideoRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import VideoItem
from monitor_noticias.repositories import VideoRepository, VideoTermStore
from monitor_noticias.ui.runtime_controller import RuntimeUiController

class FakeWebsite:
    def fetch_search_website(self,source,query,captured_at):
        return [VideoItem(title="Marinha realiza exercício naval",sourceId=source.id,sourceName=source.name,publishedAt=captured_at,link="https://www.cnnbrasil.com.br/videos/marinha-exercicio",summary="Operação da Marinha",capturedAt=captured_at)]
    def fetch_website(self,source,captured_at): return []
class FakeDirect:
    def resolve(self,source,item,captured_at): return item
class NeverUsed:
    def __getattr__(self,name): raise AssertionError(f"collector inesperado: {name}")
class NoopNewsRunner:
    def search_news(self,**kwargs): raise AssertionError
    def search_demand(self,*args,**kwargs): raise AssertionError
    def search_all_demands(self,**kwargs): raise AssertionError
class FakeProxy:
    def load(self):
        class C: status_label="Proxy desativado"
        return C()
class FakeStartup:
    def configure(self,_enabled): return True

def wait_idle(automation,timeout=5):
    deadline=time.time()+timeout
    while automation.state.videoBusy and time.time()<deadline: time.sleep(0.01)
    assert not automation.state.videoBusy

def test_ui_to_video_collect_matching_sqlite_and_ui_refresh(tmp_path: Path):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs(); prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties")
    news_db=NewsDb(paths.news_db); video_db=VideoDb(paths.videos_db); terms=VideoTermStore(prefs); terms.save(["MARINHA"])
    prefs.update(desktop_video_source_ids={"video-cnn-brasil"},desktop_video_sources_v6_migrated=True)
    repository=VideoRepository(news_db,video_db,terms,youtube=NeverUsed(),website=FakeWebsite(),direct=FakeDirect(),editions=NeverUsed(),trechos=NeverUsed(),jarvis=NeverUsed())
    video_runner=RuntimeVideoRunner(repository,prefs)
    automation=AutomationService(AutomationSettings(prefs),NoopNewsRunner(),video_runner)
    controller=RuntimeUiController(paths=paths,prefs=prefs,news_db=news_db,video_db=video_db,proxy=FakeProxy(),startup=FakeStartup(),automation=automation,news_sources=(),video_sources=(),specialized_sources=(),default_video_source_ids={"video-cnn-brasil"},video_term_store=terms)
    assert controller.search_videos() is True
    wait_idle(automation); controller.sync_automation_state()
    stored=video_db.listAll(10)
    assert len(stored)==1 and stored[0].matchedTerm=="MARINHA"
    assert controller.state.videos and controller.state.videos[0].link.endswith("/videos/marinha-exercicio")
    assert stored[0].link in controller.state.new_video_links
    controller.close()
