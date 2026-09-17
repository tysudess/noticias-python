from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from pathlib import Path
import time
from typing import Callable, Iterable, Protocol

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.automation import AutomationService, AutomationSettings
from monitor_noticias.automation.models import LiveSearchProgress
from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import Demand, MediaSource, News, VideoItem, VideoSource
from monitor_noticias.networking.proxy import ProxyConfig, ProxySettings
from monitor_noticias.windows.startup import StartupManager

log = logging.getLogger(__name__)


class AutomationPort(Protocol):
    state: object
    settings: AutomationSettings
    def search_news(self, from_ms: int | None = None, to_ms: int | None = None) -> bool: ...
    def search_all_demands(self) -> bool: ...
    def search_videos(self, from_ms: int | None = None, to_ms: int | None = None) -> bool: ...
    def stop_news_search(self) -> None: ...
    def stop_video_search(self) -> None: ...
    def stop_all_searches(self) -> None: ...
    def close(self) -> None: ...


@dataclass(slots=True)
class UiState:
    news: list[News] = field(default_factory=list)
    videos: list[VideoItem] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    demands: list[Demand] = field(default_factory=list)
    new_news_links: set[str] = field(default_factory=set)
    new_video_links: set[str] = field(default_factory=set)
    news_progress: LiveSearchProgress = field(default_factory=LiveSearchProgress)
    video_progress: LiveSearchProgress = field(default_factory=LiveSearchProgress)
    news_busy: bool = False
    video_busy: bool = False
    status: str = "Pronto"
    video_status: str = "Pronto"
    last_news_duration_ms: int = 0
    last_video_duration_ms: int = 0
    unstable_video_sources: tuple[object, ...] = ()


class MainUiController:
    """Adaptador fino entre a UI PySide6 e os componentes já migrados.

    Não contém scraping, matching, SQL ou lógica de scheduling. A busca real só é
    habilitada quando um ``AutomationPort`` com runners reais é injetado.
    """

    def __init__(
        self,
        *,
        paths: AppPaths,
        prefs: SharedPreferences,
        news_db: NewsDb,
        video_db: VideoDb,
        proxy: ProxySettings,
        startup: StartupManager,
        automation: AutomationPort | None = None,
        news_sources: Iterable[MediaSource] = (),
        video_sources: Iterable[VideoSource] = (),
        specialized_sources: Iterable[MediaSource] = (),
    ) -> None:
        self.paths = paths
        self.prefs = prefs
        self.news_db = news_db
        self.video_db = video_db
        self.proxy = proxy
        self.startup = startup
        self.automation = automation
        self.news_sources = tuple(news_sources)
        self.video_sources = tuple(video_sources)
        self.specialized_sources = tuple(specialized_sources)
        self.state = UiState()
        self._listeners: list[Callable[[UiState], None]] = []
        self.refresh()

    @classmethod
    def create_default(
        cls,
        paths: AppPaths | None = None,
        *,
        automation: AutomationPort | None = None,
        news_sources: Iterable[MediaSource] = (),
        video_sources: Iterable[VideoSource] = (),
        specialized_sources: Iterable[MediaSource] = (),
    ) -> "MainUiController":
        paths = paths or AppPaths.discover()
        paths.ensure_runtime_dirs()
        prefs = SharedPreferences(paths.data / "prefs" / "monitor_prefs.properties")
        return cls(
            paths=paths,
            prefs=prefs,
            news_db=NewsDb(paths.news_db),
            video_db=VideoDb(paths.videos_db),
            proxy=ProxySettings(prefs, data_dir=paths.data),
            startup=StartupManager.default(),
            automation=automation,
            news_sources=news_sources,
            video_sources=video_sources,
            specialized_sources=specialized_sources,
        )

    @property
    def search_available(self) -> bool:
        return self.automation is not None

    def subscribe(self, callback: Callable[[UiState], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _emit(self) -> None:
        for callback in tuple(self._listeners):
            try:
                callback(self.state)
            except Exception:
                log.exception("Falha ao atualizar observador da UI")

    def refresh(self) -> None:
        self.state.news = self.news_db.listRecent(24, 1000)
        self.state.videos = self.video_db.listRecent(7, 1500)
        self.state.terms = self.news_db.listTerms()
        self.state.demands = self.news_db.listDemands()
        self.sync_automation_state()
        self._emit()

    def sync_automation_state(self) -> None:
        if self.automation is None:
            return
        state = self.automation.state
        self.state.news_progress = getattr(state, "newsProgress", self.state.news_progress)
        self.state.video_progress = getattr(state, "videoProgress", self.state.video_progress)
        self.state.news_busy = bool(getattr(state, "newsBusy", False))
        self.state.video_busy = bool(getattr(state, "videoBusy", False))
        self.state.status = str(getattr(state, "status", "Pronto"))
        self.state.video_status = str(getattr(state, "videoStatus", "Pronto"))
        self.state.last_news_duration_ms = int(getattr(state, "lastNewsSearchDurationMs", 0))
        self.state.last_video_duration_ms = int(getattr(state, "lastVideoSearchDurationMs", 0))
        self.state.unstable_video_sources = tuple(getattr(state, "unstableVideoSources", ()))

    def _missing_search_engine(self, kind: str) -> bool:
        message = (
            f"{kind}: integração de busca indisponível porque NewsRepository/VideoRepository "
            "de negócio ainda não foram migrados no repositório Python."
        )
        if kind == "Vídeos":
            self.state.video_status = message
        else:
            self.state.status = message
        self._emit()
        return False

    def search_news(self, from_ms: int | None = None, to_ms: int | None = None) -> bool:
        if self.automation is None:
            return self._missing_search_engine("Notícias")
        ok = self.automation.search_news(from_ms, to_ms)
        self.sync_automation_state(); self._emit()
        return ok

    def search_videos(self, from_ms: int | None = None, to_ms: int | None = None) -> bool:
        if self.automation is None:
            return self._missing_search_engine("Vídeos")
        ok = self.automation.search_videos(from_ms, to_ms)
        self.sync_automation_state(); self._emit()
        return ok

    def search_all_demands(self) -> bool:
        if self.automation is None:
            return self._missing_search_engine("Demandas")
        ok = self.automation.search_all_demands()
        self.sync_automation_state(); self._emit()
        return ok

    def search_demand(self, demand: Demand) -> bool:
        # O AutomationService migrado expõe busca de todas as demandas, não busca
        # individual. Não duplicamos NewsRepository dentro da UI.
        self.state.status = (
            f"Demanda {demand.id}: busca individual aguarda a porta do NewsRepository migrado."
        )
        self._emit()
        return False

    def stop_news_search(self) -> None:
        if self.automation is not None:
            self.automation.stop_news_search(); self.sync_automation_state(); self._emit()

    def stop_video_search(self) -> None:
        if self.automation is not None:
            self.automation.stop_video_search(); self.sync_automation_state(); self._emit()

    def stop_all_searches(self) -> None:
        if self.automation is not None:
            self.automation.stop_all_searches(); self.sync_automation_state(); self._emit()

    @staticmethod
    def period_last_hours(hours: int) -> tuple[int, int]:
        end = int(time.time() * 1000)
        return end - int(hours) * 60 * 60 * 1000, end

    @staticmethod
    def period_today() -> tuple[int, int]:
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp() * 1000), int(now.timestamp() * 1000)

    @staticmethod
    def parse_period(start_date: str, start_time: str, end_date: str, end_time: str) -> tuple[int, int] | None:
        try:
            start = datetime.strptime(f"{start_date.strip()} {start_time.strip()}", "%Y-%m-%d %H:%M")
            end = datetime.strptime(f"{end_date.strip()} {end_time.strip()}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        if end < start:
            return None
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    def add_term(self, term: str) -> None:
        self.news_db.addTerm(term); self.refresh()

    def remove_term(self, term: str) -> None:
        self.news_db.removeTerm(term); self.refresh()

    def add_demand(self, vehicle: str, subject: str) -> None:
        self.news_db.addDemand(vehicle, subject); self.refresh()

    def remove_demand(self, demand_id: int) -> None:
        self.news_db.removeDemand(demand_id); self.refresh()

    def clear_news_history(self) -> None:
        self.news_db.clearHistory(); self.refresh()

    def clear_video_history(self) -> None:
        self.video_db.clear(); self.refresh()

    @property
    def news_all_sources(self) -> bool:
        return self.prefs.get_boolean("desktop_news_all_sources", True)

    @news_all_sources.setter
    def news_all_sources(self, value: bool) -> None:
        self.prefs.update(desktop_news_all_sources=value)

    @property
    def selected_news_source_ids(self) -> set[str]:
        return self.prefs.get_string_set("desktop_news_source_ids", set()) or set()

    @selected_news_source_ids.setter
    def selected_news_source_ids(self, value: set[str]) -> None:
        self.prefs.update(desktop_news_source_ids=set(value))

    @property
    def selected_video_source_ids(self) -> set[str]:
        default = {source.id for source in self.video_sources}
        return self.prefs.get_string_set("desktop_video_source_ids", default) or set()

    @selected_video_source_ids.setter
    def selected_video_source_ids(self, value: set[str]) -> None:
        self.prefs.update(desktop_video_source_ids=set(value))

    def set_news_source(self, source_id: str, checked: bool) -> None:
        ids = self.selected_news_source_ids
        ids.add(source_id) if checked else ids.discard(source_id)
        self.selected_news_source_ids = ids; self._emit()

    def set_video_source(self, source_id: str, checked: bool) -> None:
        ids = self.selected_video_source_ids
        ids.add(source_id) if checked else ids.discard(source_id)
        self.selected_video_source_ids = ids; self._emit()

    @property
    def proxy_config(self) -> ProxyConfig:
        return self.proxy.load()

    def save_proxy(self, enabled: bool, host: str, port: int, username: str, password: str) -> ProxyConfig:
        cfg = self.proxy.save(enabled=enabled, host=host, port=port, username=username, password=password)
        self._emit(); return cfg

    def test_proxy(self) -> tuple[bool, str]:
        return self.proxy.test_connection()

    @property
    def automation_settings(self) -> AutomationSettings:
        if self.automation is not None:
            return self.automation.settings
        return AutomationSettings(self.prefs)

    @property
    def start_with_windows(self) -> bool:
        return self.prefs.get_boolean("desktop_start_with_windows", False)

    def set_start_with_windows(self, enabled: bool) -> bool:
        ok = self.startup.configure(enabled)
        # Preserva a preferência solicitada pelo usuário, como no Controller Kotlin.
        self.prefs.update(desktop_start_with_windows=enabled)
        self._emit(); return ok

    def close(self) -> None:
        if self.automation is not None:
            self.automation.close()
        self.news_db.close(); self.video_db.close()
