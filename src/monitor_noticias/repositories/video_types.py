from __future__ import annotations

from dataclasses import dataclass
from monitor_noticias.models import VideoItem

@dataclass(frozen=True, slots=True)
class VideoSourceIssue:
    sourceId: str
    sourceName: str
    failureCount: int
    stage: str

@dataclass(frozen=True, slots=True)
class VideoSearchResult:
    items: tuple[VideoItem, ...]
    foundCount: int
    newCount: int
    relevantCount: int
    newRelevantCount: int
    errors: int = 0
    unstableSources: tuple[VideoSourceIssue, ...] = ()
    newLinks: tuple[str, ...] = ()
