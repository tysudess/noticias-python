from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve()

    candidates = [
        # Execução normal no repositório
        here.parents[1] / "assets" / "app_icon.ico",
        here.parents[1] / "assets" / "app_icon.png",

        # Execução em bundle PyInstaller
        Path(getattr(sys, "_MEIPASS", ".")) / "src" / "monitor_noticias" / "assets" / "app_icon.ico",
        Path(getattr(sys, "_MEIPASS", ".")) / "src" / "monitor_noticias" / "assets" / "app_icon.png",

        # Execução em bundle com assets copiados sem prefixo src/
        Path(getattr(sys, "_MEIPASS", ".")) / "monitor_noticias" / "assets" / "app_icon.ico",
        Path(getattr(sys, "_MEIPASS", ".")) / "monitor_noticias" / "assets" / "app_icon.png",

        # Execução portable ao lado do executável
        Path(sys.executable).resolve().parent / "src" / "monitor_noticias" / "assets" / "app_icon.ico",
        Path(sys.executable).resolve().parent / "src" / "monitor_noticias" / "assets" / "app_icon.png",
        Path(sys.executable).resolve().parent / "monitor_noticias" / "assets" / "app_icon.ico",
        Path(sys.executable).resolve().parent / "monitor_noticias" / "assets" / "app_icon.png",
    ]

    # remove duplicatas mantendo ordem
    seen: set[str] = set()
    ordered: list[Path] = []

    for item in candidates:
        key = str(item)
        if key not in seen:
            seen.add(key)
            ordered.append(item)

    return ordered


def load_app_icon() -> QIcon:
    for path in _candidate_paths():
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return QIcon()
