from __future__ import annotations

from collections.abc import Iterable

from monitor_noticias.models import MediaSource


VEJA_SOURCE = MediaSource(
    id="nacional-veja",
    name="VEJA",
    region="Nacional",
    state="BR",
    stateName="Brasil",
    group="Jornais nacionais",
    aliases=["Veja", "Revista VEJA", "Veja.com", "veja.abril.com.br"],
)

VEJA_LATEST_ROUTE = (
    "https://veja.abril.com.br/ultimas-noticias/",
    {"veja.abril.com.br"},
)


def register_veja_latest_route() -> None:
    """Registra a listagem oficial da VEJA no coletor de últimas notícias."""
    from .latest import ROUTES

    ROUTES.setdefault(VEJA_SOURCE.id, VEJA_LATEST_ROUTE)


def extend_news_catalog(
    national_sources: Iterable[MediaSource],
    all_news_sources: Iterable[MediaSource],
) -> tuple[tuple[MediaSource, ...], tuple[MediaSource, ...]]:
    """Inclui VEJA no catálogo efetivo de notícias, sem duplicar seu ID."""
    national = tuple(
        source for source in national_sources if source.id != VEJA_SOURCE.id
    ) + (VEJA_SOURCE,)
    remaining_sources = [
        source for source in all_news_sources if source.id != VEJA_SOURCE.id
    ]
    # NEWS_SOURCES começa pelos veículos nacionais e depois lista fontes
    # estaduais/especializadas. Insere VEJA no bloco nacional, não no final.
    insert_at = next(
        (index for index, source in enumerate(remaining_sources)
         if source.group != VEJA_SOURCE.group),
        len(remaining_sources),
    )
    remaining_sources.insert(insert_at, VEJA_SOURCE)
    all_sources = tuple(remaining_sources)
    register_veja_latest_route()
    return national, all_sources
