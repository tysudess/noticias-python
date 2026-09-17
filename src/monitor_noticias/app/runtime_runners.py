from __future__ import annotations

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.collectors.video.catalog import DEFAULT_IDS, selected as select_video_sources
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS
from monitor_noticias.models import Demand, MediaSource
from monitor_noticias.repositories import NewsRepository, VideoRepository

class RuntimeNewsRunner:
    def __init__(self, repository: NewsRepository, prefs: SharedPreferences, news_sources) -> None:
        self.repository=repository; self.prefs=prefs; self.by_id={source.id:source for source in news_sources}
    def _selection(self):
        all_sources=self.prefs.get_boolean("desktop_news_all_sources",True)
        if all_sources: return (), True
        ids=self.prefs.get_string_set("desktop_news_source_ids",set()) or set()
        return tuple(self.by_id[id_] for id_ in ids if id_ in self.by_id), False
    def search_news(self, *, token, progress, from_ms=None, to_ms=None):
        selected,all_sources=self._selection(); token.raise_if_cancelled()
        callback=lambda state,_items=(): progress(state)
        if from_ms is None or to_ms is None:
            return self.repository.search(selected,all_sources,on_update=callback,cancel=token.raise_if_cancelled)
        return self.repository.search_period(from_ms,to_ms,selected,all_sources,on_update=callback,cancel=token.raise_if_cancelled)
    def search_demand(self,demand:Demand,*,token):
        return self.repository.search_demand(demand,cancel=token.raise_if_cancelled)
    def search_all_demands(self,*,token):
        return self.repository.search_all_demands(cancel=token.raise_if_cancelled)

class RuntimeVideoRunner:
    def __init__(self, repository: VideoRepository, prefs: SharedPreferences) -> None:
        self.repository=repository; self.prefs=prefs; self._migrate_desktop_extras()
    def _migrate_desktop_extras(self):
        key="desktop_video_sources_v6_migrated"
        if self.prefs.get_boolean(key,False): return
        current=self.prefs.get_string_set("desktop_video_source_ids",set(DEFAULT_IDS)) or set()
        current |= {source.id for source in DESKTOP_VIDEO_EXTRAS}
        self.prefs.update(desktop_video_source_ids=current, **{key:True})
    def selected_ids(self):
        return self.prefs.get_string_set("desktop_video_source_ids",set(DEFAULT_IDS)) or set()
    def search_videos(self, *, token, progress, from_ms=None, to_ms=None):
        token.raise_if_cancelled(); sources=select_video_sources(self.selected_ids())
        callback=lambda state,_items=(): progress(state)
        return self.repository.search(sources,from_ms=from_ms,to_ms=to_ms,on_update=callback,cancel=token.raise_if_cancelled)
