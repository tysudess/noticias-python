from __future__ import annotations

from dataclasses import replace

from monitor_noticias.automation.models import LiveSearchProgress
from monitor_noticias.database.default_terms import DEFAULT_MONITOR_TERMS
from monitor_noticias.collectors.video.catalog import CORE_NATIONAL_GLOBOPLAY_IDS, GLOBOPLAY_REGIONAL_SWEEP_IDS, PORTAL_PROGRAM_SCAN_IDS
from monitor_noticias.matching.video_rules import canonical_key, canonicalize_url, in_period, is_globoplay_source, is_specific_video_url, is_youtube_url, is_youtube_video_url, merge_video, phrase_matches, prioritize_globoplay_candidates, source_matches_demand, useful_title
from .video_collect import collect_for_query, collect_recent_by_source, is_source_scan_mode
from .video_types import VideoSearchResult, VideoSourceIssue

DEFAULT_VIDEO_WINDOW_MS = 24 * 60 * 60 * 1000
MAX_REQUEST_FAILURES_PER_SOURCE = 3
MAX_RESOLVED_PER_QUERY = 8
MAX_GLOBOPLAY_ITEMS_PER_SCAN = 40
MAX_GLOBOPLAY_GENERAL_ITEMS_PER_SCAN = 48
MAX_GLOBOPLAY_NATIONAL_ITEMS_PER_SCAN = 72
MAX_GLOBOPLAY_DEEP_FALLBACK_PER_SOURCE = 12
MAX_GLOBOPLAY_DEEP_FALLBACK_GENERAL = 14
MAX_GLOBOPLAY_DEEP_FALLBACK_NATIONAL = 72
MAX_YOUTUBE_ITEMS_PER_SCAN = 40
MAX_PORTAL_PROGRAM_ITEMS_PER_SCAN = 40
# A busca interna é usada apenas como fallback para fontes nacionais que não
# encontraram termos/demandas no HTML inicial. As regionais ficam para a etapa
# seguinte de otimização específica, evitando ampliar agora a carga de rede.
MAX_NATIONAL_PORTAL_FALLBACK_TERMS = 6
NATIONAL_PORTAL_FALLBACK_IDS = {
    "video-globoplay-jornalismo",
    "video-r7-record",
    "video-sbt-news",
    "video-band",
    "video-band-jornal-da-band",
    "video-band-brasil-urgente",
    "video-r7-jornal-da-record",
    "video-r7-domingo-espetacular",
}


def _resolve_limit(source):
    if source.youtubeHandle.strip(): return MAX_YOUTUBE_ITEMS_PER_SCAN
    if source.id in CORE_NATIONAL_GLOBOPLAY_IDS: return MAX_GLOBOPLAY_NATIONAL_ITEMS_PER_SCAN
    if source.id == "video-globoplay-jornalismo": return MAX_GLOBOPLAY_GENERAL_ITEMS_PER_SCAN
    if source.id in GLOBOPLAY_REGIONAL_SWEEP_IDS: return MAX_GLOBOPLAY_GENERAL_ITEMS_PER_SCAN
    if is_globoplay_source(source): return MAX_GLOBOPLAY_ITEMS_PER_SCAN
    if source.id in PORTAL_PROGRAM_SCAN_IDS: return MAX_PORTAL_PROGRAM_ITEMS_PER_SCAN
    return MAX_RESOLVED_PER_QUERY


def _deep_limit(source):
    if source.id in CORE_NATIONAL_GLOBOPLAY_IDS: return MAX_GLOBOPLAY_DEEP_FALLBACK_NATIONAL
    if source.id == "video-globoplay-jornalismo" or source.id in GLOBOPLAY_REGIONAL_SWEEP_IDS: return MAX_GLOBOPLAY_DEEP_FALLBACK_GENERAL
    if is_globoplay_source(source): return MAX_GLOBOPLAY_DEEP_FALLBACK_PER_SOURCE
    return 0


def _direct(source, item):
    if not useful_title(item.title): return False
    if is_youtube_url(item.link): return is_youtube_video_url(item.link)
    return is_specific_video_url(source, item.link)


def _matches_any_watch_item(source, items, terms, demands):
    """True quando o HTML inicial já tem ao menos um candidato monitorável."""
    for item in items:
        body = f"{item.title} {item.summary}"
        if any(phrase_matches(body, term) for term in terms):
            return True
        if any(
            source_matches_demand(source, demand.vehicle)
            and phrase_matches(body, demand.subject)
            for demand in demands
        ):
            return True
    return False


def _national_portal_fallback_queries(source, terms, demands):
    """Prioriza demandas e termos próprios; depois usa a ordem base do catálogo."""
    values = []
    seen = set()

    def add(raw):
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            values.append(value)

    for demand in demands:
        if source_matches_demand(source, demand.vehicle):
            add(demand.subject)

    default_keys = {str(value).casefold() for value in DEFAULT_MONITOR_TERMS}
    # Termos adicionados pelo usuário ou herdados de Notícias vêm antes dos
    # defaults, pois representam a configuração específica desta instalação.
    for term in terms:
        if str(term or "").strip().casefold() not in default_keys:
            add(term)
    # Mantém a ordem intencional do catálogo padrão, não a ordem alfabética da
    # persistência, para tentar primeiro as palavras-chave mais centrais.
    current_by_key = {str(term).strip().casefold(): term for term in terms if str(term).strip()}
    for default in DEFAULT_MONITOR_TERMS:
        value = current_by_key.get(str(default).casefold())
        if value is not None:
            add(value)
    for term in terms:
        add(term)
    return values[:MAX_NATIONAL_PORTAL_FALLBACK_TERMS]


def _collect_national_portal_fallback(repo, source, candidates, terms, demands, captured, cancel, on_error):
    """Tenta a busca interna se o resultado inicial não contém correspondências.

    Isso corrige o caso em que uma página de vídeos tem conteúdo, porém nenhum
    dos itens listados corresponde aos termos cadastrados: antes, a página não
    vazia impedia qualquer consulta ao mecanismo de busca do próprio portal.
    """
    if source.id not in NATIONAL_PORTAL_FALLBACK_IDS:
        return candidates
    if str(getattr(source, "region", "Nacional") or "Nacional") != "Nacional":
        return candidates
    if not source.searchUrlTemplate.strip():
        return candidates
    if _matches_any_watch_item(source, candidates, terms, demands):
        return candidates

    original_by_link = {canonical_key(item.link): item for item in candidates}
    fallback_by_link = {}
    for query in _national_portal_fallback_queries(source, terms, demands):
        if cancel:
            cancel()
        try:
            found = repo.website.fetch_search_website(source, query, captured)
        except Exception:
            on_error("Busca interna • fallback nacional")
            continue
        for item in found:
            body = f"{item.title} {item.summary}"
            synthetic_title = str(item.title or "").strip().lower().startswith(
                ("vídeo recente", "video recente", "trecho recente")
            )
            if not phrase_matches(body, query) and not synthetic_title:
                continue
            if not _direct(source, item):
                continue
            fallback_by_link.setdefault(canonical_key(item.link), item)
    # Resultados da busca interna vêm primeiro, já que a listagem inicial foi
    # considerada sem correspondências e não deve ocupar o limite de resolução.
    merged = dict(fallback_by_link)
    for key, item in original_by_link.items():
        merged.setdefault(key, item)
    return list(merged.values())


def perform_video_search(repo, sources, from_ms, to_ms, on_update, cancel):
    news_terms = repo.news_db.listTerms()
    terms = repo.term_store.load(news_terms)
    demands = [item for item in repo.news_db.listDemands() if item.active]
    captured = repo.now_ms(); started = captured
    effective_to = captured if to_ms is None else to_ms
    effective_from = effective_to - DEFAULT_VIDEO_WINDOW_MS if from_ms is None else from_ms
    collected = {}; new_keys = set(); unstable = {}; completed = 0

    plan = {}
    for source in sources:
        if is_source_scan_mode(source):
            plan[source.id] = [("", "", None)]
        else:
            specs = [(term, term, None) for term in terms]
            specs += [(d.subject, "", d) for d in demands if source_matches_demand(source, d.vehicle)]
            unique = {}; [unique.setdefault((q.lower().strip(), term, d.id if d else 0), (q,term,d)) for q,term,d in specs]
            plan[source.id] = list(unique.values())
    total = sum(len(value) for value in plan.values())
    errors = 0

    def progress(source_name, query, active=True):
        return LiveSearchProgress(active=active, kind="Vídeos • Período" if from_ms is not None or to_ms is not None else "Vídeos", startedAt=started, finishedAt=0 if active else repo.now_ms(), completed=completed, total=total, currentSource=source_name, currentQuery=query, found=len(collected), newCount=len(new_keys), errors=errors)

    def emit(source_name, query, items=(), active=True):
        if on_update: on_update(progress(source_name, query, active), tuple(items))

    national_globoplay = [source for source in sources if source.id in CORE_NATIONAL_GLOBOPLAY_IDS]
    jarvis_queries = list(dict.fromkeys([*terms, *[d.subject for d in demands if any(source_matches_demand(source,d.vehicle) for source in national_globoplay)]]))
    if national_globoplay and jarvis_queries:
        try: jarvis = repo.jarvis.collect(jarvis_queries, national_globoplay, captured)
        except Exception: jarvis = None
    else: jarvis = None

    emit("Preparando", "")
    for source in sources:
        if cancel: cancel()
        failures = []; cache = {}; scan = is_source_scan_mode(source)

        def source_error(stage): failures.append(stage)

        scan_candidates = collect_recent_by_source(repo, source, captured, effective_from, effective_to, source_error) if scan else []
        if source.id in CORE_NATIONAL_GLOBOPLAY_IDS and jarvis is not None:
            scan_candidates = list({canonical_key(item.link):item for item in [*(jarvis.candidatesBySourceId.get(source.id,[]) or []),*scan_candidates]}.values())

        # Evita perder resultados quando a página inicial tem vídeos, mas não
        # retorna nenhum que corresponda aos termos monitorados. Por ora, esse
        # fallback automático é restrito aos portais nacionais; a varredura
        # regional será otimizada em uma etapa própria.
        if scan:
            scan_candidates = _collect_national_portal_fallback(
                repo, source, scan_candidates, terms, demands, captured, cancel, source_error
            )

        specs = plan.get(source.id, [])
        for query, term, demand_spec in specs:
            if cancel: cancel()
            if not scan and len(failures) >= MAX_REQUEST_FAILURES_PER_SOURCE:
                unstable[source.id] = VideoSourceIssue(source.id, source.name, len(failures), max(set(failures), key=failures.count) if failures else "HTTP/rede")
                completed += 1; emit(source.name,"Fonte instável • consultas restantes ignoradas"); continue
            label = query if not scan else ("Edições + Trechos + Jarvis • cruzamento local" if source.id in CORE_NATIONAL_GLOBOPLAY_IDS else "Vídeos recentes • cruzamento local")
            emit(source.name,label)
            raw = scan_candidates if scan else collect_for_query(repo, source, query, captured, source_error)
            if not scan:
                filtered = [item for item in raw if phrase_matches(f"{item.title} {item.summary}", query)]
                if not filtered:
                    try: filtered = [item for item in repo.website.fetch_website(source,captured) if phrase_matches(f"{item.title} {item.summary}",query)]
                    except Exception: source_error("Busca por termo"); filtered = []
                raw = filtered
            candidates = prioritize_globoplay_candidates(raw,source,terms,demands) if is_globoplay_source(source) else raw
            deep = 0
            for original in candidates[:_resolve_limit(source)]:
                if cancel: cancel()
                # Primeiro filtramos datas já conhecidas para não baixar páginas
                # individuais de vídeos que certamente não pertencem ao período.
                # Itens sem data (0) continuam elegíveis para enriquecimento na
                # página individual; nunca serão tratados como publicados agora.
                if original.publishedAt > 0 and not in_period(original, effective_from, effective_to):
                    continue
                globoplay_scan = scan and is_globoplay_source(source)
                shallow_body = f"{original.title} {original.summary}"
                shallow_term = globoplay_scan and any(phrase_matches(shallow_body,value) for value in terms)
                shallow_demand = globoplay_scan and any(source_matches_demand(source,d.vehicle) and phrase_matches(shallow_body,d.subject) for d in demands)
                if globoplay_scan and not shallow_term and not shallow_demand:
                    if deep >= _deep_limit(source): continue
                    deep += 1
                if globoplay_scan and (shallow_term or shallow_demand) and original.publishedAt > 0 and useful_title(original.title) and is_specific_video_url(source,original.link):
                    item = replace(original,link=canonicalize_url(original.link))
                else:
                    key0 = canonical_key(original.link)
                    if key0 not in cache:
                        try: cache[key0] = repo.direct.resolve(source,original,captured)
                        except Exception: cache[key0] = None; source_error("Abrir página do vídeo") if not is_globoplay_source(source) else None
                    item = cache[key0]
                    if item is None and is_globoplay_source(source) and useful_title(original.title) and is_specific_video_url(source,original.link): item = replace(original,link=canonicalize_url(original.link))
                    if item is None: continue
                body = f"{item.title} {item.summary}"
                if not in_period(item,effective_from,effective_to) or not _direct(source,item): continue
                actual_terms = [value for value in terms if phrase_matches(body,value)]
                matched_demands = [d for d in demands if source_matches_demand(source,d.vehicle) and phrase_matches(body,d.subject)]
                if not scan and not phrase_matches(body,query): continue
                key = canonical_key(item.link); previous = collected.get(key)
                matched_term = ", ".join(actual_terms) if actual_terms else (term if term and phrase_matches(body,term) else (previous.matchedTerm if previous else ""))
                if matched_demands: matched_demand = f"{matched_demands[0].vehicle} • {matched_demands[0].subject}"
                elif demand_spec is not None and phrase_matches(body,demand_spec.subject): matched_demand = f"{demand_spec.vehicle} • {demand_spec.subject}"
                else: matched_demand = previous.matchedDemand if previous else ""
                candidate = replace(item,link=canonicalize_url(item.link),matchedTerm=matched_term,matchedDemand=matched_demand,capturedAt=captured)
                if not candidate.relevant: continue
                merged = candidate if previous is None else merge_video(previous,candidate)
                collected[key] = merged
                if repo.db.insert([merged]): new_keys.add(key)
                emit(source.name,label,[merged])
            completed += 1; emit(source.name,label)
        if scan and not scan_candidates and failures:
            actionable = (source.youtubeHandle.strip() and len(failures)>=2) or (is_globoplay_source(source) and len(failures)>=2) or (source.id in PORTAL_PROGRAM_SCAN_IDS and len(set(failures))>=2)
            if actionable:
                unstable[source.id] = VideoSourceIssue(source.id,source.name,len(failures),max(set(failures),key=failures.count))
    errors = len(unstable)
    items = tuple(sorted([item for key,item in collected.items() if item.relevant and in_period(item,effective_from,effective_to)], key=lambda item:item.publishedAt, reverse=True))
    emit("Concluído","",active=False)
    issues = tuple(sorted(unstable.values(),key=lambda item:item.sourceName.lower()))
    return VideoSearchResult(items,len(items),len(new_keys),len(items),len(new_keys),len(issues),issues,tuple(new_keys))
