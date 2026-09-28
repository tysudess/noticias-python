from __future__ import annotations

import struct
from datetime import date
from pathlib import Path

from monitor_noticias.digital_newspapers.providers import (
    CorreioBrazilienseProvider,
)


ROOT = Path(__file__).resolve().parents[2]


def test_v79_correio_keeps_direct_pdf_and_adds_pagewise_templates():
    provider = CorreioBrazilienseProvider()

    assert provider.supports_direct_pdf
    assert provider.supports_pagewise_pdf
    assert (
        provider.direct_pdf_url(date(2026, 9, 28))
        == "https://edicao.correiobraziliense.com.br/"
        "correiobraziliense/2026/09/28/all.pdf"
    )

    urls = provider.page_pdf_urls(date(2026, 9, 28), 3)
    assert (
        "https://edicao.correiobraziliense.com.br/"
        "correiobraziliense/2026/09/28/3.pdf"
    ) in urls
    assert (
        "https://edicao.correiobraziliense.com.br/"
        "correiobraziliense/2026/09/28/03.pdf"
    ) in urls


def test_v79_browser_has_pagewise_rebuild_logic_before_integral_fallback():
    source = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "browser.py"
    ).read_text(encoding="utf-8")

    assert "def _try_pagewise_pdf_build(" in source
    assert "PDF oficial remontado página a página" in source
    assert "Tentando o PDF integral oficial" in source
    assert "faltaram páginas na sequência" in source


def test_v79_windows_icon_is_multi_resolution_ico():
    path = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "assets"
        / "app_icon.ico"
    )
    data = path.read_bytes()
    reserved, ico_type, count = struct.unpack("<HHH", data[:6])

    assert reserved == 0
    assert ico_type == 1
    assert count >= 6

    sizes: set[tuple[int, int]] = set()
    for index in range(count):
        entry = data[6 + index * 16 : 6 + (index + 1) * 16]
        width, height, _colors, _reserved, _planes, _bpp, _size, _offset = struct.unpack(
            "<BBBBHHII",
            entry,
        )
        sizes.add((width or 256, height or 256))

    assert (16, 16) in sizes
    assert (32, 32) in sizes
    assert (48, 48) in sizes
    assert (256, 256) in sizes
