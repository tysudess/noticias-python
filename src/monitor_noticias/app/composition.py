from __future__ import annotations

from dataclasses import dataclass

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.app.runtime_runners import RuntimeNewsRunner, RuntimeVideoRunner
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.collectors.news import GoogleNewsCollector, NewsLatestCollector
from monitor_noticias.collectors.video import DirectVideoPageResolver, GloboplayEditionCollector, GloboplayJarvisCollector, GloboplayTrechosCollector, WebsiteVideoCollector, YouTubeCollector
from monitor_noticias.collectors.video.catalog import DEFAULT_IDS, VIDEO_SOURCES
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.networking import HttpClient
from monitor_noticias.networking.proxy import ProxySettings
from monitor_noticias.repositories import NewsRepository, VideoRepository, VideoTermStore
from monitor_noticias.ui.catalog import NATIONAL as NEWS_NATIONAL, NEWS_SOURCES, SPECIALIZED
from monitor_noticias.ui.runtime_controller import RuntimeUiController
from monitor_noticias.windows.startup import StartupManager

@dataclass(slots=True)
class AppContainer:
    paths: AppPaths
    prefs: SharedPreferences
    news_db: NewsDb
    video_db: VideoDb
    proxy: ProxySettings
    news_repository: NewsRepository
    video_repository: VideoRepository
    video_term_store: VideoTermStore
    automation: AutomationService
    controller: RuntimeUiController

    @classmethod
    def build(cls, paths: AppPaths | None = None) -> "AppContainer":
        paths = paths or AppPaths.discover(); paths.ensure_runtime_dirs()
        prefs = SharedPreferences(paths.data / "prefs" / "monitor_prefs.properties")
        news_db = NewsDb(paths.news_db); video_db = VideoDb(paths.videos_db)
        proxy = ProxySettings(prefs, data_dir=paths.data); proxy.migrate_host()
        http = HttpClient.from_proxy_settings(proxy)
        news_repository = NewsRepository(news_db, google=GoogleNewsCollector(http), latest=NewsLatestCollector(http), national_sources=NEWS_NATIONAL)
        video_terms = VideoTermStore(prefs)
        video_repository = VideoRepository(news_db, video_db, video_terms,
            youtube=YouTubeCollector(http), website=WebsiteVideoCollector(http), direct=DirectVideoPageResolver(http),
            editions=GloboplayEditionCollector(http), trechos=GloboplayTrechosCollector(http), jarvis=GloboplayJarvisCollector(http))
        news_runner = RuntimeNewsRunner(news_repository, prefs, NEWS_SOURCES)
        video_runner = RuntimeVideoRunner(video_repository, prefs)
        automation = AutomationService(AutomationSettings(prefs), news_runner, video_runner)
        controller = RuntimeUiController(paths=paths,prefs=prefs,news_db=news_db,video_db=video_db,proxy=proxy,startup=StartupManager.default(),automation=automation,news_sources=NEWS_SOURCES,video_sources=VIDEO_SOURCES,specialized_sources=SPECIALIZED,default_video_source_ids=DEFAULT_IDS,video_term_store=video_terms)
        automation.start()
        return cls(paths,prefs,news_db,video_db,proxy,news_repository,video_repository,video_terms,automation,controller)

    def close(self) -> None:
        self.controller.close()
