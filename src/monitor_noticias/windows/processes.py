"""Compatibilidade histórica.

Código novo deve importar:
    monitor_noticias.platform.processes

Este módulo continua existindo para que módulos antigos não quebrem.
"""

from monitor_noticias.platform.processes import (
    HiddenProcessRunner,
    ProcessResult,
)

__all__ = [
    "HiddenProcessRunner",
    "ProcessResult",
]
