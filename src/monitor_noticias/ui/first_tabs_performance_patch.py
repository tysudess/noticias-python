from __future__ import annotations

import inspect
from typing import Any, Iterable

_PATCHED = False


def _value(obj: Any, name: str, default=None):
    return getattr(obj, name, default)


def news_row_key(item: Any) -> tuple:
    """Stable identity for a news row, preferring the canonical article URL."""
    link = str(_value(item, "link", "") or "")
    if link:
        return ("link", link)
    return ("id", _value(item, "id", 0))


def news_row_signature(item: Any) -> tuple:
    return tuple(
        _value(item, field, default)
        for field, default in (
            ("id", 0),
            ("link", ""),
            ("title", ""),
            ("source", ""),
            ("date", 0),
            ("snippet", ""),
            ("important", False),
            ("demand", False),
            ("matchedTerm", ""),
            ("matchedDemand", ""),
            ("capturedAt", 0),
        )
    )


def changed_news_rows(
    old_rows: Iterable[Any],
    old_new_links: set[str],
    new_rows: Iterable[Any],
    new_new_links: set[str],
) -> list[int] | None:
    """Return changed indices; None means insertion/removal/reordering needs reset."""
    old = list(old_rows)
    new = list(new_rows)
    if len(old) != len(new):
        return None
    if [news_row_key(item) for item in old] != [news_row_key(item) for item in new]:
        return None
    old_new = set(old_new_links or ())
    new_new = set(new_new_links or ())
    changed = []
    for index, (before, after) in enumerate(zip(old, new)):
        key = news_row_key(after)
        was_new = str(_value(before, "link", "") or "") in old_new
        is_new = str(_value(after, "link", "") or "") in new_new
        if news_row_signature(before) != news_row_signature(after) or was_new != is_new:
            changed.append(index)
    return changed


def video_row_signature(video: Any, is_new: bool) -> tuple:
    return tuple(
        _value(video, field, default)
        for field, default in (
            ("id", 0),
            ("link", ""),
            ("title", ""),
            ("sourceId", ""),
            ("sourceName", ""),
            ("publishedAt", 0),
            ("summary", ""),
            ("matchedTerm", ""),
            ("matchedDemand", ""),
            ("capturedAt", 0),
        )
    ) + (bool(is_new),)


def demand_row_signature(demand: Any) -> tuple:
    return tuple(
        _value(demand, field, default)
        for field, default in (
            ("id", 0),
            ("vehicle", ""),
            ("subject", ""),
            ("active", True),
            ("lastCheckedAt", 0),
            ("lastFoundCount", 0),
            ("lastNewCount", 0),
            ("lastError", ""),
        )
    )


def demand_progress_payload(
    *,
    started_at: int,
    now_ms: int,
    completed: int,
    total: int,
    vehicle: str = "",
    subject: str = "",
    found: int = 0,
    new_count: int = 0,
    errors: int = 0,
    active: bool = True,
) -> dict[str, Any]:
    """Payload kept pure so its semantics can be tested without starting Qt."""
    return {
        "active": bool(active),
        "kind": "Demandas",
        "startedAt": int(started_at),
        "finishedAt": 0 if active else int(now_ms),
        "completed": max(0, int(completed)),
        "total": max(0, int(total)),
        "currentSource": str(vehicle or ""),
        "currentQuery": str(subject or ""),
        "found": max(0, int(found)),
        "newCount": max(0, int(new_count)),
        "errors": max(0, int(errors)),
    }


def _install_news_model_diff() -> None:
    from PySide6.QtCore import Qt
    from monitor_noticias.ui.news_page import NewsModel

    original_set_rows = NewsModel.set_rows

    def optimized_set_rows(self, rows, new_links=()):
        new_rows = list(rows)
        links = set(new_links or ())
        if not getattr(self, "_v116_model_initialized", False):
            original_set_rows(self, new_rows, links)
            self._v116_model_initialized = True
            return

        changed = changed_news_rows(
            getattr(self, "rows", ()),
            set(getattr(self, "new_links", set()) or ()),
            new_rows,
            links,
        )
        if changed is None:
            original_set_rows(self, new_rows, links)
            return
        if not changed:
            return

        self.rows = new_rows
        self.new_links = links
        roles = [
            int(Qt.ItemDataRole.DisplayRole),
            int(self.NewsRole),
            int(self.NewRole),
        ]
        # Coalesce adjacent changed rows into the fewest Qt notifications.
        start = previous = changed[0]
        for index in changed[1:] + [None]:
            if index is not None and index == previous + 1:
                previous = index
                continue
            self.dataChanged.emit(self.index(start, 0), self.index(previous, 0), roles)
            if index is not None:
                start = previous = index

    NewsModel.set_rows = optimized_set_rows


def _install_progressive_news_refresh() -> None:
    from monitor_noticias.ui.runtime_controller import RuntimeUiController

    original_sync = RuntimeUiController.sync_automation_state

    def sync_with_incremental_news(self):
        original_sync(self)
        state = self.state
        if not state.news_busy:
            self._v116_last_news_progress_key = None
            return

        progress = state.news_progress
        key = (
            int(_value(progress, "completed", 0) or 0),
            int(_value(progress, "total", 0) or 0),
            str(_value(progress, "currentSource", "") or ""),
            str(_value(progress, "currentQuery", "") or ""),
            round(float(_value(progress, "fraction", 0.0) or 0.0), 4),
            int(_value(progress, "found", 0) or 0),
            int(_value(progress, "newCount", 0) or 0),
            int(_value(progress, "errors", 0) or 0),
        )
        if key == getattr(self, "_v116_last_news_progress_key", None):
            return
        self._v116_last_news_progress_key = key

        start = int(getattr(self, "_first_tabs_news_view_from_ms", 0) or 0)
        end = int(getattr(self, "_first_tabs_news_view_to_ms", 0) or 0)
        if start <= 0 or end <= 0:
            from monitor_noticias.ui.first_tabs_functional_patch import normalize_news_window
            start, end = normalize_news_window(None, None)
        # The repository inserts results per source/query. Reload only when the
        # progress signature changes; lock the shared SQLite connection against
        # concurrent inserts from the worker thread.
        with self.news_db._lock:
            self.state.news = self.news_db.listPeriod(start, end, 1000)

    RuntimeUiController.sync_automation_state = sync_with_incremental_news


def _install_video_list_diff() -> None:
    from monitor_noticias.ui.videos_page import VideosPage, _duration
    from monitor_noticias.ui.first_tabs_functional_patch import classify_execution

    original_init = VideosPage.__init__

    def init_with_exclusive_periods(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if getattr(self, "_v116_period_hooks_installed", False):
            return

        def select_fixed(selected, page=self):
            for option in getattr(page, "period_buttons", ()):
                option.setChecked(option is selected)
            custom = getattr(page, "custom", None)
            if custom is not None:
                custom.setChecked(False)

        for option in getattr(self, "period_buttons", ()):
            option.clicked.connect(lambda _checked=False, button=option: select_fixed(button))
        custom = getattr(self, "custom", None)
        if custom is not None:
            def custom_toggled(checked, page=self):
                if checked:
                    for option in getattr(page, "period_buttons", ()):
                        option.setChecked(False)
            custom.toggled.connect(custom_toggled)
        self._v116_period_hooks_installed = True

    def optimized_refresh(self, state):
        query = self.query.text().strip().lower()
        rows = [
            video for video in state.videos
            if not query or query in (
                f"{video.title} {video.sourceName} {video.matchedTerm} {video.matchedDemand}"
            ).lower()
        ]
        self.count.setText("Vídeos encontrados")
        self.shown.setText(f"{len(rows)} exibido(s)")
        self.run.setEnabled(not state.video_busy and self.controller.search_available)
        self.period_go.setEnabled(not state.video_busy and self.controller.search_available)
        self.stop.setVisible(state.video_busy)
        for button in list(getattr(self, "period_buttons", ()) or ()) + [getattr(self, "custom", None)]:
            if button is not None:
                button.setEnabled(not state.video_busy)
        for field in (
            getattr(self, "start_date", None),
            getattr(self, "start_time", None),
            getattr(self, "end_date", None),
            getattr(self, "end_time", None),
        ):
            if field is not None:
                field.setEnabled(not state.video_busy)

        progress = state.video_progress
        kind = classify_execution(
            state.video_status,
            progress,
            busy=state.video_busy,
            duration_ms=state.last_video_duration_ms,
            unstable_sources=state.unstable_video_sources,
        )
        fraction = max(0.0, min(1.0, float(_value(progress, "fraction", 0.0) or 0.0)))
        completed = int(_value(progress, "completed", 0) or 0)
        total = int(_value(progress, "total", 0) or 0)
        pct = round(fraction * 100)
        if total > 0 and completed >= total:
            pct = 100
        if kind == "idle" and not state.video_busy:
            pct = 0
            title = "Vídeos • aguardando primeira busca"
            detail = "Escolha um período e clique em Buscar vídeos agora."
            subtitle = "Nenhuma execução registrada nesta sessão."
        elif kind == "failure":
            title = "Vídeos • busca falhou"
            detail = state.video_status
            subtitle = state.video_status
        elif kind == "cancelled":
            title = "Vídeos • busca interrompida"
            detail = state.video_status
            subtitle = state.video_status
        elif kind == "partial":
            title = "Vídeos • concluída com falhas ou fontes instáveis"
            detail = state.video_status
            subtitle = state.video_status
        elif state.video_busy:
            title = "Vídeos • busca em andamento"
            current_source = str(_value(progress, "currentSource", "") or "Preparando")
            current_query = str(_value(progress, "currentQuery", "") or "consultas")
            detail = f"{current_source} • {current_query} • etapa {completed}/{total}" if total else f"{current_source} • {current_query}"
            subtitle = state.video_status or "Buscando vídeos..."
        else:
            title = "Vídeos • última execução concluída"
            detail = state.video_status or f"A busca foi concluída. {int(_value(progress, 'found', 0) or 0)} vídeo(s) encontrado(s)."
            subtitle = state.video_status or "Execução concluída."

        self.exec_title.setText(title)
        self.exec_sub.setText(subtitle)
        found = int(_value(progress, "found", 0) or 0)
        errors = int(_value(progress, "errors", 0) or 0)
        fresh = len(state.new_video_links)
        self.metrics["pct"].setText(f"{pct}%")
        self.metrics["found"].setText(str(found))
        self.metrics["new"].setText(str(fresh))
        self.metrics["errors"].setText(str(errors))
        self.metrics["steps"].setText(f"{completed}/{total}")
        self.metrics["time"].setText(_duration(state.last_video_duration_ms))
        self.progress.setValue(pct)
        self.detail.setText(detail)

        signature = tuple(
            video_row_signature(video, video.link in state.new_video_links)
            for video in rows
        )
        if signature != getattr(self, "_v116_video_list_signature", None):
            self._clear()
            for video in rows:
                self.items.insertWidget(
                    self.items.count() - 1,
                    self._card(video, video.link in state.new_video_links),
                )
            self.container.setMinimumHeight(max(120, len(rows) * 108))
            self._v116_video_list_signature = signature

    VideosPage.__init__ = init_with_exclusive_periods
    VideosPage.refresh = optimized_refresh


def _install_demands_list_diff() -> None:
    from PySide6.QtWidgets import QPushButton
    from monitor_noticias.ui.demands_page import DemandsPage
    from monitor_noticias.ui.first_tabs_functional_patch import classify_execution

    def optimized_refresh(self, state):
        progress = state.news_progress
        if state.news_busy:
            self.status_title.setText("Status: Em execução")
            if str(_value(progress, "kind", "")) == "Demandas" and int(_value(progress, "total", 0) or 0) > 0:
                completed = int(_value(progress, "completed", 0) or 0)
                total = int(_value(progress, "total", 0) or 0)
                position = min(total, completed + 1)
                source = str(_value(progress, "currentSource", "") or "Veículo não informado")
                subject = str(_value(progress, "currentQuery", "") or "Consulta em andamento")
                self.status_text.setText(
                    f"Demanda {position}/{total}: {source} • {subject}  |  "
                    f"{int(_value(progress, 'found', 0) or 0)} encontrados até agora  •  "
                    f"{int(_value(progress, 'newCount', 0) or 0)} novos  •  "
                    f"{int(_value(progress, 'errors', 0) or 0)} falhas"
                )
            else:
                self.status_text.setText(state.status or "Busca de notícias/demandas em andamento.")
        else:
            kind = classify_execution(state.status, progress, duration_ms=state.last_news_duration_ms)
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

        self.all.setEnabled(not state.news_busy and self.controller.search_available)
        total = len(state.demands)
        self.count.setText(f"{total} demanda cadastrada" if total == 1 else f"{total} demandas cadastradas")

        signature = tuple(demand_row_signature(item) for item in state.demands)
        if signature != getattr(self, "_v116_demand_list_signature", None):
            self._clear()
            widgets = {}
            for demand in state.demands:
                frame = self._item(demand)
                widgets[getattr(demand, "id", 0)] = frame
                self.items.insertWidget(self.items.count() - 1, frame)
            self.items_widget.setMinimumHeight(max(120, total * 96))
            self._v116_demand_widgets = widgets
            self._v116_demand_list_signature = signature

        for frame in getattr(self, "_v116_demand_widgets", {}).values():
            for button in frame.findChildren(QPushButton):
                if button.objectName() == "demandSearch":
                    button.setEnabled(not state.news_busy and self.controller.search_available)
                elif button.objectName() == "demandDelete":
                    button.setEnabled(not state.news_busy)

        demand_news = self._demand_news(state)
        self.results_model.set_rows(demand_news, state.new_news_links)
        found = len(demand_news)
        self.results_count.setText("1 resultado" if found == 1 else f"{found} resultados")
        if found:
            self.results_hint.setText(
                "Use os botões da matéria para abrir, compartilhar no WhatsApp, copiar o link direto ou enviar ao Extrator."
            )
        else:
            self.results_hint.setText(
                "As matérias encontradas nas buscas de demanda aparecerão aqui automaticamente."
            )

    DemandsPage.refresh = optimized_refresh


def _install_demand_progress() -> None:
    from monitor_noticias.automation.service import AutomationService
    from monitor_noticias.automation.models import DemandSweepResult
    from monitor_noticias.repositories.news_repository import NewsRepository
    from monitor_noticias.app.runtime_runners import RuntimeNewsRunner

    def repository_search_all_demands(self, *, cancel=None, on_progress=None):
        from monitor_noticias.automation.models import LiveSearchProgress

        active = [item for item in self.db.listDemands() if item.active]
        started_at = self.now_ms()
        all_items = []
        new_links = []
        found = fresh = errors = completed = 0
        total = len(active)

        def emit(current=None, *, finished=False):
            if on_progress is None:
                return
            payload = demand_progress_payload(
                started_at=started_at,
                now_ms=self.now_ms(),
                completed=completed,
                total=total,
                vehicle=getattr(current, "vehicle", "Concluído" if finished else ""),
                subject=getattr(current, "subject", ""),
                found=found,
                new_count=fresh,
                errors=errors,
                active=not finished,
            )
            on_progress(LiveSearchProgress(**payload))

        for demand in active:
            if cancel:
                cancel()
            # Publishes the current demand before the network request starts.
            emit(demand)
            result = self.search_demand(demand, cancel=cancel)
            found += int(getattr(result, "foundCount", 0) or 0)
            fresh += int(getattr(result, "newCount", 0) or 0)
            if getattr(result, "error", None) is not None:
                errors += 1
            all_items.extend(getattr(result, "items", ()) or ())
            new_links.extend(getattr(result, "newLinks", ()) or ())
            completed += 1

        items = tuple(sorted(
            {item.link: item for item in all_items}.values(),
            key=lambda item: item.date,
            reverse=True,
        ))
        unique_new_links = tuple(dict.fromkeys(new_links))
        emit(finished=True)
        return DemandSweepResult(total, found, fresh, errors, items, unique_new_links)

    def runtime_runner_search_all_demands(self, *, token, progress=None):
        token.raise_if_cancelled()
        return self.repository.search_all_demands(
            cancel=token.raise_if_cancelled,
            on_progress=progress,
        )

    def service_run_demands(self, token):
        from monitor_noticias.automation.service import AutomationCancelled

        started = self.clock.now_ms()

        def report(progress):
            self.state.newsProgress = progress
            if bool(getattr(progress, "active", False)) and int(getattr(progress, "total", 0) or 0) > 0:
                completed_count = int(getattr(progress, "completed", 0) or 0)
                total_count = int(getattr(progress, "total", 0) or 0)
                position = min(total_count, completed_count + 1)
                vehicle = str(getattr(progress, "currentSource", "") or "Veículo")
                subject = str(getattr(progress, "currentQuery", "") or "Assunto")
                self.state.status = (
                    f"Consultando demanda {position}/{total_count}: {vehicle} • {subject}  |  "
                    f"{int(getattr(progress, 'found', 0) or 0)} encontrados  •  "
                    f"{int(getattr(progress, 'newCount', 0) or 0)} novos  •  "
                    f"{int(getattr(progress, 'errors', 0) or 0)} falhas"
                )
            self._emit()

        try:
            token.raise_if_cancelled()
            runner_method = self.news_runner.search_all_demands
            try:
                parameters = inspect.signature(runner_method).parameters.values()
                supports_progress = any(
                    param.name == "progress" or param.kind == inspect.Parameter.VAR_KEYWORD
                    for param in parameters
                )
            except (TypeError, ValueError):
                supports_progress = False

            if supports_progress:
                result = runner_method(token=token, progress=report)
            else:
                result = runner_method(token=token)
            token.raise_if_cancelled()
            self.state.newNewsLinks = set(getattr(result, "newLinks", ()))
            self.state.status = (
                f"✓ {result.checkedCount} demanda(s)  •  {result.foundCount} resultado(s)  •  "
                f"{result.newCount} novo(s)  •  {result.errors} falha(s)"
            )
            if result.newCount > 0:
                self.notify("Demandas", f"{result.newCount} novo(s) resultado(s)")
        except AutomationCancelled:
            self.state.status = "⏹ Busca de demandas interrompida pelo usuário."
        except BaseException as exc:
            self.state.status = f"Falha nas demandas: {str(exc) or exc.__class__.__name__}"
            import logging
            logging.getLogger(__name__).exception("Falha na busca de demandas")
        finally:
            self.state.lastNewsSearchDurationMs = self.clock.now_ms() - started
            self.state.newsBusy = False
            self._emit()

    NewsRepository.search_all_demands = repository_search_all_demands
    RuntimeNewsRunner.search_all_demands = runtime_runner_search_all_demands
    AutomationService._run_demands = service_run_demands


def install_first_tabs_performance_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return

    # V115's functional patch is installed before this one by composition.py.
    _install_news_model_diff()
    _install_progressive_news_refresh()
    _install_video_list_diff()
    _install_demands_list_diff()
    _install_demand_progress()
    _PATCHED = True
