from __future__ import annotations

from pathlib import Path
import threading
import time

from monitor_noticias.database.connection import SQLiteConnection
from monitor_noticias.database.default_terms import DEFAULT_MONITOR_TERMS
from monitor_noticias.models import Demand, News


class NewsDb:
    def __init__(self, path: Path) -> None:
        self._db = SQLiteConnection(path)
        self._lock = threading.RLock()
        self._create_schema()
        self._ensure_columns()
        self._seed_terms()

    @property
    def path(self) -> Path:
        return self._db.path

    def _create_schema(self) -> None:
        connection = self._db.raw
        connection.execute(
            "CREATE TABLE IF NOT EXISTS news("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "title TEXT NOT NULL,source TEXT,date INTEGER NOT NULL,link TEXT UNIQUE,"
            "snippet TEXT,important INTEGER DEFAULT 0,demand INTEGER DEFAULT 0,"
            "matched_term TEXT DEFAULT '',matched_demand TEXT DEFAULT '',"
            "captured_at INTEGER NOT NULL DEFAULT 0)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS terms("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,term TEXT UNIQUE NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS demands("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,vehicle TEXT NOT NULL,subject TEXT NOT NULL,"
            "active INTEGER DEFAULT 1,last_checked_at INTEGER NOT NULL DEFAULT 0,"
            "last_found_count INTEGER NOT NULL DEFAULT 0,last_new_count INTEGER NOT NULL DEFAULT 0,"
            "last_error TEXT DEFAULT '')"
        )

    def _ensure_columns(self) -> None:
        connection = self._db.raw
        cols = {row["name"] for row in connection.execute("PRAGMA table_info(news)")}
        if "matched_term" not in cols:
            connection.execute("ALTER TABLE news ADD COLUMN matched_term TEXT DEFAULT ''")
        if "matched_demand" not in cols:
            connection.execute("ALTER TABLE news ADD COLUMN matched_demand TEXT DEFAULT ''")
        if "captured_at" not in cols:
            connection.execute(
                "ALTER TABLE news ADD COLUMN captured_at INTEGER NOT NULL DEFAULT 0"
            )
            connection.execute("UPDATE news SET captured_at=date WHERE captured_at=0")

        demand_cols = {
            row["name"] for row in connection.execute("PRAGMA table_info(demands)")
        }
        if "last_checked_at" not in demand_cols:
            connection.execute(
                "ALTER TABLE demands ADD COLUMN last_checked_at INTEGER NOT NULL DEFAULT 0"
            )
        if "last_found_count" not in demand_cols:
            connection.execute(
                "ALTER TABLE demands ADD COLUMN last_found_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_new_count" not in demand_cols:
            connection.execute(
                "ALTER TABLE demands ADD COLUMN last_new_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_error" not in demand_cols:
            connection.execute("ALTER TABLE demands ADD COLUMN last_error TEXT DEFAULT ''")

    def _seed_terms(self) -> None:
        self._db.raw.executemany(
            "INSERT OR IGNORE INTO terms(term) VALUES(?)",
            ((value,) for value in DEFAULT_MONITOR_TERMS),
        )

    def insertNews(self, items: list[News]) -> list[News]:
        inserted: list[News] = []
        with self._lock, self._db.transaction() as connection:
            for item in items:
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO news("
                    "title,source,date,link,snippet,important,demand,"
                    "matched_term,matched_demand,captured_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        item.title,
                        item.source,
                        item.date,
                        item.link,
                        item.snippet,
                        1 if item.important else 0,
                        1 if item.demand else 0,
                        item.matchedTerm,
                        item.matchedDemand,
                        item.capturedAt,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted.append(
                        News(
                            id=int(cursor.lastrowid or 0),
                            title=item.title,
                            source=item.source,
                            date=item.date,
                            link=item.link,
                            snippet=item.snippet,
                            important=item.important,
                            demand=item.demand,
                            matchedTerm=item.matchedTerm,
                            matchedDemand=item.matchedDemand,
                            capturedAt=item.capturedAt,
                        )
                    )
                else:
                    connection.execute(
                        """UPDATE news SET title=?,source=?,date=?,snippet=?,
                           important=CASE WHEN ?=1 THEN 1 ELSE important END,
                           demand=CASE WHEN ?=1 THEN 1 ELSE demand END,
                           matched_term=CASE WHEN ?<>'' THEN ? ELSE matched_term END,
                           matched_demand=CASE WHEN ?<>'' THEN ? ELSE matched_demand END
                           WHERE link=?""",
                        (
                            item.title,
                            item.source,
                            item.date,
                            item.snippet,
                            1 if item.important else 0,
                            1 if item.demand else 0,
                            item.matchedTerm,
                            item.matchedTerm,
                            item.matchedDemand,
                            item.matchedDemand,
                            item.link,
                        ),
                    )
        return inserted

    def listRecent(self, hours: int = 24, limit: int = 500) -> list[News]:
        cutoff = int(time.time() * 1000) - hours * 60 * 60 * 1000
        return self._queryNews("date>=?", (cutoff,), limit)

    def listNews(self, limit: int = 500) -> list[News]:
        return self._queryNews(None, (), limit)

    def _queryNews(
        self, where: str | None, args: tuple[int, ...], limit: int
    ) -> list[News]:
        sql = (
            "SELECT id,title,source,date,link,snippet,important,demand,"
            "matched_term,matched_demand,captured_at FROM news"
        )
        if where is not None:
            sql += f" WHERE {where}"
        sql += " ORDER BY date DESC LIMIT ?"
        rows = self._db.raw.execute(sql, (*args, limit))
        return [
            News(
                id=row[0],
                title=row[1],
                source=row[2] or "",
                date=row[3],
                link=row[4],
                snippet=row[5] or "",
                important=row[6] == 1,
                demand=row[7] == 1,
                matchedTerm=row[8] or "",
                matchedDemand=row[9] or "",
                capturedAt=row[10],
            )
            for row in rows
        ]

    def listTerms(self) -> list[str]:
        return [
            row[0]
            for row in self._db.raw.execute(
                "SELECT term FROM terms ORDER BY term COLLATE NOCASE"
            )
        ]

    def addTerm(self, term: str) -> None:
        clean = term.strip()
        if not clean:
            return
        self._db.raw.execute("INSERT OR IGNORE INTO terms(term) VALUES(?)", (clean,))

    def removeTerm(self, term: str) -> None:
        self._db.raw.execute("DELETE FROM terms WHERE term=?", (term,))

    def listDemands(self) -> list[Demand]:
        rows = self._db.raw.execute(
            "SELECT id,vehicle,subject,active,last_checked_at,last_found_count,"
            "last_new_count,last_error FROM demands ORDER BY id DESC"
        )
        return [
            Demand(
                id=row[0],
                vehicle=row[1],
                subject=row[2],
                active=row[3] == 1,
                lastCheckedAt=row[4],
                lastFoundCount=row[5],
                lastNewCount=row[6],
                lastError=row[7] or "",
            )
            for row in rows
        ]

    def addDemand(self, vehicle: str, subject: str) -> None:
        if not vehicle.strip() or not subject.strip():
            return
        self._db.raw.execute(
            "INSERT INTO demands(vehicle,subject) VALUES(?,?)",
            (vehicle.strip(), subject.strip()),
        )

    def updateDemandStatus(
        self,
        id: int,
        checked_at: int,
        found_count: int,
        new_count: int,
        error: str = "",
    ) -> None:
        self._db.raw.execute(
            "UPDATE demands SET last_checked_at=?,last_found_count=?,"
            "last_new_count=?,last_error=? WHERE id=?",
            (checked_at, found_count, new_count, error, id),
        )

    def removeDemand(self, id: int) -> None:
        self._db.raw.execute("DELETE FROM demands WHERE id=?", (id,))

    def clearHistory(self) -> None:
        self._db.raw.execute("DELETE FROM news")

    def close(self) -> None:
        try:
            self._db.close()
        except Exception:
            pass

    def __enter__(self) -> "NewsDb":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
