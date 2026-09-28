from __future__ import annotations

import struct
from datetime import date
from pathlib import Path

from monitor_noticias.digital_newspapers.providers import (
    get_provider,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET_DATE = date(2026, 9, 28)


def test_v80_uses_the_real_reader_entry_points():
    assert get_provider("estadao").edition_urls(TARGET_DATE)[0] == (
        "https://digital.estadao.com.br/o-estado-de-s-paulo/20260928"
    )
    assert get_provider("estado-de-minas").edition_urls(TARGET_DATE)[0] == (
        "https://digital.em.com.br/estadodeminas/28/09/2026/p1"
    )
    assert get_provider("o-globo").edition_url == (
        "https://jornaldigital.oglobo.globo.com/"
    )
    assert get_provider("valor-economico").edition_url == (
        "https://jornaldigital.valor.globo.com/"
    )
    assert get_provider("a-tarde").edition_url == (
        "https://flip.atarde.com.br/edicaodehoje/"
    )
    assert get_provider("gzh-zero-hora").edition_urls(TARGET_DATE)[0] == (
        "https://flipzh.clicrbs.com.br/jornal-digital/pub/gruporbs/"
        "?numero=20260928"
    )
    assert get_provider("new-york-times").edition_url == (
        "https://eeditionnytimes.newspaperdirect.com/epaper/viewer.aspx"
    )


def test_v80_folha_has_both_current_digital_entry_points():
    urls = get_provider("folha").edition_urls(TARGET_DATE)
    assert "https://acervo.folha.uol.com.br/digital/index.do" in urls
    assert "https://edicaodigital.folha.uol.com.br/" in urls


def test_v80_gzh_preserves_login_domain_session():
    provider = get_provider("gzh-zero-hora")
    assert provider.domain_allowed("www.gauchazh.com.br")
    assert provider.domain_allowed("gauchazh.clicrbs.com.br")
    assert provider.domain_allowed("flipzh.clicrbs.com.br")


def test_v80_browser_discovers_nested_viewers_and_retries_entries():
    source = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "browser.py"
    ).read_text(encoding="utf-8")

    assert "iframe[src]" in source
    assert "mode:'navigate'" in source
    assert "login_required" in source
    assert "def _advance_auto_entry(" in source
    assert "def _navigation_allowed(" in source
    assert "self._auto_navigation_depth < 5" in source
    assert "self.provider.edition_urls(self.target_date)" in source


def test_v80_preserves_v79_correio_pagewise_rebuild():
    provider = get_provider("correio-braziliense")
    source = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "browser.py"
    ).read_text(encoding="utf-8")

    assert provider.supports_pagewise_pdf
    assert "PDF oficial remontado página a página" in source
    assert "faltaram páginas na sequência" in source


def test_v80_keeps_multi_resolution_windows_icon():
    path = ROOT / "src" / "monitor_noticias" / "assets" / "app_icon.ico"
    data = path.read_bytes()
    reserved, ico_type, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0
    assert ico_type == 1
    assert count >= 6

    sizes: set[tuple[int, int]] = set()
    for index in range(count):
        entry = data[6 + index * 16 : 6 + (index + 1) * 16]
        width, height, _colors, _r, _planes, _bpp, _size, _offset = struct.unpack(
            "<BBBBHHII", entry
        )
        sizes.add((width or 256, height or 256))

    assert {(16, 16), (32, 32), (48, 48), (256, 256)}.issubset(sizes)


def test_washington_post_remains_app_only():
    provider = get_provider("washington-post")
    assert provider.download_strategy == "app_only"
    assert not provider.can_try_download
