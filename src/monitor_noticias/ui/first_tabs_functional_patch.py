from __future__ import annotations

from datetime import datetime
import re
import time
from typing import Any

DAY_MS = 24 * 60 * 60 * 1000
_PATCHED = False


def normalize_news_window(from_ms: int | None, to_ms: int | None, *, now_ms: int | None = None) -> tuple[int, int]:
    """Normalize the News tab's visible interval; default to the last 24 hours."""
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    if from_ms is None or to_ms is None:
        return now - DAY_MS, now
    start, end = int(from_ms), int(to_ms)
    return (end, start) if end < start else (start, end)


def local_day_start_ms(now: datetime | None = None) -> int:
    """Local timestamp for midnight today, respecting the system timezone."""
    current = now or datetime.now()
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


def classify_execution(status: str, progress: Any = None, *, busy: bool = False,
                       duration_ms: int = 0, unstable_sources=()) -> str:
    """Classify execution status so the UI does not falsely report success."""
    if busy:
        return "running"

    value = str(status or "").strip()
    lowered = value.casefold()

    if any(term in lowered for term in ("interrompid", "cancelad", "cancelamento")):
        return "cancelled"
    if (lowered.startswith(("falha", "erro")) or "falha na busca" in lowered
            or "erro na busca" in lowered or "exception" in lowered
            or "timed out" in lowered or "timeout" in lowered):
        return "failure"

    errors = int(getattr(progress, "errors", 0) or 0)
    if errors > 0 or tuple(unstable_sources or ()):
        return "partial"
    if re.search(r"\b([1-9]\d*)\s+(?:falha|falhas|erro|erros)\b", lowered):
        return "partial"

    finished_at = int(getattr(progress, "finishedAt", 0) or 0)
    started_at = int(getattr(progress, "startedAt", 0) or 0)
    completed = int(getattr(progress, "completed", 0) or 0)
    total = int(getattr(progress, "total", 0) or 0)
    if (not value or lowered in {"pronto", "ready", "nenhuma busca em andamento."}) \
            and not duration_ms and not finished_at and not started_at:
        return "idle"
    if duration_ms > 0 or finished_at > 0 or started_at > 0 or "✓" in value or "conclu" in lowered:
        if total > 0 and completed < total and not finished_at:
            return "partial"
        return "completed"
    return "idle"


def _news_list_period(self, from_ms: int, to_ms: int, limit: int = 1000):
    start, end = normalize_news_window(from_ms, to_ms)
    return self._queryNews("date>=? AND date<=?", (start, end), max(1, int(limit)))


def _news_count_period(self, from_ms: int, to_ms: int) -> int:
    start, end = normalize_news_window(from_ms, to_ms)
    with self._lock:
        row = self._db.raw.execute(
            "SELECT COUNT(*) FROM news WHERE date>=? AND date<=?", (start, end)
        ).fetchone()
    return int(row[0] if row else 0)


def _video_count_all(self) -> int:
    with self._lock:
        row = self._db.raw.execute("SELECT COUNT(*) FROM videos").fetchone()
    return int(row[0] if row else 0)


def _video_count_captured_period(self, from_ms: int, to_ms: int) -> int:
    start, end = normalize_news_window(from_ms, to_ms)
    with self._lock:
        row = self._db.raw.execute(
            "SELECT COUNT(*) FROM videos WHERE captured_at>=? AND captured_at<=?", (start, end)
        ).fetchone()
    return int(row[0] if row else 0)


def _state_for(state, kind: str):
    if kind == "news":
        return (str(getattr(state, "status", "") or ""), getattr(state, "news_progress", None),
                bool(getattr(state, "news_busy", False)), int(getattr(state, "last_news_duration_ms", 0) or 0), ())
    return (str(getattr(state, "video_status", "") or ""), getattr(state, "video_progress", None),
            bool(getattr(state, "video_busy", False)), int(getattr(state, "last_video_duration_ms", 0) or 0),
            tuple(getattr(state, "unstable_video_sources", ()) or ()))


def _install_database_helpers() -> None:
    from monitor_noticias.database.news_db import NewsDb
    from monitor_noticias.database.video_db import VideoDb
    if not hasattr(NewsDb, "listPeriod"):
        NewsDb.listPeriod = _news_list_period
    if not hasattr(NewsDb, "countPeriod"):
        NewsDb.countPeriod = _news_count_period
    if not hasattr(VideoDb, "countAll"):
        VideoDb.countAll = _video_count_all
    if not hasattr(VideoDb, "countCapturedPeriod"):
        VideoDb.countCapturedPeriod = _video_count_captured_period


def install_first_tabs_functional_patch() -> None:
    """Apply first-stage functional corrections before the UI is constructed."""
    global _PATCHED
    if _PATCHED:
        return
    _install_database_helpers()

    from monitor_noticias.ui.runtime_controller import RuntimeUiController
    from monitor_noticias.ui.home_page import HomePage
    from monitor_noticias.ui.news_page import NewsPage
    from monitor_noticias.ui.videos_page import VideosPage
    from monitor_noticias.ui.demands_page import DemandsPage
    from monitor_noticias.ui.main_window import MainWindow

    original_controller_init = RuntimeUiController.__init__
    original_controller_sync = RuntimeUiController.sync_automation_state
    original_controller_search_news = RuntimeUiController.search_news
    original_home_refresh = HomePage.refresh
    original_news_refresh = NewsPage.refresh
    original_video_refresh = VideosPage.refresh
    original_demands_refresh = DemandsPage.refresh
    original_progress_signature = MainWindow._progress_signature

    def controller_init(self, *args, **kwargs):
        start, end = normalize_news_window(None, None)
        self._first_tabs_news_view_from_ms = start
        self._first_tabs_news_view_to_ms = end
        original_controller_init(self, *args, **kwargs)

    def controller_refresh(self):
        start = int(getattr(self, "_first_tabs_news_view_from_ms", 0) or 0)
        end = int(getattr(self, "_first_tabs_news_view_to_ms", 0) or 0)
        if start <= 0 or end <= 0:
            start, end = normalize_news_window(None, None)
            self._first_tabs_news_view_from_ms = start
            self._first_tabs_news_view_to_ms = end
        self.state.news = self.news_db.listPeriod(start, end, 1000)
        self.state.videos = self.video_db.listPeriod(self._video_view_from_ms, self._video_view_to_ms, 1500)
        self.state.terms = self.news_db.listTerms()
        self.state.demands = self.news_db.listDemands()
        self.sync_automation_state()
        self._emit()

    def controller_search_news(self, from_ms=None, to_ms=None):
        # Don't change the selected window if a search is already running.
        if bool(getattr(getattr(self, "state", None), "news_busy", False)):
            return original_controller_search_news(self, from_ms, to_ms)
        start, end = normalize_news_window(from_ms, to_ms)
        self._first_tabs_news_view_from_ms = start
        self._first_tabs_news_view_to_ms = end
        self.state.news = self.news_db.listPeriod(start, end, 1000)
        return original_controller_search_news(self, from_ms, to_ms)

    def controller_sync(self):
        was_news = bool(getattr(self, "_last_news_busy", False))
        original_controller_sync(self)
        now_news = bool(getattr(self.state, "news_busy", False))
        if not was_news and now_news:
            status = str(getattr(self.state, "status", "") or "").casefold()
            # Auto searches and the Home shortcut use the standard 24-hour window.
            if "buscando notícias" in status and "no período" not in status:
                start, end = normalize_news_window(None, None)
                self._first_tabs_news_view_from_ms = start
                self._first_tabs_news_view_to_ms = end
                self.state.news = self.news_db.listPeriod(start, end, 1000)
        if was_news and not now_news:
            start = int(getattr(self, "_first_tabs_news_view_from_ms", 0) or 0)
            end = int(getattr(self, "_first_tabs_news_view_to_ms", 0) or 0)
            if start <= 0 or end <= 0:
                start, end = normalize_news_window(None, None)
            self.state.news = self.news_db.listPeriod(start, end, 1000)
            self._emit()

    def home_refresh(self, state):
        original_home_refresh(self, state)
        now = datetime.now()
        now_ms = int(now.timestamp() * 1000)
        news_count = self.controller.news_db.countPeriod(now_ms - DAY_MS, now_ms)
        video_count = self.controller.video_db.countAll()
        today_count = self.controller.video_db.countCapturedPeriod(local_day_start_ms(now), now_ms)
        specialized_count = len(getattr(self.controller, "specialized_sources", ()) or ())

        self.metric_values["news"].setText(str(news_count))
        self.metric_values["videos"].setText(str(video_count))
        self.metric_values["today"].setText(str(today_count))
        self.metric_values["sources"].setText(str(specialized_count))
        self.metric_subtitles["news"].setText("publicadas nas últimas 24h")
        self.metric_subtitles["videos"].setText("registros na base")
        self.metric_subtitles["today"].setText("capturados desde 00:00")
        self.metric_subtitles["sources"].setText(f"{specialized_count} especializadas")

        news = _state_for(state, "news")
        video = _state_for(state, "video")
        news_kind = classify_execution(news[0], news[1], busy=news[2], duration_ms=news[3], unstable_sources=news[4])
        video_kind = classify_execution(video[0], video[1], busy=video[2], duration_ms=video[3], unstable_sources=video[4])
        if state.news_busy or state.video_busy:
            active = []
            if state.news_busy:
                active.append("Notícias/Demandas")
            if state.video_busy:
                active.append("Vídeos")
            self.ready_title.setText("●  Status: Em execução")
            self.ready_text.setText("Busca em andamento: " + " e ".join(active) + ".")
        else:
            problems = []
            if news_kind in {"failure", "partial", "cancelled"}:
                problems.append("Notícias/Demandas: " + (news[0] or news_kind))
            if video_kind in {"failure", "partial", "cancelled"}:
                problems.append("Vídeos: " + (video[0] or video_kind))
            if problems:
                self.ready_title.setText("⚠  Status: Verificar última execução")
                self.ready_text.setText("  •  ".join(problems))
            elif getattr(self.controller.automation_settings, "automatic_monitoring", False):
                self.ready_title.setText("●  Status: Pronto")
                self.ready_text.setText("Monitoramento automático ativo; nenhuma busca em andamento.")
            else:
                self.ready_title.setText("○  Status: Pronto")
                self.ready_text.setText("Central pronta; monitoramento automático pausado.")

        # Before the first execution, don't show a fake 100% completion.
        if state.news_busy:
            label, progress = "Notícias", state.news_progress
        elif state.video_busy:
            label, progress = "Vídeos", state.video_progress
        else:
            candidates = []
            for name, progress0, duration_ms in (
                ("Notícias", state.news_progress, state.last_news_duration_ms),
                ("Vídeos", state.video_progress, state.last_video_duration_ms),
            ):
                started = int(getattr(progress0, "startedAt", 0) or 0)
                finished = int(getattr(progress0, "finishedAt", 0) or 0)
                if duration_ms > 0 or started or finished:
                    candidates.append((max(started, finished), name, progress0))
            if not candidates:
                self.search_progress_title.setText("Busca atual")
                self.search_progress_value.setText("0%")
                self.search_progress.setValue(0)
                self.search_progress_detail.setText("Nenhuma busca executada ainda.")
                label = progress = None
            else:
                _, label, progress = max(candidates, key=lambda item: item[0])
        if progress is not None:
            total = int(getattr(progress, "total", 0) or 0)
            done = int(getattr(progress, "completed", 0) or 0)
            pct = round(max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0)))) * 100)
            if total > 0 and done >= total:
                pct = 100
            self.search_progress_title.setText(("Busca atual • " if state.news_busy or state.video_busy else "Última execução • ") + label)
            self.search_progress_value.setText(f"{pct}%")
            self.search_progress.setValue(pct)
            status = state.status if label == "Notícias" else state.video_status
            current_source = getattr(progress, "currentSource", "") or getattr(progress, "currentQuery", "") or ""
            self.search_progress_detail.setText(status if not (state.news_busy or state.video_busy) else f"{current_source} • etapa {done}/{total}" if total else current_source)

    def news_refresh(self, state):
        original_news_refresh(self, state)
        for button in list(getattr(self, "period_buttons", ()) or ()) + [getattr(self, "custom", None)]:
            if button is not None:
                button.setEnabled(not state.news_busy)
        for field in (getattr(self, "start_date", None), getattr(self, "start_time", None),
                      getattr(self, "end_date", None), getattr(self, "end_time", None)):
            if field is not None:
                field.setEnabled(not state.news_busy)

        kind = classify_execution(state.status, state.news_progress, busy=state.news_busy,
                                  duration_ms=state.last_news_duration_ms)
        progress = state.news_progress
        completed = int(getattr(progress, "completed", 0) or 0)
        total = int(getattr(progress, "total", 0) or 0)
        pct = round(max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0)))) * 100)
        if total > 0 and completed >= total:
            pct = 100
        if kind == "idle" and not state.news_busy:
            self.exec_title.setText("Aguardando primeira busca")
            self.exec_sub.setText("Nenhuma execução registrada nesta sessão.")
            self.exec_detail.setText("Selecione o período e inicie uma busca.")
            self.progress.setValue(0)
            self.exec_pct.setText("0%")
            self.metric_labels["pct"].setText("0%")
        elif kind == "failure":
            self.exec_title.setText("Busca falhou")
            self.exec_sub.setText(state.status)
            self.exec_detail.setText(state.status)
        elif kind == "cancelled":
            self.exec_title.setText("Busca interrompida")
            self.exec_sub.setText(state.status)
            self.exec_detail.setText(state.status)
        elif kind == "partial":
            self.exec_title.setText("Busca concluída com falhas")
            self.exec_sub.setText(state.status)
            self.exec_detail.setText(state.status)
        elif kind == "completed" and not state.news_busy:
            self.exec_title.setText("Busca concluída")
            self.exec_sub.setText(state.status)
            self.exec_detail.setText(state.status or "Execução concluída.")
        if kind in {"failure", "cancelled", "partial", "completed"} and not state.news_busy:
            self.progress.setValue(pct)
            self.exec_pct.setText(f"{pct}%")
            self.metric_labels["pct"].setText(f"{pct}%")

    def video_refresh(self, state):
        original_video_refresh(self, state)
        for button in list(getattr(self, "period_buttons", ()) or ()) + [getattr(self, "custom", None)]:
            if button is not None:
                button.setEnabled(not state.video_busy)
        for field in (getattr(self, "start_date", None), getattr(self, "start_time", None),
                      getattr(self, "end_date", None), getattr(self, "end_time", None)):
            if field is not None:
                field.setEnabled(not state.video_busy)

        kind = classify_execution(state.video_status, state.video_progress, busy=state.video_busy,
                                  duration_ms=state.last_video_duration_ms,
                                  unstable_sources=state.unstable_video_sources)
        progress = state.video_progress
        completed = int(getattr(progress, "completed", 0) or 0)
        total = int(getattr(progress, "total", 0) or 0)
        pct = round(max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0)))) * 100)
        if total > 0 and completed >= total:
            pct = 100
        if kind == "idle" and not state.video_busy:
            self.exec_title.setText("Vídeos • aguardando primeira busca")
            self.exec_sub.setText("Nenhuma execução registrada nesta sessão.")
            self.detail.setText("Escolha um período e clique em Buscar vídeos agora.")
            self.progress.setValue(0)
            self.metrics["pct"].setText("0%")
        elif kind == "failure":
            self.exec_title.setText("Vídeos • busca falhou")
            self.exec_sub.setText(state.video_status)
            self.detail.setText(state.video_status)
        elif kind == "cancelled":
            self.exec_title.setText("Vídeos • busca interrompida")
            self.exec_sub.setText(state.video_status)
            self.detail.setText(state.video_status)
        elif kind == "partial":
            self.exec_title.setText("Vídeos • concluída com fontes instáveis")
            self.exec_sub.setText(state.video_status)
            self.detail.setText(state.video_status)
        elif kind == "completed" and not state.video_busy:
            self.exec_title.setText("Vídeos • última execução concluída")
            self.exec_sub.setText(state.video_status)
            self.detail.setText(state.video_status or "Execução concluída.")
        if kind in {"failure", "cancelled", "partial", "completed"} and not state.video_busy:
            self.progress.setValue(pct)
            self.metrics["pct"].setText(f"{pct}%")

        if not getattr(self, "_v115_period_hooks_installed", False):
            def select_fixed_period(selected, page=self):
                for option in getattr(page, "period_buttons", ()):
                    option.setChecked(option is selected)
                custom = getattr(page, "custom", None)
                if custom is not None:
                    custom.setChecked(False)
            for option in getattr(self, "period_buttons", ()):
                option.clicked.connect(lambda _checked=False, b=option: select_fixed_period(b))
            custom = getattr(self, "custom", None)
            if custom is not None:
                custom.toggled.connect(lambda checked, page=self: [
                    option.setChecked(False) for option in getattr(page, "period_buttons", ())
                ] if checked else None)
            self._v115_period_hooks_installed = True

    def demands_refresh(self, state):
        original_demands_refresh(self, state)
        if state.news_busy:
            self.status_title.setText("Status: Em execução")
            self.status_text.setText(state.status or "Busca de notícias/demandas em andamento.")
            return
        kind = classify_execution(state.status, state.news_progress, duration_ms=state.last_news_duration_ms)
        if kind == "failure":
            self.status_title.setText("Status: Falha na última operação")
            self.status_text.setText(state.status)
        elif kind == "cancelled":
            self.status_title.setText("Status: Operação interrompida")
            self.status_text.setText(state.status)
        elif kind == "partial":
            self.status_title.setText("Status: Concluída com falhas")
            self.status_text.setText(state.status)
        elif kind == "completed":
            self.status_title.setText("Status: Última operação concluída")
            self.status_text.setText(state.status)
        else:
            self.status_title.setText("Status: Pronto")
            self.status_text.setText("Sistema disponível para consultar e gerenciar demandas.")

    def progress_signature(progress):
        base = original_progress_signature(progress)
        if progress is None:
            return base
        return base + (
            bool(getattr(progress, "active", False)),
            int(getattr(progress, "startedAt", 0) or 0),
            int(getattr(progress, "finishedAt", 0) or 0),
            int(getattr(progress, "found", 0) or 0),
            int(getattr(progress, "newCount", 0) or 0),
            int(getattr(progress, "errors", 0) or 0),
        )

    RuntimeUiController.__init__ = controller_init
    RuntimeUiController.refresh = controller_refresh
    RuntimeUiController.search_news = controller_search_news
    RuntimeUiController.sync_automation_state = controller_sync
    HomePage.refresh = home_refresh
    NewsPage.refresh = news_refresh
    VideosPage.refresh = video_refresh
    DemandsPage.refresh = demands_refresh
    MainWindow._progress_signature = staticmethod(progress_signature)
    _PATCHED = True
