from __future__ import annotations

from pathlib import Path
import re
import threading
import time
import unicodedata
from urllib.parse import urlsplit

from monitor_noticias.database.connection import SQLiteConnection
from monitor_noticias.matching import phrase_matches
from monitor_noticias.models import VideoItem


_GENERIC_TITLES = {
    "videos", "video", "todos os videos", "todos videos", "ultimos videos",
    "mais videos", "ver videos", "ver todos os videos", "ao vivo",
    "assistir ao vivo", "carregar mais", "ver mais", "ver tudo",
}
_GENERIC_PATHS = {
    "/videos", "/video", "/ao-vivo", "/busca", "/search", "/categorias/jornalismo",
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()


def _is_generic_stored_result(title: str, link: str) -> bool:
    normalized = _normalize(title)
    if normalized in _GENERIC_TITLES or normalized.startswith("todos os videos"):
        return True
    if any(ch.isspace() for ch in link):
        return False
    try:
        path = (urlsplit(link).path or "").lower().rstrip("/")
    except ValueError:
        return False
    return (
        path in _GENERIC_PATHS
        or path.endswith("/busca")
        or path.endswith("/search")
        or "/busca/" in path
        or "/search/" in path
    )


class VideoDb:
    def __init__(self, path: Path) -> None:
        self._db = SQLiteConnection(path)
        self._lock = threading.RLock()
        self._db.raw.execute(
            """CREATE TABLE IF NOT EXISTS videos(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, source_id TEXT NOT NULL, source_name TEXT NOT NULL,
                published_at INTEGER NOT NULL, link TEXT UNIQUE NOT NULL, summary TEXT DEFAULT '',
                matched_term TEXT DEFAULT '', matched_demand TEXT DEFAULT '',
                captured_at INTEGER NOT NULL)"""
        )

    @property
    def path(self) -> Path:
        return self._db.path

    def insert(self, items: list[VideoItem]) -> list[VideoItem]:
        inserted: list[VideoItem] = []
        with self._lock, self._db.transaction() as connection:
            for item in items:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO videos("
                    "title,source_id,source_name,published_at,link,summary,"
                    "matched_term,matched_demand,captured_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        item.title,
                        item.sourceId,
                        item.sourceName,
                        item.publishedAt,
                        item.link,
                        item.summary,
                        item.matchedTerm,
                        item.matchedDemand,
                        item.capturedAt,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted.append(
                        VideoItem(
                            id=int(cursor.lastrowid or 0),
                            title=item.title,
                            sourceId=item.sourceId,
                            sourceName=item.sourceName,
                            publishedAt=item.publishedAt,
                            link=item.link,
                            summary=item.summary,
                            matchedTerm=item.matchedTerm,
                            matchedDemand=item.matchedDemand,
                            capturedAt=item.capturedAt,
                        )
                    )
                else:
                    connection.execute(
                        """UPDATE videos SET title=?,source_id=?,source_name=?,published_at=?,summary=?,
                           matched_term=CASE WHEN ?<>'' THEN ? ELSE matched_term END,
                           matched_demand=CASE WHEN ?<>'' THEN ? ELSE matched_demand END WHERE link=?""",
                        (
                            item.title,
                            item.sourceId,
                            item.sourceName,
                            item.publishedAt,
                            item.summary,
                            item.matchedTerm,
                            item.matchedTerm,
                            item.matchedDemand,
                            item.matchedDemand,
                            item.link,
                        ),
                    )
        return inserted

    def removeInvalidListingEntries(self) -> int:
        ids = [
            row[0]
            for row in self._db.raw.execute("SELECT id,title,link FROM videos")
            if _is_generic_stored_result(row[1] or "", row[2] or "")
        ]
        for id in ids:
            self._db.raw.execute("DELETE FROM videos WHERE id=?", (id,))
        return len(ids)

    def repairStoredMatches(self) -> int:
        repairs: list[tuple[int, str, str, bool]] = []
        rows = self._db.raw.execute(
            "SELECT id,title,summary,matched_term,matched_demand FROM videos"
        )
        for row in rows:
            id = row[0]
            body = f"{row[1] or ''} {row[2] or ''}"
            term = row[3] or ""
            demand = row[4] or ""
            term_valid = not term.strip() or phrase_matches(body, term)
            subject = demand.partition(" • ")[2].strip() if " • " in demand else demand.strip()
            demand_valid = (
                not demand.strip()
                or (bool(subject) and phrase_matches(body, subject))
            )
            if term_valid and demand_valid:
                continue
            keep_term = term if term_valid else ""
            keep_demand = demand if demand_valid else ""
            repairs.append((id, keep_term, keep_demand, not keep_term and not keep_demand))

        for id, term, demand, delete in repairs:
            if delete:
                self._db.raw.execute("DELETE FROM videos WHERE id=?", (id,))
            else:
                self._db.raw.execute(
                    "UPDATE videos SET matched_term=?,matched_demand=? WHERE id=?",
                    (term, demand, id),
                )
        return len(repairs)

    def listRecent(self, days: int = 7, limit: int = 500) -> list[VideoItem]:
        cutoff = int(time.time() * 1000) - days * 24 * 60 * 60 * 1000
        return self._query("published_at>=?", (cutoff,), limit)

    def listPeriod(self, from_: int, to: int, limit: int = 1000) -> list[VideoItem]:
        return self._query("published_at>=? AND published_at<=?", (from_, to), limit)

    def listAll(self, limit: int = 1000) -> list[VideoItem]:
        return self._query(None, (), limit)

    def clear(self) -> None:
        self._db.raw.execute("DELETE FROM videos")

    def _query(
        self, where: str | None, args: tuple[int, ...], limit: int
    ) -> list[VideoItem]:
        sql = (
            "SELECT id,title,source_id,source_name,published_at,link,summary,"
            "matched_term,matched_demand,captured_at FROM videos"
        )
        if where is not None:
            sql += f" WHERE {where}"
        sql += " ORDER BY published_at DESC,captured_at DESC LIMIT ?"
        rows = self._db.raw.execute(sql, (*args, limit))
        return [
            VideoItem(
                id=row[0],
                title=row[1],
                sourceId=row[2],
                sourceName=row[3],
                publishedAt=row[4],
                link=row[5],
                summary=row[6] or "",
                matchedTerm=row[7] or "",
                matchedDemand=row[8] or "",
                capturedAt=row[9],
            )
            for row in rows
        ]

    def close(self) -> None:
        try:
            self._db.close()
        except Exception:
            pass

    def __enter__(self) -> "VideoDb":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
