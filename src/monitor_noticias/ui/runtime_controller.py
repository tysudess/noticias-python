from __future__ import annotations

from monitor_noticias.repositories import VideoTermStore
from .controller import MainUiController

class RuntimeUiController(MainUiController):
    """Controller de produção: somente ponte UI ↔ serviços reais."""
    def __init__(self, *, default_video_source_ids, video_term_store: VideoTermStore, **kwargs) -> None:
        self.default_video_source_ids=set(default_video_source_ids); self.video_term_store=video_term_store
        self.video_terms=[]; self._last_news_busy=False; self._last_video_busy=False; self._runtime_closed=False
        super().__init__(**kwargs)
        self.video_terms=self.video_term_store.load(self.state.terms)

    @property
    def selected_video_source_ids(self) -> set[str]:
        return self.prefs.get_string_set("desktop_video_source_ids",set(self.default_video_source_ids)) or set()
    @selected_video_source_ids.setter
    def selected_video_source_ids(self,value:set[str]) -> None:
        self.prefs.update(desktop_video_source_ids=set(value))

    def search_demand(self,demand) -> bool:
        if self.automation is None: return self._missing_search_engine("Demandas")
        ok=self.automation.search_demand(demand); self.sync_automation_state(); self._emit(); return ok

    def add_video_term(self,value:str) -> None:
        self.video_terms=self.video_term_store.add(value,self.news_db.listTerms()); self._emit()
    def remove_video_term(self,value:str) -> None:
        self.video_terms=self.video_term_store.remove(value,self.news_db.listTerms()); self._emit()

    def sync_automation_state(self) -> None:
        was_news=self._last_news_busy; was_video=self._last_video_busy
        super().sync_automation_state()
        if self.automation is None: return
        state=self.automation.state
        self.state.new_news_links=set(getattr(state,"newNewsLinks",set()))
        self.state.new_video_links=set(getattr(state,"newVideoLinks",set()))
        now_news=self.state.news_busy; now_video=self.state.video_busy
        if (was_news and not now_news) or (was_video and not now_video):
            self.state.news=self.news_db.listRecent(24,1000); self.state.videos=self.video_db.listRecent(7,1500)
            self.state.terms=self.news_db.listTerms(); self.state.demands=self.news_db.listDemands(); self.video_terms=self.video_term_store.load(self.state.terms)
        self._last_news_busy=now_news; self._last_video_busy=now_video

    def set_notifier(self, notifier) -> None:
        if self.automation is not None: self.automation.notify=notifier

    def close(self) -> None:
        if self._runtime_closed: return
        self._runtime_closed=True
        super().close()
