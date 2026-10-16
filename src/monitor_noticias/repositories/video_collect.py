from __future__ import annotations

from monitor_noticias.collectors.video.catalog import CORE_NATIONAL_GLOBOPLAY_IDS, PORTAL_PROGRAM_SCAN_IDS
from monitor_noticias.matching.video_rules import canonical_key, is_globoplay_source

REGIONAL_EDITION_DISCOVERY_URL_LIMIT = 2


def is_source_scan_mode(source) -> bool:
    return is_globoplay_source(source) or bool(source.youtubeHandle.strip()) or source.id in PORTAL_PROGRAM_SCAN_IDS


def _is_state_specific_regional_source(source) -> bool:
    state = str(getattr(source, "state", "") or "").strip().upper()
    return len(state) == 2 and state != "BR"


def _collect_editions_with_regional_limit(collector, source, captured_at, from_ms, to_ms, on_error):
    """Limita só as URLs de descoberta de telejornais estaduais.

    O coletor mantém a lista completa de aliases para pontuar links e títulos.
    Apenas a lista de páginas de busca que ele consulta fica limitada a duas
    (termo principal + no máximo um alias). O método original é sempre
    restaurado, mesmo quando a rede lança uma exceção.
    """
    collect = collector.collect
    discovery = getattr(collector, "_discovery_urls", None)
    if not _is_state_specific_regional_source(source) or not callable(discovery):
        return collect(source, captured_at, from_ms, to_ms, on_error)

    namespace = getattr(collector, "__dict__", {})
    had_instance_override = "_discovery_urls" in namespace
    previous_instance_override = namespace.get("_discovery_urls")

    def bounded_discovery(current_source):
        urls = discovery(current_source)
        if _is_state_specific_regional_source(current_source):
            return urls[:REGIONAL_EDITION_DISCOVERY_URL_LIMIT]
        return urls

    collector._discovery_urls = bounded_discovery
    try:
        return collect(source, captured_at, from_ms, to_ms, on_error)
    finally:
        if had_instance_override:
            collector._discovery_urls = previous_instance_override
        else:
            try:
                delattr(collector, "_discovery_urls")
            except AttributeError:
                pass


def collect_recent_by_source(repo, source, captured_at, from_ms, to_ms, on_error):
    if source.youtubeHandle.strip():
        try:
            items = repo.youtube.collect(source, captured_at)
        except Exception:
            on_error("YouTube • feed/canal")
            items = []
        if items:
            return list({canonical_key(item.link): item for item in items}.values())
        try:
            return list({
                canonical_key(item.link): item
                for item in repo.website.fetch_website(source, captured_at)
            }.values())
        except Exception:
            on_error("YouTube • página")
            return []

    if is_globoplay_source(source):
        try:
            editions = _collect_editions_with_regional_limit(
                repo.editions,
                source,
                captured_at,
                from_ms,
                to_ms,
                lambda: on_error("Globoplay • Edições"),
            )
        except Exception:
            on_error("Globoplay • Edições")
            editions = []

        if source.id in CORE_NATIONAL_GLOBOPLAY_IDS:
            try:
                scenes = repo.trechos.collect(
                    source, captured_at, lambda: on_error("Globoplay • Trechos")
                )
            except Exception:
                on_error("Globoplay • Trechos")
                scenes = []
            combined = list({
                canonical_key(item.link): item for item in [*editions, *scenes]
            }.values())
            if combined:
                return combined
        elif editions:
            return list({canonical_key(item.link): item for item in editions}.values())
        else:
            try:
                scenes = repo.trechos.collect(
                    source, captured_at, lambda: on_error("Globoplay • Trechos")
                )
            except Exception:
                on_error("Globoplay • Trechos")
                scenes = []
            if scenes:
                return list({canonical_key(item.link): item for item in scenes}.values())

        try:
            if source.searchPrefix.strip() and source.searchUrlTemplate.strip():
                primary = repo.website.fetch_search_website(source, "", captured_at)
            else:
                primary = repo.website.fetch_website(source, captured_at)
            return list({canonical_key(item.link): item for item in primary}.values())
        except Exception:
            on_error("Globoplay • busca fallback")
            return []

    if source.id in PORTAL_PROGRAM_SCAN_IDS:
        try:
            landing = repo.website.fetch_website(source, captured_at)
        except Exception:
            on_error("Portal • página do programa")
            landing = []
        if landing:
            return list({canonical_key(item.link): item for item in landing}.values())
        if source.searchUrlTemplate.strip() and source.searchPrefix.strip():
            try:
                fallback = repo.website.fetch_search_website(source, "", captured_at)
                return list({canonical_key(item.link): item for item in fallback}.values())
            except Exception:
                on_error("Portal • busca fallback")
        return []

    try:
        return list({canonical_key(item.link): item for item in repo.website.fetch_website(source, captured_at)}.values())
    except Exception:
        on_error("Portal • página")
        return []


def collect_for_query(repo, source, query, captured_at, on_error):
    searched = []
    if source.searchUrlTemplate.strip():
        try:
            searched = repo.website.fetch_search_website(source, query, captured_at)
        except Exception:
            on_error("Busca por termo")
    return searched
