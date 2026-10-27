from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.models import News, VideoItem
from monitor_noticias.repositories import NewsRepository


class ExplodingGoogle:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def collect(self, query: str):
        self.queries.append(query)
        if query == "Falha":
            # A raw exception message may contain implementation details; the
            # status field should only store its type, not this message.
            raise RuntimeError("erro de transporte interno")
        return []


class NoLatest:
    pass


def test_news_db_serializes_concurrent_reads_and_writes(tmp_path: Path):
    with NewsDb(tmp_path / "news-concurrent.db") as db:
        def worker(index: int) -> None:
            db.addTerm(f"TERMO-{index}")
            db.insertNews(
                [
                    News(
                        title=f"Notícia {index}",
                        source="Fonte de teste",
                        date=1_800_000_000_000 + index,
                        link=f"https://example.test/news/{index}",
                        snippet=f"Conteúdo {index}",
                        capturedAt=1_800_000_000_000 + index,
                    )
                ]
            )
            # Exercise both query paths while other threads are inserting.
            db.listNews(limit=1000)
            db.listTerms()
            db.listDemands()

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(worker, range(80)))

        assert len(db.listNews(limit=1000)) == 80
        assert len([term for term in db.listTerms() if term.startswith("TERMO-")]) == 80


def test_video_db_serializes_concurrent_reads_and_writes(tmp_path: Path):
    with VideoDb(tmp_path / "videos-concurrent.db") as db:
        def worker(index: int) -> None:
            db.insert(
                [
                    VideoItem(
                        title=f"Vídeo {index}",
                        sourceId="source-test",
                        sourceName="Fonte de teste",
                        publishedAt=1_800_000_000_000 + index,
                        link=f"https://example.test/video/{index}",
                        summary=f"Resumo {index}",
                        capturedAt=1_800_000_000_000 + index,
                    )
                ]
            )
            db.listAll(limit=1000)
            db.listRecent(days=3650, limit=1000)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(worker, range(80)))

        assert len(db.listAll(limit=1000)) == 80


def test_unexpected_demand_failure_does_not_abort_remaining_demands(tmp_path: Path):
    db = NewsDb(tmp_path / "demands.db")
    try:
        # listDemands() is ordered by descending id, so the failure is visited
        # first and the successful empty result proves the sweep continued.
        db.addDemand("Veículo", "Sucesso")
        db.addDemand("Veículo", "Falha")
        google = ExplodingGoogle()
        repository = NewsRepository(db, google=google, latest=NoLatest())

        result = repository.search_all_demands()

        assert result.checkedCount == 2
        assert result.errors == 1
        assert google.queries == ["Falha", "Sucesso"]
        stored = {demand.subject: demand for demand in db.listDemands()}
        assert stored["Falha"].lastError == "Falha inesperada (RuntimeError)"
        assert stored["Sucesso"].lastError == ""
        assert stored["Sucesso"].lastCheckedAt > 0
    finally:
        db.close()
