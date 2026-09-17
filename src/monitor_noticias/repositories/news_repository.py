from __future__ import annotations

from dataclasses import replace
import time
from typing import Callable, Iterable

from monitor_noticias.collectors.news import GoogleNewsCollector, NewsLatestCollector
from monitor_noticias.database import NewsDb
from monitor_noticias.database.default_terms import DEFAULT_MONITOR_TERMS
from monitor_noticias.matching import demand_vehicle_matches, merge_news, story_key, subject_matches
from monitor_noticias.models import Demand, MediaSource
from .news_search import perform_news_search
from .news_types import DemandSearchResult, DemandSweepResult, NewsSearchResult

CancelCheck = Callable[[], None]

class NewsRepository:
    """Orquestração equivalente ao NewsRepository Kotlin ativo."""
    def __init__(self, db: NewsDb, *, google: GoogleNewsCollector | None = None, latest: NewsLatestCollector | None = None, national_sources: Iterable[MediaSource] = ()) -> None:
        self.db = db
        self.google = google or GoogleNewsCollector()
        self.latest = latest or NewsLatestCollector()
        self.national_sources = tuple(national_sources)
        self.defaultTerms = list(DEFAULT_MONITOR_TERMS)

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    def search(self, selected_sources: Iterable[MediaSource] = (), search_all_sources: bool = True, *, on_update=None, cancel: CancelCheck | None = None) -> NewsSearchResult:
        now = self.now_ms()
        return perform_news_search(self, now - 86_400_000, now, tuple(selected_sources), search_all_sources, on_update, cancel)

    def search_period(self, from_ms: int, to_ms: int, selected_sources: Iterable[MediaSource] = (), search_all_sources: bool = True, *, on_update=None, cancel: CancelCheck | None = None) -> NewsSearchResult:
        return perform_news_search(self, from_ms, to_ms, tuple(selected_sources), search_all_sources, on_update, cancel)

    def search_demand(self, demand: Demand, *, cancel: CancelCheck | None = None) -> DemandSearchResult:
        if cancel: cancel()
        checked_at = self.now_ms()
        fetched = self.google.collect(demand.subject.strip())
        if cancel: cancel()
        if fetched is None:
            self.db.updateDemandStatus(demand.id, checked_at, 0, 0, "Falha na consulta")
            return DemandSearchResult(demand, (), 0, 0, "Falha na consulta")
        cutoff = checked_at - 86_400_000
        matched = []
        for news in fetched:
            if news.date < cutoff: continue
            if not demand_vehicle_matches(news.source, demand.vehicle): continue
            if not subject_matches(f"{news.title} {news.snippet}", demand.subject): continue
            matched.append(replace(news, important=True, demand=True, matchedTerm=demand.subject, matchedDemand=f"{demand.vehicle} • {demand.subject}", capturedAt=checked_at))
        matched = sorted({item.link:item for item in matched}.values(), key=lambda item:item.date, reverse=True)
        history = self.db.listNews(2000)
        by_link = {item.link:item for item in history}
        by_story = {story_key(item):item for item in history}
        stable = []
        for incoming in matched:
            previous = by_link.get(incoming.link) or by_story.get(story_key(incoming))
            stable.append(incoming if previous is None else merge_news(previous, replace(incoming, link=previous.link, capturedAt=previous.capturedAt)))
        stable = list({item.link:item for item in stable}.values())
        inserted = self.db.insertNews(stable)
        self.db.updateDemandStatus(demand.id, checked_at, len(stable), len(inserted), "")
        return DemandSearchResult(demand, tuple(stable), len(stable), len(inserted), None, tuple(item.link for item in inserted))

    def search_all_demands(self, *, cancel: CancelCheck | None = None) -> DemandSweepResult:
        active = [item for item in self.db.listDemands() if item.active]
        all_items = []; new_links = []; found = fresh = errors = 0
        for demand in active:
            if cancel: cancel()
            result = self.search_demand(demand, cancel=cancel)
            found += result.foundCount; fresh += result.newCount
            if result.error is not None: errors += 1
            all_items.extend(result.items); new_links.extend(result.newLinks)
        items = tuple(sorted({item.link:item for item in all_items}.values(), key=lambda item:item.date, reverse=True))
        return DemandSweepResult(len(active), found, fresh, errors, items, tuple(dict.fromkeys(new_links)))
