from __future__ import annotations

import time

from monitor_noticias.collectors.video import DirectVideoPageResolver, GloboplayEditionCollector, GloboplayJarvisCollector, GloboplayTrechosCollector, WebsiteVideoCollector, YouTubeCollector
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import VideoSource
from .video_search import perform_video_search
from .video_term_store import VideoTermStore
from .video_types import VideoSearchResult

class VideoRepository:
    """Composição do VideoRepository Kotlin usando os coletores já migrados."""
    def __init__(self, news_db: NewsDb, video_db: VideoDb, term_store: VideoTermStore, *, youtube=None, website=None, direct=None, editions=None, trechos=None, jarvis=None) -> None:
        self.news_db = news_db
        self.db = video_db
        self.term_store = term_store
        self.youtube = youtube or YouTubeCollector()
        self.website = website or WebsiteVideoCollector()
        self.direct = direct or DirectVideoPageResolver()
        self.editions = editions or GloboplayEditionCollector()
        self.trechos = trechos or GloboplayTrechosCollector()
        self.jarvis = jarvis or GloboplayJarvisCollector()

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def search(self, sources: list[VideoSource], *, from_ms: int | None = None, to_ms: int | None = None, on_update=None, cancel=None) -> VideoSearchResult:
        return perform_video_search(self, sources, from_ms, to_ms, on_update, cancel)
