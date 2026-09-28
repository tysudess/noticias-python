from __future__ import annotations

from datetime import date

from monitor_noticias.digital_newspapers.providers import (
    DIGITAL_NEWSPAPER_PROVIDERS,
    CorreioBrazilienseProvider,
    EstadoMinasProvider,
    EstadaoProvider,
    FolhaProvider,
    GloboProvider,
    ValorProvider,
    ATardeProvider,
    GZHProvider,
    GazetaPovoProvider,
    NYTimesProvider,
    WashingtonPostProvider,
    get_provider,
)


def test_v77_catalog_has_all_requested_newspapers():
    ids = {provider.id for provider in DIGITAL_NEWSPAPER_PROVIDERS}

    assert {
        "estadao",
        "folha",
        "o-globo",
        "correio-braziliense",
        "valor-economico",
        "a-tarde",
        "estado-de-minas",
        "gzh-zero-hora",
        "gazeta-revista",
        "new-york-times",
        "washington-post",
    }.issubset(ids)


def test_provider_ids_are_unique():
    ids = [provider.id for provider in DIGITAL_NEWSPAPER_PROVIDERS]
    assert len(ids) == len(set(ids))


def test_official_pdf_providers_are_explicit():
    assert get_provider("correio-braziliense").official_pdf_documented
    assert get_provider("estado-de-minas").official_pdf_documented
    assert get_provider("gazeta-revista").official_pdf_documented


def test_washington_post_does_not_offer_desktop_full_download():
    provider = get_provider("washington-post")
    assert provider.download_strategy == "app_only"
    assert not provider.can_try_download


def test_output_filename_is_stable_and_pdf():
    provider = get_provider("estado-de-minas")
    assert (
        provider.output_filename(date(2026, 9, 28))
        == "estado-de-minas-2026-09-28.pdf"
    )


def test_provider_domain_matching_accepts_subdomains_only():
    provider = get_provider("folha")
    assert provider.domain_allowed("edicaodigital.folha.uol.com.br")
    assert provider.domain_allowed("www1.folha.uol.com.br")
    assert not provider.domain_allowed("example.com")


def test_each_newspaper_has_its_own_adapter_class():
    expected_types = {
        CorreioBrazilienseProvider,
        EstadoMinasProvider,
        EstadaoProvider,
        FolhaProvider,
        GloboProvider,
        ValorProvider,
        ATardeProvider,
        GZHProvider,
        GazetaPovoProvider,
        NYTimesProvider,
        WashingtonPostProvider,
    }
    assert {type(provider) for provider in DIGITAL_NEWSPAPER_PROVIDERS} == expected_types
