from __future__ import annotations

from dataclasses import dataclass
from monitor_noticias.models import Demand, News

@dataclass(frozen=True, slots=True)
class NewsSearchResult:
    items: tuple[News, ...]
    foundCount: int
    newCount: int
    newDemandCount: int
    errors: int = 0
    newLinks: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class DemandSearchResult:
    demand: Demand
    items: tuple[News, ...]
    foundCount: int
    newCount: int
    error: str | None = None
    newLinks: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class DemandSweepResult:
    checkedCount: int
    foundCount: int
    newCount: int
    errors: int
    items: tuple[News, ...]
    newLinks: tuple[str, ...] = ()
