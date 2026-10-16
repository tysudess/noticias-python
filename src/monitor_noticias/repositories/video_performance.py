from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

STAT_KEYS = (
    "network_gets",
    "cache_hits",
    "cache_misses",
    "cache_reused_bytes",
    "bytes_received",
    "elapsed_ms",
    "errors",
)


def is_regional_video_source(source) -> bool:
    state = str(getattr(source, "state", "") or "").strip().upper()
    return (len(state) == 2 and state != "BR") or str(getattr(source, "id", "")).startswith(
        "globoplay-regionais-"
    )


def _totals(stats_list) -> dict[str, int]:
    return {
        key: sum(int(stats.get(key, 0) or 0) for stats in stats_list)
        for key in STAT_KEYS
    }


class RegionalVideoSearchProfiler:
    """Mede tempo e GETs por fonte regional sem alterar o resultado da busca."""

    def __init__(self, sources, stats_list, downstream=None):
        self._sources_by_name = {source.name: source for source in sources}
        self._stats_list = list(stats_list)
        self._downstream = downstream
        self._active_source = None
        self._started_at = 0.0
        self._before = _totals(self._stats_list)
        self._last_progress = None
        self._start_found = 0
        self._start_new_count = 0

    def __call__(self, progress, items=()):
        source_name = str(getattr(progress, "currentSource", "") or "")
        if source_name != self._active_name():
            self._finish_active()
            source = self._sources_by_name.get(source_name)
            if source is not None:
                self._active_source = source
                self._started_at = time.monotonic()
                self._before = _totals(self._stats_list)
                self._last_progress = progress
                self._start_found = int(getattr(progress, "found", 0) or 0)
                self._start_new_count = int(getattr(progress, "newCount", 0) or 0)
        elif self._active_source is not None:
            self._last_progress = progress

        if self._downstream:
            self._downstream(progress, items)

    def _active_name(self):
        return getattr(self._active_source, "name", "") if self._active_source else ""

    def _finish_active(self):
        source = self._active_source
        if source is None:
            return

        after = _totals(self._stats_list)
        elapsed_ms = max(0, int((time.monotonic() - self._started_at) * 1000))
        delta = {key: max(0, after[key] - self._before[key]) for key in STAT_KEYS}
        progress = self._last_progress
        found_now = int(getattr(progress, "found", 0) or 0) if progress is not None else self._start_found
        new_now = int(getattr(progress, "newCount", 0) or 0) if progress is not None else self._start_new_count
        found_delta = max(0, found_now - self._start_found)
        new_delta = max(0, new_now - self._start_new_count)

        if is_regional_video_source(source):
            log.info(
                "VIDEO_SEARCH_PERF regional source=%s state=%s elapsed_ms=%d "
                "http_gets=%d html_cache_hits=%d cache_misses=%d "
                "request_elapsed_ms=%d bytes_received=%d bytes_reused=%d "
                "found_delta=%d new_delta=%d errors=%d",
                source.name,
                str(getattr(source, "state", "") or ""),
                elapsed_ms,
                delta["network_gets"],
                delta["cache_hits"],
                delta["cache_misses"],
                delta["elapsed_ms"],
                delta["bytes_received"],
                delta["cache_reused_bytes"],
                found_delta,
                new_delta,
                delta["errors"],
            )

        self._active_source = None
        self._started_at = 0.0
        self._last_progress = None
        self._before = after
        self._start_found = 0
        self._start_new_count = 0

    def finish(self):
        self._finish_active()
