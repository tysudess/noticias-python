from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.current import is_linux, is_windows


SESSION_SERVICE = "CentralInteligenteDeMidia"


class SecureSessionUnavailable(RuntimeError):
    pass


class SecureSessionStore:
    """Cofre de cookies/sessão dos jornais digitais.

    Windows usa DPAPI CurrentUser. Ubuntu/Linux usa Secret Service / Keyring.
    Não existe fallback em texto puro.
    """

    def __init__(
        self,
        paths: AppPaths,
        provider_id: str,
    ) -> None:
        self.paths = paths
        self.provider_id = str(provider_id)
        self._store = self._create_store()

    def _create_store(self):
        if is_windows():
            from monitor_noticias.windows.dpapi import DpapiTextStore

            return DpapiTextStore(
                self.paths.data
                / "digital_newspapers"
                / "sessions"
                / f"{self.provider_id}.dpapi"
            )

        if is_linux():
            from monitor_noticias.platform.credentials import LinuxKeyringTextStore

            return LinuxKeyringTextStore(
                service_name=SESSION_SERVICE,
                account_name=(
                    "digital-newspaper-session:"
                    + self.provider_id
                ),
            )

        return None

    @property
    def available(self) -> bool:
        return self._store is not None

    def exists(self) -> bool:
        if self._store is None:
            return False
        try:
            return bool(self._store.exists())
        except Exception:
            return False

    def save_json(self, value) -> None:
        if self._store is None:
            raise SecureSessionUnavailable(
                "Cofre seguro não disponível neste sistema."
            )

        payload = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        self._store.save(payload)

    def load_json(self, default=None):
        if self._store is None:
            return default

        try:
            raw = self._store.load()
            if not raw:
                return default
            return json.loads(raw)
        except Exception:
            return default

    def clear(self) -> None:
        if self._store is None:
            return
        try:
            self._store.delete()
        except Exception:
            pass


class SecureCredentialStore:
    """Cofre local de usuário/senha por jornal.

    Windows: DPAPI CurrentUser.
    Ubuntu/Linux: Secret Service / Keyring.
    Nunca existe fallback em texto puro nem arquivo para GitHub.
    """

    def __init__(
        self,
        paths: AppPaths,
        provider_id: str,
    ) -> None:
        self.paths = paths
        self.provider_id = str(provider_id)
        self._store = self._create_store()

    def _create_store(self):
        if is_windows():
            from monitor_noticias.windows.dpapi import DpapiTextStore

            return DpapiTextStore(
                self.paths.data
                / "digital_newspapers"
                / "credentials"
                / f"{self.provider_id}.dpapi"
            )

        if is_linux():
            from monitor_noticias.platform.credentials import LinuxKeyringTextStore

            return LinuxKeyringTextStore(
                service_name=SESSION_SERVICE,
                account_name=(
                    "digital-newspaper-credential:"
                    + self.provider_id
                ),
            )

        return None

    @property
    def available(self) -> bool:
        return self._store is not None

    def exists(self) -> bool:
        if self._store is None:
            return False
        try:
            return bool(self._store.exists())
        except Exception:
            return False

    def save(
        self,
        username: str,
        password: str,
    ) -> None:
        username = str(username or "").strip()
        password = str(password or "")
        if not username or not password:
            raise ValueError("Usuário e senha são obrigatórios.")
        if self._store is None:
            raise SecureSessionUnavailable(
                "Cofre seguro não disponível neste sistema."
            )
        payload = json.dumps(
            {"username": username, "password": password},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        self._store.save(payload)

    def load(self) -> tuple[str, str] | None:
        if self._store is None:
            return None
        try:
            raw = self._store.load()
            if not raw:
                return None
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            username = str(data.get("username") or "").strip()
            password = str(data.get("password") or "")
            if not username or not password:
                return None
            return username, password
        except Exception:
            return None

    def clear(self) -> None:
        if self._store is None:
            return
        try:
            self._store.delete()
        except Exception:
            pass


@dataclass(slots=True)
class DigitalNewspaperHistoryEntry:
    newspaper: str
    provider_id: str
    edition_date: str
    pages: int
    quality: str
    method: str
    path: str
    status: str
    created_at: str

    @classmethod
    def completed(
        cls,
        *,
        newspaper: str,
        provider_id: str,
        edition_date: str,
        pages: int,
        quality: str,
        method: str,
        path: Path,
    ) -> "DigitalNewspaperHistoryEntry":
        return cls(
            newspaper=newspaper,
            provider_id=provider_id,
            edition_date=edition_date,
            pages=max(0, int(pages)),
            quality=quality,
            method=method,
            path=str(path),
            status="Concluído",
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class DigitalNewspaperHistoryStore:
    def __init__(self, paths: AppPaths) -> None:
        self.path = (
            paths.data
            / "digital_newspapers"
            / "history.json"
        )

    def list(self, limit: int = 200) -> list[DigitalNewspaperHistoryEntry]:
        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        out: list[DigitalNewspaperHistoryEntry] = []
        for item in data[: max(1, int(limit))]:
            if not isinstance(item, dict):
                continue
            try:
                out.append(DigitalNewspaperHistoryEntry(**item))
            except Exception:
                continue
        return out

    def append(self, entry: DigitalNewspaperHistoryEntry) -> None:
        rows = self.list(limit=999)
        rows.insert(0, entry)
        rows = rows[:500]
        self._write(rows)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def _write(
        self,
        rows: Iterable[DigitalNewspaperHistoryEntry],
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(
                [asdict(row) for row in rows],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        tmp.replace(self.path)
