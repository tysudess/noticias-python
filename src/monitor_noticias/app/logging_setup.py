from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import AppPaths

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(paths: AppPaths, *, console: bool = True) -> logging.Logger:
    paths.logs.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    formatter = logging.Formatter(_FORMAT)
    file_handler = RotatingFileHandler(
        paths.logs / "monitor-noticias.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        root.addHandler(stream)

    return logging.getLogger("monitor_noticias")
