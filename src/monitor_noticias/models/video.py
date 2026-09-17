from __future__ import annotations

from dataclasses import dataclass, field
import time


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True, kw_only=True)
class VideoItem:
    id: int = 0
    title: str
    sourceId: str
    sourceName: str
    publishedAt: int
    link: str
    summary: str = ""
    matchedTerm: str = ""
    matchedDemand: str = ""
    capturedAt: int = field(default_factory=_now_ms)

    @property
    def relevant(self) -> bool:
        return bool(self.matchedTerm.strip() or self.matchedDemand.strip())

    @property
    def demand(self) -> bool:
        return bool(self.matchedDemand.strip())
