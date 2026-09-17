from __future__ import annotations

import logging
import sys
import threading
from types import TracebackType
from typing import Type

_LOG = logging.getLogger("monitor_noticias.exceptions")


def _sys_hook(exc_type: Type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
    _LOG.critical("Exceção não tratada", exc_info=(exc_type, exc, tb))


def _thread_hook(args: threading.ExceptHookArgs) -> None:
    _LOG.critical(
        "Exceção não tratada em thread %s",
        args.thread.name if args.thread else "desconhecida",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def install_global_exception_hooks() -> None:
    sys.excepthook = _sys_hook
    threading.excepthook = _thread_hook
