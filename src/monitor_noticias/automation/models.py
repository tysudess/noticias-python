from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LiveSearchProgress:
    active: bool = False
    kind: str = ""
    startedAt: int = 0
    finishedAt: int = 0
    completed: int = 0
    total: int = 0
    currentSource: str = ""
    currentQuery: str = ""
    found: int = 0
    newCount: int = 0
    errors: int = 0

    @property
    def fraction(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.completed / self.total))


@dataclass(frozen=True, slots=True)
class SearchResult:
    foundCount: int
    newCount: int
    newDemandCount: int
    errors: int = 0


@dataclass(frozen=True, slots=True)
class DemandSweepResult:
    checkedCount: int
    foundCount: int
    newCount: int
    errors: int = 0


@dataclass(frozen=True, slots=True)
class VideoSearchResult:
    relevantCount: int
    newRelevantCount: int
    errors: int = 0
    unstableSources: tuple[object, ...] = field(default_factory=tuple)
