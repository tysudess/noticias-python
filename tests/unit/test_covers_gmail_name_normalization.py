from monitor_noticias.capas_tool.app.paper_names import (
    canonical_paper_name,
    normalize_matters_payload,
)


def test_canonical_names_ignore_accents_case_punctuation_and_spacing():
    assert canonical_paper_name("Folha de Sao Paulo") == "FOLHA DE SÃO PAULO"
    assert canonical_paper_name("estadao") == "ESTADÃO"
    assert canonical_paper_name("  O   GLOBO  ") == "O GLOBO"


def test_known_editorial_aliases_map_to_the_existing_newspaper_entries():
    assert canonical_paper_name("O Estado de S. Paulo") == "ESTADÃO"
    assert canonical_paper_name("NYT") == "THE NEW YORK TIMES"
    assert canonical_paper_name("Correio de Brasília") == "CORREIO BRAZILIENSE"


def test_alias_groups_merge_without_losing_distinct_matter_urls():
    mapped, unknown, aliases = normalize_matters_payload({
        "Folha de Sao Paulo": ["https://example.test/a", "https://example.test/b"],
        "FOLHA DE SÃO PAULO": ["https://example.test/b", "https://example.test/c"],
        "ESTADAO": ["https://example.test/e"],
    })
    assert mapped["FOLHA DE SÃO PAULO"] == [
        "https://example.test/a",
        "https://example.test/b",
        "https://example.test/c",
    ]
    assert mapped["ESTADÃO"] == ["https://example.test/e"]
    assert not unknown
    assert "Folha de Sao Paulo" in aliases


def test_unknown_newspaper_names_are_preserved_for_diagnostics():
    mapped, unknown, _aliases = normalize_matters_payload({
        "JORNAL NOVO": ["https://example.test/x"],
    })
    assert not mapped
    assert unknown == {"JORNAL NOVO": ["https://example.test/x"]}


def test_empty_or_malformed_payloads_do_not_crash():
    assert normalize_matters_payload(None) == ({}, {}, [])
    assert normalize_matters_payload([]) == ({}, {}, [])


def test_valor_and_washington_post_are_not_silently_added_to_the_gmail_group():
    mapped, unknown, _aliases = normalize_matters_payload({
        "Valor Econômico": ["https://example.test/valor"],
        "The Washington Post": ["https://example.test/post"],
    })
    assert not mapped
    assert set(unknown) == {"Valor Econômico", "The Washington Post"}
