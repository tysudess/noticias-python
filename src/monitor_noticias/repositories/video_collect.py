from __future__ import annotations

from monitor_noticias.collectors.video.catalog import CORE_NATIONAL_GLOBOPLAY_IDS, PORTAL_PROGRAM_SCAN_IDS
from monitor_noticias.matching.video_rules import canonical_key, is_globoplay_source


def is_source_scan_mode(source) -> bool:
    return is_globoplay_source(source) or bool(source.youtubeHandle.strip()) or source.id in PORTAL_PROGRAM_SCAN_IDS


def collect_recent_by_source(repo, source, captured_at, from_ms, to_ms, on_error):
    if source.youtubeHandle.strip():
        try:
            items = repo.youtube.collect(source, captured_at)
        except Exception:
            on_error("YouTube • feed/canal"); items = []
        if items:
            return list({canonical_key(item.link):item for item in items}.values())
        try:
            return list({canonical_key(item.link):item for item in repo.website.fetch_website(source, captured_at)}.values())
        except Exception:
            on_error("YouTube • página"); return []

    if is_globoplay_source(source):
        try:
            editions = repo.editions.collect(source, captured_at, from_ms, to_ms, lambda: on_error("Globoplay • Edições"))
        except Exception:
            on_error("Globoplay • Edições"); editions = []
        if source.id in CORE_NATIONAL_GLOBOPLAY_IDS:
            try:
                scenes = repo.trechos.collect(source, captured_at, lambda: on_error("Globoplay • Trechos"))
            except Exception:
                on_error("Globoplay • Trechos"); scenes = []
            combined = list({canonical_key(item.link):item for item in [*editions,*scenes]}.values())
            if combined: return combined
        elif editions:
            return list({canonical_key(item.link):item for item in editions}.values())
        else:
            try:
                scenes = repo.trechos.collect(source, captured_at, lambda: on_error("Globoplay • Trechos"))
            except Exception:
                on_error("Globoplay • Trechos"); scenes = []
            if scenes: return list({canonical_key(item.link):item for item in scenes}.values())
        try:
            if source.searchPrefix.strip() and source.searchUrlTemplate.strip():
                primary = repo.website.fetch_search_website(source, "", captured_at)
            else:
                primary = repo.website.fetch_website(source, captured_at)
            return list({canonical_key(item.link):item for item in primary}.values())
        except Exception:
            on_error("Globoplay • busca fallback"); return []

    if source.id in PORTAL_PROGRAM_SCAN_IDS:
        try:
            landing = repo.website.fetch_website(source, captured_at)
        except Exception:
            on_error("Portal • página do programa"); landing = []
        if landing:
            return list({canonical_key(item.link):item for item in landing}.values())
        if source.searchUrlTemplate.strip() and source.searchPrefix.strip():
            try:
                fallback = repo.website.fetch_search_website(source, "", captured_at)
                return list({canonical_key(item.link):item for item in fallback}.values())
            except Exception:
                on_error("Portal • busca fallback")
        return []

    try:
        return list({canonical_key(item.link):item for item in repo.website.fetch_website(source, captured_at)}.values())
    except Exception:
        on_error("Portal • página"); return []


def collect_for_query(repo, source, query, captured_at, on_error):
    searched = []
    if source.searchUrlTemplate.strip():
        try: searched = repo.website.fetch_search_website(source, query, captured_at)
        except Exception: on_error("Busca por termo")
    return searched
