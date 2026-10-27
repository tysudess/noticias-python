from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Iterator, TypeVar, cast

_F = TypeVar("_F", bound=Callable[..., Any])


def synchronized(method: _F) -> _F:
    """Serialize access to the SQLite connection owned by a database object.

    ``check_same_thread=False`` only allows a connection to be used by different
    threads; it does not make a multi-statement operation atomic. Database
    methods use this decorator so reads cannot interleave with writes or with
    another transaction on the same connection.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._db.lock:
            return method(self, *args, **kwargs)

    return cast(_F, wrapper)


class SQLiteConnection:
    """Conexão central SQLite com as mesmas pragmas usadas no Desktop Kotlin."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA busy_timeout=5000")

    @property
    def raw(self) -> sqlite3.Connection:
        """Raw connection; callers must hold ``lock`` for the whole operation."""
        return self._connection

    @property
    def lock(self) -> threading.RLock:
        """Shared re-entrant lock for every operation on this connection."""
        return self._lock

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        # The same RLock is used by synchronized database methods. It must stay
        # held until COMMIT/ROLLBACK, not merely while executing BEGIN.
        with self._lock:
            self._connection.execute("BEGIN")
            try:
                yield self._connection
            except BaseException:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
