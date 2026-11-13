import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_runtime_alias_points_to_existing_versioned_runtime():
    alias = _read(
        "tools/news_extractor/engine/extrator-materia-v1.25.10-runtime.js"
    )
    match = re.search(
        r"module\.exports\s*=\s*require\(\s*['\"]\./([^'\"]+-runtime\.js)['\"]\s*\)",
        alias,
    )

    assert match, "O alias não contém um require válido para o runtime ativo."
    target_name = match.group(1)
    target = (
        ROOT
        / "tools/news_extractor/engine"
        / target_name
    )
    assert target.is_file(), (
        f"O alias aponta para {target_name}, mas esse runtime não existe."
    )


def test_uol_runtime_checks_split_article_blocks():
    source = _read(
        "tools/news_extractor/engine/extrator-materia-v1.25.20-runtime.js"
    )

    assert "extrairCorpoUolDoHtml" in source
    assert "encontrarInicio" in source
    assert "continua ap[oó]s a publicidade" in source
    assert "ehBlocoTerminalUol" in source
    assert "uol-dom-multiblocos" in source


def test_uol_runtime_does_not_hide_subscription_restriction():
    source = _read(
        "tools/news_extractor/engine/extrator-materia-v1.25.20-runtime.js"
    )

    assert "paginaMarcaSoAssinantes" in source
    assert "Só para assinantes" in source
    assert "o extrator não contorna o acesso do site" in source


def test_uol_completeness_fallback_is_bounded():
    source = _read(
        "tools/news_extractor/engine/extrator-materia-v1.25.20-runtime.js"
    )

    assert "timeoutMs: 18000" in source
    assert "tentativas: 1" in source
    assert "pareceUolIncompleto" in source
