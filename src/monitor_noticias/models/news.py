from __future__ import annotations

from dataclasses import dataclass, field
import time


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True, kw_only=True)
class News:
    id: int = 0
    title: str
    source: str
    date: int
    link: str
    snippet: str = ""
    important: bool = False
    demand: bool = False
    matchedTerm: str = ""
    matchedDemand: str = ""
    capturedAt: int = field(default_factory=_now_ms)


@dataclass(frozen=True, slots=True, kw_only=True)
class Demand:
    id: int = 0
    vehicle: str
    subject: str
    active: bool = True
    lastCheckedAt: int = 0
    lastFoundCount: int = 0
    lastNewCount: int = 0
    lastError: str = ""
