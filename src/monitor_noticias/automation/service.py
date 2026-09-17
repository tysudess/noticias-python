from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
import logging
import threading
from typing import Callable, Protocol

from monitor_noticias.models import Demand
from .clock import SystemClock
from .models import DemandSweepResult, LiveSearchProgress, SearchResult, VideoSearchResult
from .settings import AutomationSettings

log = logging.getLogger(__name__)

class AutomationCancelled(Exception):
    pass

class CancellationToken:
    def __init__(self) -> None: self._event = threading.Event()
    def cancel(self) -> None: self._event.set()
    @property
    def cancelled(self) -> bool: return self._event.is_set()
    def raise_if_cancelled(self) -> None:
        if self.cancelled: raise AutomationCancelled("Interrompida pelo usuário")

ProgressCallback = Callable[[LiveSearchProgress], None]

class NewsRunner(Protocol):
    def search_news(self, *, token: CancellationToken, progress: ProgressCallback, from_ms: int | None = None, to_ms: int | None = None): ...
    def search_demand(self, demand: Demand, *, token: CancellationToken): ...
    def search_all_demands(self, *, token: CancellationToken): ...

class VideoRunner(Protocol):
    def search_videos(self, *, token: CancellationToken, progress: ProgressCallback, from_ms: int | None = None, to_ms: int | None = None): ...

@dataclass(slots=True)
class AutomationState:
    newsProgress: LiveSearchProgress = LiveSearchProgress()
    videoProgress: LiveSearchProgress = LiveSearchProgress()
    newsBusy: bool = False
    videoBusy: bool = False
    status: str = "Pronto"
    videoStatus: str = "Pronto"
    lastNewsSearchDurationMs: int = 0
    lastVideoSearchDurationMs: int = 0
    unstableVideoSources: tuple[object, ...] = ()
    newNewsLinks: set[str] = field(default_factory=set)
    newVideoLinks: set[str] = field(default_factory=set)

class AutomationService:
    """Motor automático do DesktopControllerV5, com lanes independentes news/video."""
    LOOP_DELAY_SECONDS = 30.0

    def __init__(self, settings: AutomationSettings, news_runner: NewsRunner, video_runner: VideoRunner, *, clock: SystemClock | None = None, notify: Callable[[str, str], None] | None = None, on_state: Callable[[AutomationState], None] | None = None) -> None:
        self.settings = settings; self.news_runner = news_runner; self.video_runner = video_runner
        self.clock = clock or SystemClock(); self.notify = notify or (lambda _title,_body: None); self.on_state = on_state or (lambda _state: None)
        self.state = AutomationState(); self._lock = threading.RLock()
        self._news_executor = ThreadPoolExecutor(max_workers=1,thread_name_prefix="monitor-news")
        self._video_executor = ThreadPoolExecutor(max_workers=1,thread_name_prefix="monitor-video")
        self._news_future: Future[object] | None = None; self._video_future: Future[object] | None = None
        self._news_token: CancellationToken | None = None; self._video_token: CancellationToken | None = None
        self._stop = threading.Event(); self._loop_thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._loop_thread and self._loop_thread.is_alive(): return
            self._stop.clear(); self._loop_thread = threading.Thread(target=self._loop,name="monitor-automation",daemon=True); self._loop_thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set(): self.tick(); self._stop.wait(self.LOOP_DELAY_SECONDS)

    def tick(self) -> None:
        if not self.settings.automatic_monitoring: return
        now = self.clock.now_ms()
        news_due = self.settings.news_automatic and now-self.settings.last_news_auto_at >= self.settings.news_interval_minutes*60_000
        demand_due = self.settings.demand_automatic and now-self.settings.last_demand_auto_at >= self.settings.demand_interval_minutes*60_000
        if not self.state.newsBusy and news_due:
            self.settings.mark_news_triggered(now); self.search_news()
        elif not self.state.newsBusy and demand_due:
            self.settings.mark_demand_triggered(now); self.search_all_demands()
        if self.settings.video_automatic and not self.state.videoBusy:
            dt=self.clock.local_datetime(); slot=dt.strftime("%H:%M")
            if slot in self.settings.video_schedule_times:
                key=dt.strftime("%Y-%m-%d-%H-%M")
                if self.settings.last_video_slot != key:
                    self.settings.mark_video_triggered(now,key); self.search_videos()

    def _emit(self) -> None: self.on_state(self.state)

    def search_news(self, from_ms: int | None = None, to_ms: int | None = None) -> bool:
        with self._lock:
            if self.state.newsBusy: return False
            self.state.newsBusy=True; self.state.newNewsLinks.clear(); self.state.status="Buscando notícias..." if from_ms is None else "Buscando notícias no período..."
            token=CancellationToken(); self._news_token=token; self._emit(); self._news_future=self._news_executor.submit(self._run_news,token,from_ms,to_ms); return True

    def _run_news(self, token, from_ms, to_ms) -> None:
        started=self.clock.now_ms()
        try:
            result=self.news_runner.search_news(token=token,progress=self._news_progress,from_ms=from_ms,to_ms=to_ms); token.raise_if_cancelled()
            self.state.newNewsLinks=set(getattr(result,"newLinks",()))
            self.state.status=f"✓ {result.newCount} nova(s) notícia(s) • {result.newDemandCount} demanda(s) • {result.errors} falha(s)"
            if result.newCount+result.newDemandCount>0: self.notify("Monitor de Notícias",self.state.status)
        except AutomationCancelled: self.state.status="⏹ Busca de notícias interrompida pelo usuário."
        except BaseException as exc: self.state.status=f"Falha na busca de notícias: {str(exc) or exc.__class__.__name__}"; log.exception("Falha na busca de notícias")
        finally: self.state.lastNewsSearchDurationMs=self.clock.now_ms()-started; self.state.newsBusy=False; self._emit()

    def search_demand(self, demand: Demand) -> bool:
        with self._lock:
            if self.state.newsBusy: return False
            self.state.newsBusy=True; self.state.newNewsLinks.clear(); self.state.status=f"Buscando demanda: {demand.vehicle} • {demand.subject}"
            token=CancellationToken(); self._news_token=token; self._emit(); self._news_future=self._news_executor.submit(self._run_demand,token,demand); return True

    def _run_demand(self, token, demand) -> None:
        started=self.clock.now_ms()
        try:
            result=self.news_runner.search_demand(demand,token=token); token.raise_if_cancelled(); self.state.newNewsLinks=set(getattr(result,"newLinks",()))
            self.state.status=f"✓ Demanda: {result.foundCount} resultado(s), {result.newCount} novo(s)"
            if result.newCount>0: self.notify("Monitor de Notícias",self.state.status)
        except AutomationCancelled: self.state.status="⏹ Busca de notícias interrompida pelo usuário."
        except BaseException as exc: self.state.status=f"Falha na demanda: {str(exc) or exc.__class__.__name__}"; log.exception("Falha na demanda")
        finally: self.state.lastNewsSearchDurationMs=self.clock.now_ms()-started; self.state.newsBusy=False; self._emit()

    def search_all_demands(self) -> bool:
        with self._lock:
            if self.state.newsBusy: return False
            self.state.newsBusy=True; self.state.newNewsLinks.clear(); self.state.status="Buscando todas as demandas..."
            token=CancellationToken(); self._news_token=token; self._emit(); self._news_future=self._news_executor.submit(self._run_demands,token); return True

    def _run_demands(self, token) -> None:
        started=self.clock.now_ms()
        try:
            result=self.news_runner.search_all_demands(token=token); token.raise_if_cancelled(); self.state.newNewsLinks=set(getattr(result,"newLinks",()))
            self.state.status=f"✓ {result.checkedCount} demanda(s) • {result.foundCount} resultado(s) • {result.newCount} novo(s)"
            if result.newCount>0: self.notify("Demandas",f"{result.newCount} novo(s) resultado(s)")
        except AutomationCancelled: self.state.status="⏹ Busca de demandas interrompida pelo usuário."
        except BaseException as exc: self.state.status=f"Falha nas demandas: {str(exc) or exc.__class__.__name__}"; log.exception("Falha nas demandas")
        finally: self.state.lastNewsSearchDurationMs=self.clock.now_ms()-started; self.state.newsBusy=False; self._emit()

    def search_videos(self, from_ms: int | None = None, to_ms: int | None = None) -> bool:
        with self._lock:
            if self.state.videoBusy: return False
            self.state.videoBusy=True; self.state.newVideoLinks.clear(); self.state.videoStatus="Buscando vídeos..." if from_ms is None else "Buscando vídeos no período..."
            token=CancellationToken(); self._video_token=token; self._emit(); self._video_future=self._video_executor.submit(self._run_videos,token,from_ms,to_ms); return True

    def _run_videos(self, token, from_ms, to_ms) -> None:
        started=self.clock.now_ms()
        try:
            result=self.video_runner.search_videos(token=token,progress=self._video_progress,from_ms=from_ms,to_ms=to_ms); token.raise_if_cancelled()
            self.state.newVideoLinks=set(getattr(result,"newLinks",())); self.state.unstableVideoSources=tuple(result.unstableSources)
            self.state.videoStatus=f"✓ {result.relevantCount} relevante(s) • {result.newRelevantCount} novo(s) • {result.errors} fonte(s) instável(is)"
            if result.newRelevantCount>0: self.notify("Novos vídeos",f"{result.newRelevantCount} vídeo(s) relevante(s)")
        except AutomationCancelled: self.state.videoStatus="⏹ Busca de vídeos interrompida pelo usuário."
        except BaseException as exc: self.state.videoStatus=f"Falha na busca de vídeos: {str(exc) or exc.__class__.__name__}"; log.exception("Falha na busca de vídeos")
        finally: self.state.lastVideoSearchDurationMs=self.clock.now_ms()-started; self.state.videoBusy=False; self._emit()

    def _news_progress(self, progress): self.state.newsProgress=progress; self._emit()
    def _video_progress(self, progress): self.state.videoProgress=progress; self._emit()
    def stop_news_search(self) -> None:
        with self._lock:
            if self.state.newsBusy and self._news_token is not None: self.state.status="⏹ Interrompendo busca de notícias/demandas..."; self._news_token.cancel(); self._emit()
    def stop_video_search(self) -> None:
        with self._lock:
            if self.state.videoBusy and self._video_token is not None: self.state.videoStatus="⏹ Interrompendo busca de vídeos..."; self._video_token.cancel(); self._emit()
    def stop_all_searches(self) -> None: self.stop_news_search(); self.stop_video_search()
    def close(self) -> None:
        self._stop.set(); self.stop_all_searches()
        if self._loop_thread and self._loop_thread.is_alive(): self._loop_thread.join(timeout=1.0)
        self._news_executor.shutdown(wait=False,cancel_futures=True); self._video_executor.shutdown(wait=False,cancel_futures=True)
