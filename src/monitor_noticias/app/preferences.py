from __future__ import annotations

import base64
import threading
from pathlib import Path


class SharedPreferences:
    """Compatibilidade com o SharedPreferences desktop de Context.kt.

    Persistência em data/prefs/<name>.properties. Valores escalares são texto; sets
    usam Base64 URL-safe sem padding separados por ``|``, como a baseline Kotlin.
    """

    def __init__(self, file: Path) -> None:
        self.file = Path(file)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, str]:
        if not self.file.is_file():
            return {}
        out: dict[str, str] = {}
        for raw in self.file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                key, value = line, ""
            out[key.strip()] = value.strip()
        return out

    def _persist(self, values: dict[str, str]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_name(self.file.name + ".tmp")
        body = "#Monitor de Noticias\n" + "".join(f"{k}={v}\n" for k, v in values.items())
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(self.file)

    def get_boolean(self, key: str, default: bool) -> bool:
        with self._lock:
            raw = self._load().get(key)
            return default if raw not in {"true", "false"} else raw == "true"

    def get_int(self, key: str, default: int) -> int:
        with self._lock:
            try: return int(self._load().get(key, str(default)))
            except ValueError: return default

    def get_long(self, key: str, default: int) -> int:
        return self.get_int(key, default)

    def get_string(self, key: str, default: str | None) -> str | None:
        with self._lock:
            return self._load().get(key, default)

    def get_string_set(self, key: str, default: set[str] | None) -> set[str] | None:
        with self._lock:
            raw = self._load().get(key)
            if raw is None: return default
            if not raw: return set()
            out: set[str] = set()
            for piece in raw.split("|"):
                if not piece: continue
                padded = piece + "=" * ((4 - len(piece) % 4) % 4)
                out.add(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
            return out

    def update(self, **values: object) -> None:
        with self._lock:
            current = self._load()
            for key, value in values.items():
                if value is None:
                    current.pop(key, None)
                elif isinstance(value, bool):
                    current[key] = "true" if value else "false"
                elif isinstance(value, set):
                    current[key] = "|".join(
                        base64.urlsafe_b64encode(str(item).encode("utf-8")).decode("ascii").rstrip("=")
                        for item in value
                    )
                else:
                    current[key] = str(value)
            self._persist(current)
