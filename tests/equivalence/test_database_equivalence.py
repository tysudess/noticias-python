from pathlib import Path
import sqlite3

import pytest

from monitor_noticias.database import NewsDb, VideoDb
from monitor_noticias.database.default_terms import DEFAULT_MONITOR_TERMS
from monitor_noticias.models import Demand, News, VideoItem


def table_columns(path: Path, table: str) -> list[tuple]:
    con = sqlite3.connect(path)
    try:
        return [tuple(row) for row in con.execute(f"PRAGMA table_info({table})")]
    finally:
        con.close()


def test_news_schema_and_seed_exact(tmp_path: Path):
    path = tmp_path / "news.db"
    with NewsDb(path) as db:
        assert db.listTerms() == sorted(DEFAULT_MONITOR_TERMS, key=str.lower)

    cols = {row[1]: (row[2], row[3], row[4], row[5]) for row in table_columns(path, "news")}
    assert cols == {
        "id": ("INTEGER", 0, None, 1),
        "title": ("TEXT", 1, None, 0),
        "source": ("TEXT", 0, None, 0),
        "date": ("INTEGER", 1, None, 0),
        "link": ("TEXT", 0, None, 0),
        "snippet": ("TEXT", 0, None, 0),
        "important": ("INTEGER", 0, "0", 0),
        "demand": ("INTEGER", 0, "0", 0),
        "matched_term": ("TEXT", 0, "''", 0),
        "matched_demand": ("TEXT", 0, "''", 0),
        "captured_at": ("INTEGER", 1, "0", 0),
    }


def test_news_runtime_migration_matches_kotlin(tmp_path: Path):
    path = tmp_path / "news.db"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE news(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,"
        "source TEXT,date INTEGER NOT NULL,link TEXT UNIQUE,snippet TEXT,"
        "important INTEGER DEFAULT 0,demand INTEGER DEFAULT 0)"
    )
    con.execute("CREATE TABLE terms(id INTEGER PRIMARY KEY AUTOINCREMENT,term TEXT UNIQUE NOT NULL)")
    con.execute(
        "CREATE TABLE demands(id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "vehicle TEXT NOT NULL,subject TEXT NOT NULL,active INTEGER DEFAULT 1)"
    )
    con.execute(
        "INSERT INTO news(title,source,date,link) VALUES(?,?,?,?)",
        ("Título", "Fonte", 123456, "https://example.com/a"),
    )
    con.commit()
    con.close()

    with NewsDb(path):
        pass

    news_cols = {row[1] for row in table_columns(path, "news")}
    demand_cols = {row[1] for row in table_columns(path, "demands")}
    assert {"matched_term", "matched_demand", "captured_at"} <= news_cols
    assert {"last_checked_at", "last_found_count", "last_new_count", "last_error"} <= demand_cols
    con = sqlite3.connect(path)
    try:
        captured = con.execute("SELECT captured_at FROM news").fetchone()[0]
        assert captured == 123456
    finally:
        con.close()


def test_news_insert_duplicate_promotes_flags_without_replacing_capture(tmp_path: Path):
    path = tmp_path / "news.db"
    with NewsDb(path) as db:
        first = News(
            title="Original", source="Fonte", date=100, link="https://example.com/x",
            snippet="A", capturedAt=111,
        )
        assert len(db.insertNews([first])) == 1
        duplicate = News(
            title="Atualizado", source="Fonte 2", date=200, link=first.link,
            snippet="B", important=True, demand=True,
            matchedTerm="MARINHA", matchedDemand="Veículo • Assunto", capturedAt=999,
        )
        assert db.insertNews([duplicate]) == []
        stored = db.listNews()[0]
        assert stored.title == "Atualizado"
        assert stored.source == "Fonte 2"
        assert stored.date == 200
        assert stored.snippet == "B"
        assert stored.important is True and stored.demand is True
        assert stored.matchedTerm == "MARINHA"
        assert stored.matchedDemand == "Veículo • Assunto"
        assert stored.capturedAt == 111


def test_news_transaction_rolls_back_entire_batch(tmp_path: Path):
    path = tmp_path / "news.db"
    with NewsDb(path) as db:
        good = News(title="Bom", source="F", date=1, link="https://x/1", capturedAt=1)
        bad = News(title=object(), source="F", date=2, link="https://x/2", capturedAt=2)  # type: ignore[arg-type]
        with pytest.raises(sqlite3.ProgrammingError):
            db.insertNews([good, bad])
        assert db.listNews() == []


def test_terms_and_demands_crud_exact(tmp_path: Path):
    path = tmp_path / "news.db"
    with NewsDb(path) as db:
        db.addTerm("  Novo Termo  ")
        assert "Novo Termo" in db.listTerms()
        db.removeTerm("Novo Termo")
        assert "Novo Termo" not in db.listTerms()

        db.addDemand("  Veículo  ", "  Assunto  ")
        demand = db.listDemands()[0]
        assert demand.vehicle == "Veículo" and demand.subject == "Assunto"
        assert demand.active is True
        db.updateDemandStatus(demand.id, 900, 7, 2, "erro")
        updated = db.listDemands()[0]
        assert (updated.lastCheckedAt, updated.lastFoundCount, updated.lastNewCount, updated.lastError) == (900, 7, 2, "erro")
        db.removeDemand(demand.id)
        assert db.listDemands() == []


def test_video_schema_exact_and_no_runtime_column_migration(tmp_path: Path):
    path = tmp_path / "videos.db"
    with VideoDb(path):
        pass
    cols = {row[1]: (row[2], row[3], row[4], row[5]) for row in table_columns(path, "videos")}
    assert cols == {
        "id": ("INTEGER", 0, None, 1),
        "title": ("TEXT", 1, None, 0),
        "source_id": ("TEXT", 1, None, 0),
        "source_name": ("TEXT", 1, None, 0),
        "published_at": ("INTEGER", 1, None, 0),
        "link": ("TEXT", 1, None, 0),
        "summary": ("TEXT", 0, "''", 0),
        "matched_term": ("TEXT", 0, "''", 0),
        "matched_demand": ("TEXT", 0, "''", 0),
        "captured_at": ("INTEGER", 1, None, 0),
    }

    old = tmp_path / "old-videos.db"
    con = sqlite3.connect(old)
    con.execute(
        "CREATE TABLE videos(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,"
        "source_id TEXT NOT NULL,source_name TEXT NOT NULL,published_at INTEGER NOT NULL,"
        "link TEXT UNIQUE NOT NULL,summary TEXT DEFAULT '',captured_at INTEGER NOT NULL)"
    )
    con.close()
    with VideoDb(old):
        pass
    old_cols = {row[1] for row in table_columns(old, "videos")}
    assert "matched_term" not in old_cols
    assert "matched_demand" not in old_cols


def test_video_insert_duplicate_preserves_capture_and_matches_when_blank(tmp_path: Path):
    path = tmp_path / "videos.db"
    with VideoDb(path) as db:
        first = VideoItem(
            title="A", sourceId="s1", sourceName="Fonte", publishedAt=100,
            link="https://example.com/v/1", summary="um", matchedTerm="MARINHA",
            capturedAt=111,
        )
        assert len(db.insert([first])) == 1
        duplicate = VideoItem(
            title="B", sourceId="s2", sourceName="Fonte 2", publishedAt=200,
            link=first.link, summary="dois", matchedTerm="", matchedDemand="",
            capturedAt=999,
        )
        assert db.insert([duplicate]) == []
        stored = db.listAll()[0]
        assert (stored.title, stored.sourceId, stored.sourceName, stored.publishedAt, stored.summary) == (
            "B", "s2", "Fonte 2", 200, "dois"
        )
        assert stored.matchedTerm == "MARINHA"
        assert stored.capturedAt == 111


def test_video_remove_invalid_listing_entries(tmp_path: Path):
    path = tmp_path / "videos.db"
    with VideoDb(path) as db:
        db.insert([
            VideoItem(title="Todos os vídeos", sourceId="a", sourceName="A", publishedAt=1, link="https://a.test/ok", capturedAt=1),
            VideoItem(title="Título válido", sourceId="b", sourceName="B", publishedAt=2, link="https://b.test/search/query", capturedAt=2),
            VideoItem(title="Notícia válida", sourceId="c", sourceName="C", publishedAt=3, link="https://c.test/v/123", capturedAt=3),
        ])
        assert db.removeInvalidListingEntries() == 2
        assert [item.title for item in db.listAll()] == ["Notícia válida"]


def test_video_repair_stored_matches_updates_or_deletes(tmp_path: Path):
    path = tmp_path / "videos.db"
    with VideoDb(path) as db:
        db.insert([
            VideoItem(title="Marinha realiza exercício", sourceId="a", sourceName="A", publishedAt=3, link="https://x/1", matchedTerm="MARINHA", matchedDemand="Veículo • assunto ausente", capturedAt=1),
            VideoItem(title="Outro tema", sourceId="a", sourceName="A", publishedAt=2, link="https://x/2", matchedTerm="MARINHA", capturedAt=2),
            VideoItem(title="Desfile de 7 de Setembro", sourceId="a", sourceName="A", publishedAt=1, link="https://x/3", matchedTerm="comemoração 7 setembro", capturedAt=3),
        ])
        assert db.repairStoredMatches() == 2
        items = {v.link: v for v in db.listAll()}
        assert "https://x/2" not in items
        assert items["https://x/1"].matchedTerm == "MARINHA"
        assert items["https://x/1"].matchedDemand == ""
        assert items["https://x/3"].matchedTerm == "comemoração 7 setembro"


def test_video_transaction_rolls_back_entire_batch(tmp_path: Path):
    path = tmp_path / "videos.db"
    with VideoDb(path) as db:
        good = VideoItem(title="Bom", sourceId="s", sourceName="S", publishedAt=1, link="https://x/1", capturedAt=1)
        bad = VideoItem(title=object(), sourceId="s", sourceName="S", publishedAt=2, link="https://x/2", capturedAt=2)  # type: ignore[arg-type]
        with pytest.raises(sqlite3.ProgrammingError):
            db.insert([good, bad])
        assert db.listAll() == []


def test_unicode_null_empty_and_long_text_roundtrip(tmp_path: Path):
    path = tmp_path / "news.db"
    long_text = "á漢字🙂" * 2000
    with NewsDb(path) as db:
        db.insertNews([
            News(
                title="Ação – São Paulo 🙂",
                source="",
                date=42,
                link="https://example.com/unicode",
                snippet=long_text,
                capturedAt=43,
            )
        ])
        item = db.listNews()[0]
        assert item.title == "Ação – São Paulo 🙂"
        assert item.source == ""
        assert item.snippet == long_text
