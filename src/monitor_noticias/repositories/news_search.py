from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from monitor_noticias.automation.models import LiveSearchProgress
from monitor_noticias.collectors.news.latest import ROUTES
from monitor_noticias.matching import demand_vehicle_matches, merge_news, source_matches_strict, story_key, subject_matches
from monitor_noticias.models import News
from .news_types import NewsSearchResult

DIRECT_SCAN_MAX_WINDOW_MS = 48 * 60 * 60 * 1000
DIRECT_SCAN_RECENCY_TOLERANCE_MS = 2 * 60 * 60 * 1000

def perform_news_search(repo, from_ms, to_ms, selected_sources, search_all_sources, on_update, cancel):
    terms = repo.db.listTerms() or repo.defaultTerms
    demands = [item for item in repo.db.listDemands() if item.active]
    started_at = repo.now_ms()
    if from_ms >= started_at - DIRECT_SCAN_MAX_WINDOW_MS and to_ms >= started_at - DIRECT_SCAN_RECENCY_TOLERANCE_MS:
        scope = repo.national_sources if search_all_sources else selected_sources
        direct_sources = list({source.id:source for source in scope if source.id in ROUTES}.values())
    else:
        direct_sources = []
    tasks = [(term, term, "Google Notícias") for term in terms]
    if not search_all_sources and selected_sources and len(selected_sources) <= 24:
        for offset in range(0, len(selected_sources), 8):
            batch = selected_sources[offset:offset+8]
            clause = " OR ".join(f'"{source.name}"' for source in batch)
            label = ", ".join(source.name for source in batch)[:70]
            tasks.extend((f'"{term}" ({clause})', term, label) for term in terms)

    history = repo.db.listNews(2000)
    by_link = {item.link:item for item in history}; by_story = {story_key(item):item for item in history}
    def historical(incoming: News) -> News:
        previous = by_link.get(incoming.link) or by_story.get(story_key(incoming))
        return incoming if previous is None else merge_news(previous, replace(incoming, link=previous.link, capturedAt=previous.capturedAt))

    collected: dict[str,News] = {}; new_links: list[str] = []
    errors = 0; completed = 0; total = len(tasks) + len(direct_sources)
    def progress(source, query, active=True):
        return LiveSearchProgress(active=active, kind="Notícias", startedAt=started_at, finishedAt=0 if active else repo.now_ms(), completed=completed, total=total, currentSource=source, currentQuery=query, found=len(collected), newCount=len(new_links), errors=errors)
    def emit(source, query, items: Iterable[News]=(), active=True):
        if on_update: on_update(progress(source, query, active), tuple(items))

    emit("Preparando", "")
    for query, term, source_label in tasks:
        if cancel: cancel()
        emit(source_label, term)
        fetched = repo.google.collect(query)
        if cancel: cancel()
        if fetched is None:
            errors += 1
        else:
            batch = []
            for base in fetched:
                if not (from_ms <= base.date <= to_ms): continue
                if not search_all_sources and not any(source_matches_strict(base.source, source) for source in selected_sources): continue
                body = f"{base.title} {base.snippet}"
                actual_terms = [value for value in terms if subject_matches(body, value)]
                demand = next((item for item in demands if demand_vehicle_matches(base.source, item.vehicle) and subject_matches(body, item.subject)), None)
                batch.append(historical(replace(base, important=demand is not None, demand=demand is not None, matchedTerm=", ".join(dict.fromkeys(actual_terms or [term])), matchedDemand=f"{demand.vehicle} • {demand.subject}" if demand else "", capturedAt=repo.now_ms())))
            merged_batch = []
            for incoming in {item.link:item for item in batch}.values():
                previous = collected.get(incoming.link)
                merged = incoming if previous is None else merge_news(previous, incoming)
                collected[merged.link] = merged; merged_batch.append(merged)
            inserted = repo.db.insertNews(merged_batch)
            new_links.extend(item.link for item in inserted if item.link not in new_links)
            if merged_batch: emit(source_label, term, merged_batch)
        completed += 1; emit(source_label, term)

    for source in direct_sources:
        if cancel: cancel()
        label = f"{source.name} • Últimas notícias"; emit(label, "Todos os termos")
        outcome = repo.latest.collect(source, terms, demands, from_ms, to_ms, repo.now_ms())
        if cancel: cancel()
        if not outcome.failed and outcome.items:
            inserts = []; updates = []
            for raw in outcome.items:
                incoming = historical(raw)
                duplicate = next((item for item in collected.values() if story_key(item) == story_key(incoming)), None)
                if duplicate is None:
                    collected[incoming.link] = incoming; inserts.append(incoming); updates.append(incoming)
                else:
                    merged = merge_news(duplicate, replace(incoming, link=duplicate.link, source=duplicate.source))
                    collected[duplicate.link] = merged; updates.append(merged)
            inserted = repo.db.insertNews(inserts)
            new_links.extend(item.link for item in inserted if item.link not in new_links)
            if updates: emit(label, "Todos os termos", updates)
        completed += 1; emit(label, "Todos os termos")

    items = tuple(sorted(collected.values(), key=lambda item:item.date, reverse=True))
    emit("Concluído", "", active=False)
    return NewsSearchResult(items, len(items), len(new_links), sum(1 for item in items if item.link in new_links and item.demand), errors, tuple(new_links))
