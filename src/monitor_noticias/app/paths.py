from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


def _development_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_app_root() -> Path:
    """Resolve a raiz sem depender do diretório atual do terminal."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _development_root()


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        return cls(resolve_app_root())

    @property
    def resources(self) -> Path:
        return self.root / "resources"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def bin(self) -> Path:
        return self.root / "bin"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def temp(self) -> Path:
        return self.root / "temp"

    @property
    def news_db(self) -> Path:
        return self.data / "news.db"

    @property
    def videos_db(self) -> Path:
        return self.data / "videos.db"

    @property
    def ffmpeg(self) -> Path:
        return self.bin / "ffmpeg.exe"

    @property
    def ffprobe(self) -> Path:
        return self.bin / "ffprobe.exe"

    def ensure_runtime_dirs(self) -> None:
        for directory in (self.data, self.logs, self.temp):
            directory.mkdir(parents=True, exist_ok=True)
