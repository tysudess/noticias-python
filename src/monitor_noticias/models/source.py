from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaSource:
    id: str
    name: str
    region: str
    state: str
    stateName: str
    group: str
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class VideoSource:
    id: str
    name: str
    group: str
    region: str = "Nacional"
    state: str = ""
    landingUrl: str
    linkHints: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    youtubeHandle: str = ""
    searchUrlTemplate: str = ""
    searchPrefix: str = ""
