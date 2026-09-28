from monitor_noticias.ui.sources_bahia_patch import (
    install_sources_bahia_catalog_patch,
)


def test_tribuna_da_bahia_enters_real_catalog():
    from monitor_noticias.ui import catalog

    install_sources_bahia_catalog_patch()

    matches = [
        source
        for source in catalog.NEWS_SOURCES
        if source.id == "ba-tribuna-da-bahia"
    ]

    assert len(matches) == 1

    source = matches[0]

    assert source.name == "Tribuna da Bahia"
    assert source.state == "BA"
    assert source.stateName == "Bahia"
    assert source.region == "Nordeste"
    assert "Tribuna Bahia" in source.aliases


def test_patch_is_idempotent():
    from monitor_noticias.ui import catalog

    install_sources_bahia_catalog_patch()
    install_sources_bahia_catalog_patch()

    assert sum(
        1
        for source in catalog.NEWS_SOURCES
        if source.id == "ba-tribuna-da-bahia"
    ) == 1
