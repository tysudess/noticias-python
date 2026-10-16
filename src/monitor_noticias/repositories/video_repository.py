from __future__ import annotations

import time
from contextlib import ExitStack
from threading import RLock

from monitor_noticias.collectors.video import (
    DirectVideoPageResolver,
    GloboplayEditionCollector,
    GloboplayJarvisCollector,
    GloboplayTrechosCollector,
    WebsiteVideoCollector,
    YouTubeCollector,
)
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import VideoSource
from .video_performance import RegionalVideoSearchProfiler
from .video_search import perform_video_search
from .video_term_store import VideoTermStore
from .video_types import VideoSearchResult


class VideoRepository:
    """Composição do VideoRepository Python com cache e métricas de rede por busca."""

    HTTP_COLLECTOR_NAMES = ("youtube", "website", "direct", "editions", "trechos", "jarvis")

    def __init__(
        self,
        news_db: NewsDb,
        video_db: VideoDb,
        term_store: VideoTermStore,
        *,
        youtube=None,
        website=None,
        direct=None,
        editions=None,
        trechos=None,
        jarvis=None,
    ) -> None:
        self.news_db = news_db
        self.db = video_db
        self.term_store = term_store
        self.youtube = youtube or YouTubeCollector()
        self.website = website or WebsiteVideoCollector()
        self.direct = direct or DirectVideoPageResolver()
        self.editions = editions or GloboplayEditionCollector()
        self.trechos = trechos or GloboplayTrechosCollector()
        self.jarvis = jarvis or GloboplayJarvisCollector()
        self._search_lock = RLock()

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def _http_clients(self):
        seen = set()
        for name in self.HTTP_COLLECTOR_NAMES:
            collector = getattr(self, name, None)
            http = getattr(collector, "http", None)
            if http is None or id(http) in seen:
                continue
            if callable(getattr(http, "request_cache_scope", None)):
                seen.add(id(http))
                yield http

    def search(
        self,
        sources: list[VideoSource],
        *,
        from_ms: int | None = None,
        to_ms: int | None = None,
        on_update=None,
        cancel=None,
    ) -> VideoSearchResult:
        # O cache é descartado ao sair desta busca e é local à thread. Não é
        # compartilhado com a varredura de notícias nem persiste dados no disco.
        with self._search_lock, ExitStack() as stack:
            stats_list = [
                stack.enter_context(http.request_cache_scope())
                for http in self._http_clients()
            ]
            profiler = RegionalVideoSearchProfiler(sources, stats_list, on_update)
            try:
                return perform_video_search(
                    self,
                    sources,
                    from_ms,
                    to_ms,
                    profiler,
                    cancel,
                )
            finally:
                profiler.finish()
