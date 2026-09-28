from __future__ import annotations

from monitor_noticias.models import MediaSource


_SOURCE_ID = "ba-tribuna-da-bahia"
_SOURCE_NAME = "Tribuna da Bahia"


def _tribuna_source() -> MediaSource:
    return MediaSource(
        id=_SOURCE_ID,
        name=_SOURCE_NAME,
        region="Nordeste",
        state="BA",
        stateName="Bahia",
        group="Bahia • Nordeste",
        aliases=[
            "Tribuna Bahia",
            "Jornal Tribuna da Bahia",
        ],
    )


def install_sources_bahia_catalog_patch() -> None:
    """V75 — adiciona Tribuna da Bahia ao catálogo REAL antes do AppContainer.

    O AppContainer importa NEWS_SOURCES/BY_STATE de ui.catalog durante a sua
    importação. Portanto este patch precisa rodar ANTES de importar
    monitor_noticias.app.composition.
    """

    from monitor_noticias.ui import catalog

    if any(
        getattr(source, "id", "") == _SOURCE_ID
        for source in catalog.NEWS_SOURCES
    ):
        return

    source = _tribuna_source()

    catalog.BY_STATE = tuple(
        list(catalog.BY_STATE)
        + [source]
    )

    catalog.NEWS_SOURCES = tuple(
        dict(
            (
                item.id,
                item,
            )
            for item in (
                tuple(catalog.NATIONAL)
                + tuple(catalog.BY_STATE)
                + tuple(catalog.SPECIALIZED)
            )
        ).values()
    )


def install_sources_bahia_patch(window) -> None:
    """Compatibilidade com a chamada antiga da V73.

    A fonte já foi adicionada ao catálogo antes da criação do AppContainer.
    Não é mais necessário injetar nada visualmente.
    """
    return
