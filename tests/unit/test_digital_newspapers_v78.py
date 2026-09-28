from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

from monitor_noticias.digital_newspapers.providers import (
    CorreioBrazilienseProvider,
    get_provider,
)


ROOT = Path(__file__).resolve().parents[2]


def test_v78_correio_uses_official_direct_pdf_for_selected_date():
    provider = CorreioBrazilienseProvider()

    assert provider.supports_direct_pdf
    assert (
        provider.direct_pdf_url(date(2026, 9, 27))
        == "https://edicao.correiobraziliense.com.br/"
        "correiobraziliense/2026/09/27/all.pdf"
    )


def test_v78_direct_pdf_is_still_limited_to_declared_provider():
    assert get_provider("correio-braziliense").supports_direct_pdf
    assert not get_provider("folha").supports_direct_pdf
    assert not get_provider("estado-de-minas").supports_direct_pdf


def test_v78_normal_download_current_does_not_open_dialog():
    source_path = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "ui"
        / "digital_newspapers_page.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "download_current":
                target = node
                break

    assert target is not None

    source = ast.get_source_segment(
        source_path.read_text(encoding="utf-8"),
        target,
    ) or ""

    assert "dialog.show(" not in source
    assert "dialog.raise_(" not in source
    assert "dialog.activateWindow(" not in source
    assert "dialog.start_automatic_download(" in source


def test_v78_windows_spec_embeds_new_program_icon():
    spec = (ROOT / "MonitorDeNoticias.spec").read_text(encoding="utf-8")

    assert "APP_ASSETS" in spec
    assert 'icon=str(APP_ASSETS / "app_icon.ico")' in spec
    assert "+ app_datas" in spec


def test_v78_app_icon_assets_are_present():
    assets = ROOT / "src" / "monitor_noticias" / "assets"

    assert (assets / "app_icon.png").is_file()
    assert (assets / "app_icon.ico").is_file()
    assert (assets / "app_icon.png").stat().st_size > 100_000
    assert (assets / "app_icon.ico").stat().st_size > 20_000
