from __future__ import annotations

import ast
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[2]
PRESSREADER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "pressreader_hd.py"
PROVIDERS = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "providers.py"
BROWSER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "browser.py"


def _selected_functions(path: Path, names: set[str]) -> dict:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    mod = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {
        "re": re,
        "urlsplit": urlsplit,
        "parse_qsl": parse_qsl,
    }
    exec(compile(mod, str(path), "exec"), ns)
    return ns


def _function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(name)


def test_v86_pressreader_extracts_page_and_total_from_viewer_text():
    ns = _selected_functions(
        PRESSREADER,
        {"pressreader_image_page_number", "pressreader_total_pages_from_text"},
    )
    page_number = ns["pressreader_image_page_number"]
    total_pages = ns["pressreader_total_pages_from_text"]

    raw = "https://i.prcdn.co/img?file=abcdef&page=35&scale=104&issue=20260929"
    assert page_number(raw) == 35
    assert total_pages("Valor Econômico 29 Setembro 2026 · 35 de 38") == 38
    assert total_pages("O Globo 1 of 44") == 44


def test_v86_keeps_multiple_image_files_for_same_page():
    browser = BROWSER.read_text(encoding="utf-8")
    probe = _function_source(BROWSER, "_pressreader_probe_result")
    seen = _function_source(BROWSER, "_request_resource_seen")

    assert "self._pressreader_candidates" in browser
    assert "bucket = self._pressreader_candidates.setdefault(page_number, {})" in seen
    assert "self._valor_image_urls[page_number] = tuple(" in probe
    assert "len(ordered)" in probe


def test_v86_worker_tries_multiple_raw_files_before_quality_failure():
    source = _function_source(PRESSREADER, "_download_best_image")
    assert "for raw_url in raw_urls" in source
    assert "pressreader_image_variants(raw_url)" in source
    assert "per_source_best" in source
    assert "próximo `file=` capturado" in source


def test_v86_saved_credentials_auto_submit_on_manual_renewal():
    browser = BROWSER.read_text(encoding="utf-8")
    prepare = _function_source(BROWSER, "prepare_manual_login")
    loaded = _function_source(BROWSER, "_load_finished")

    assert "self._manual_login_auto_submit = self.credential_store.exists()" in prepare
    assert "or self._manual_login_auto_submit" in loaded
    assert "Acesso salvo detectado" in loaded


def test_v86_o_globo_uses_pressreader_hd_route_from_observed_viewer():
    source = PROVIDERS.read_text(encoding="utf-8")
    start = source.index("class GloboProvider")
    end = source.index("class ValorProvider", start)
    globo = source[start:end]

    assert 'edition_url="https://infoglobo.pressreader.com/o-globo"' in globo
    assert 'download_strategy="pressreader_hd_images"' in globo
    assert '"{yyyymmdd}/page/{page}"' in globo
    assert '"prcdn.co"' in globo
