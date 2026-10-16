from __future__ import annotations

import logging
from pathlib import Path
from threading import Thread

from monitor_noticias.collectors.video.catalog import BY_ID
from monitor_noticias.models import VideoSource
from monitor_noticias.networking.http_client import HttpClient
from monitor_noticias.repositories.video_collect import (
    REGIONAL_EDITION_DISCOVERY_URL_LIMIT,
    _collect_editions_with_regional_limit,
)
from monitor_noticias.repositories.video_performance import RegionalVideoSearchProfiler

ROOT = Path(__file__).resolve().parents[2]


class FakeResponse:
    def __init__(self, body=b"<html><body>page</body></html>", headers=None, encoding="utf-8"):
        self.content = body
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.encoding = encoding

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or FakeResponse()

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class FakeEditionCollector:
    def __init__(self):
        self.discoveries = [
            "https://globoplay.globo.com/busca/?q=Programa",
            "https://globoplay.globo.com/busca/?q=Emissora",
            "https://globoplay.globo.com/busca/?q=Alias3",
            "https://globoplay.globo.com/busca/?q=Alias4",
            "https://globoplay.globo.com/busca/?q=Alias5",
        ]
        self.requested = []

    def _discovery_urls(self, source):
        return list(self.discoveries)

    def collect(self, source, captured_at, from_ms, to_ms, on_error):
        self.requested = self._discovery_urls(source)
        return self.requested


def _regional_source():
    return VideoSource(
        id="globoplay-bom-dia-df",
        name="Globoplay • Bom Dia DF",
        group="Globo / Globoplay • Telejornal regional",
        region="Centro-Oeste",
        state="DF",
        landingUrl="https://globoplay.globo.com/busca/?q=Bom+Dia+DF",
        aliases=["Globo", "Globoplay", "Bom Dia DF", "Globo Brasília"],
        searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}",
        searchPrefix="Bom Dia DF",
    )


def test_regional_globoplay_discovery_uses_at_most_two_search_pages_and_restores_method():
    collector = FakeEditionCollector()
    source = _regional_source()

    result = _collect_editions_with_regional_limit(
        collector, source, 1_800_000_000_000, 0, 1_800_000_000_000, lambda: None
    )

    assert len(result) == REGIONAL_EDITION_DISCOVERY_URL_LIMIT
    assert result == collector.discoveries[:2]
    # A chamada ao coletor foi temporária; métodos/aliases completos voltam ao normal.
    assert collector._discovery_urls(source) == collector.discoveries


def test_national_globoplay_source_keeps_original_discovery_budget():
    collector = FakeEditionCollector()
    source = VideoSource(
        id="globoplay-jornal-nacional",
        name="Globoplay • Jornal Nacional",
        group="Globo / Globoplay",
        state="",
        landingUrl="https://globoplay.globo.com/busca/?q=Jornal+Nacional",
        aliases=["Globo", "Globoplay", "Jornal Nacional", "JN", "Telejornal"],
        searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}",
        searchPrefix="Jornal Nacional",
    )

    result = _collect_editions_with_regional_limit(
        collector, source, 1_800_000_000_000, 0, 1_800_000_000_000, lambda: None
    )

    assert result == collector.discoveries
    assert len(result) == 5


def test_http_get_cache_reuses_same_html_only_inside_search_scope():
    session = FakeSession()
    client = HttpClient(session=session)
    url = "https://globoplay.globo.com/busca/?q=Bom+Dia+DF"
    args = {
        "headers": {
            "User-Agent": "Test-Agent",
            "Accept-Language": "pt-BR",
            "Referer": "https://www.google.com/",
        },
        "connect_timeout": 1,
        "read_timeout": 1,
        "max_body_bytes": 1024,
    }

    with client.request_cache_scope() as stats:
        first = client.get_text(url, **args)
        second = client.get_text(url, **args)
        assert first == second
        assert len(session.calls) == 1
        assert stats["network_gets"] == 1
        assert stats["cache_hits"] == 1
        assert stats["cache_reused_bytes"] > 0

    client.get_text(url, **args)
    assert len(session.calls) == 2


def test_http_get_cache_key_respects_headers_and_does_not_cache_non_html():
    session = FakeSession()
    client = HttpClient(session=session)
    url = "https://example.test/page"
    base = {"connect_timeout": 1, "read_timeout": 1, "max_body_bytes": 1024}

    with client.request_cache_scope() as stats:
        client.get_text(url, headers={"Referer": "https://a.test"}, **base)
        client.get_text(url, headers={"Referer": "https://b.test"}, **base)
        assert len(session.calls) == 2
        assert stats["cache_hits"] == 0

    json_session = FakeSession(FakeResponse(
        body=b'{"ok":true}',
        headers={"content-type": "application/json"},
    ))
    json_client = HttpClient(session=json_session)
    with json_client.request_cache_scope() as stats:
        json_client.get_text(url, **base)
        json_client.get_text(url, **base)
        assert len(json_session.calls) == 2
        assert stats["cache_hits"] == 0



def test_http_get_cache_is_thread_local_and_cannot_leak_to_other_search_lanes():
    session = FakeSession()
    client = HttpClient(session=session)
    url = "https://globoplay.globo.com/busca/?q=regional"
    args = {"headers": {"User-Agent": "Test-Agent"}, "connect_timeout": 1, "read_timeout": 1}

    with client.request_cache_scope() as stats:
        client.get_text(url, **args)
        worker = Thread(target=lambda: client.get_text(url, **args))
        worker.start()
        worker.join(timeout=3)
        assert not worker.is_alive()
        # The second thread had no active cache scope, so it made its own GET.
        assert len(session.calls) == 2
        client.get_text(url, **args)
        assert len(session.calls) == 2
        assert stats["cache_hits"] == 1

def test_http_get_cache_skips_set_cookie_responses():
    session = FakeSession(FakeResponse(
        body=b"<html>personalized</html>",
        headers={"content-type": "text/html", "set-cookie": "session=abc"},
    ))
    client = HttpClient(session=session)
    with client.request_cache_scope() as stats:
        client.get_text("https://example.test/page", connect_timeout=1, read_timeout=1)
        client.get_text("https://example.test/page", connect_timeout=1, read_timeout=1)
        assert len(session.calls) == 2
        assert stats["cache_hits"] == 0


def test_regional_source_profile_writes_elapsed_and_http_counters(caplog):
    source = BY_ID["video-band-brasilia"]
    stats = {
        "network_gets": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "cache_reused_bytes": 0,
        "bytes_received": 0,
        "elapsed_ms": 0,
        "errors": 0,
    }
    profiler = RegionalVideoSearchProfiler([source], [stats])

    class Progress:
        currentSource = source.name
        found = 0
        newCount = 0

    caplog.set_level(logging.INFO)
    profiler(Progress())
    stats.update(network_gets=4, cache_hits=2, cache_misses=4, bytes_received=4096, elapsed_ms=1800)
    Progress.found = 3
    Progress.newCount = 1

    class Finished:
        currentSource = "Concluído"
        found = 3
        newCount = 1

    profiler(Finished())
    assert "VIDEO_SEARCH_PERF regional source=Band Brasília" in caplog.text
    assert "http_gets=4" in caplog.text
    assert "html_cache_hits=2" in caplog.text
    assert "elapsed_ms=" in caplog.text


def test_regional_profile_includes_state_specific_and_regional_sweep_sources():
    from monitor_noticias.repositories.video_performance import is_regional_video_source

    assert is_regional_video_source(BY_ID["video-band-brasilia"])
    sweep = VideoSource(
        id="globoplay-regionais-bom-dia",
        name="Globoplay • Cobertura ampla — Bom Dia",
        group="Globo / Globoplay • Cobertura regional ampla",
        state="BR",
        region="Todas",
        landingUrl="https://globoplay.globo.com/busca/?q=Bom+Dia",
        searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}",
        searchPrefix="Bom Dia",
    )
    assert is_regional_video_source(sweep)
    assert not is_regional_video_source(BY_ID["video-globoplay-jornalismo"])


def test_scan_progress_is_emitted_before_regional_collection_starts():
    source = (ROOT / "src/monitor_noticias/repositories/video_search.py").read_text(encoding="utf-8")
    marker = "emit(source.name, label)"
    collection = "scan_candidates = collect_recent_by_source("
    assert marker in source and collection in source
    assert source.index(marker) < source.index(collection)


def test_video_search_profile_does_not_change_default_source_catalog():
    # The optimization is applied at collection time and does not change what users selected.
    assert "DEFAULT_IDS" not in (
        ROOT / "src/monitor_noticias/repositories/video_collect.py"
    ).read_text(encoding="utf-8")
    assert BY_ID["video-band-brasilia"].state == "DF"
