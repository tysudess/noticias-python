from __future__ import annotations

import ast
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import zlib

from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
PRESSREADER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "pressreader_hd.py"
PROVIDERS = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "providers.py"
BROWSER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "browser.py"
PAGE = ROOT / "src" / "monitor_noticias" / "ui" / "digital_newspapers_page.py"


def _exec_selected_functions(path: Path, names: set[str]) -> dict:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "BytesIO": BytesIO,
        "Path": Path,
        "Image": Image,
        "zlib": zlib,
        "urlsplit": urlsplit,
        "urlunsplit": urlunsplit,
        "parse_qsl": parse_qsl,
        "urlencode": urlencode,
        "PRESSREADER_HIGH_SCALES": (416, 390, 364, 338, 312, 286, 260, 234, 208, 182, 156, 130, 104),
        "PRESSREADER_HIGH_WIDTHS": (3200, 3000, 2800, 2600, 2400, 2200, 2000, 1800, 1600),
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def test_v84_valor_uses_proven_pressreader_route_and_prcdn():
    source = PROVIDERS.read_text(encoding="utf-8")
    start = source.index("class ValorProvider")
    end = source.index("class ATardeProvider", start)
    valor = source[start:end]

    assert 'edition_url="https://valoreconomico.pressreader.com/valor-economico"' in valor
    assert 'download_strategy="pressreader_hd_images"' in valor
    assert '"{yyyymmdd}/page/{page}"' in valor
    assert '"prcdn.co"' in valor
    assert "pressreader_min_width=1800" in valor
    assert "pressreader_target_width=2200" in valor


def test_v84_prcdn_candidate_and_hd_variants_keep_page_and_file():
    ns = _exec_selected_functions(
        PRESSREADER,
        {"pressreader_image_candidate_score", "pressreader_image_variants"},
    )
    score = ns["pressreader_image_candidate_score"]
    variants = ns["pressreader_image_variants"]

    raw = (
        "https://i.prcdn.co/img?file=abc123&page=7&scale=104&issue=20260928&ticket=xyz"
    )
    assert score(raw, expected_page=7) is not None
    assert score(raw, expected_page=6) is None

    urls = variants(raw)
    assert urls
    assert "scale=416" in urls[0]
    assert "page=7" in urls[0]
    assert "file=abc123" in urls[0]
    assert "ticket=xyz" in urls[0]
    assert any("width=3200" in item for item in urls)


def test_v84_pdf_builder_preserves_page_pixels_and_jpeg_passthrough(tmp_path: Path):
    ns = _exec_selected_functions(
        PRESSREADER,
        {"_pdf_number", "_prepare_pdf_image", "build_image_pdf_without_pixel_loss"},
    )
    builder = ns["build_image_pdf_without_pixel_loss"]

    paths: list[Path] = []
    sizes = [(2200, 3200), (2400, 3400), (2000, 3000)]
    for index, size in enumerate(sizes, start=1):
        path = tmp_path / f"page-{index}.jpg"
        image = Image.new("RGB", size, (255, 255 - index, 250))
        image.save(path, format="JPEG", quality=93)
        paths.append(path)

    output = tmp_path / "valor.pdf"
    assert builder(paths, output) == 3

    reader = PdfReader(str(output))
    assert len(reader.pages) == 3
    assert all(float(page.mediabox.width) == 612.0 for page in reader.pages)

    payload = output.read_bytes()
    assert payload.count(b"/DCTDecode") == 3
    assert payload.count(b"/Subtype /Image") == 3
    assert paths[0].read_bytes() in payload


def test_v84_browser_has_sequential_pressreader_collection_and_worker():
    source = BROWSER.read_text(encoding="utf-8")

    assert 'self.provider.download_strategy == "pressreader_hd_images"' in source
    assert "def _start_pressreader_hd_download" in source
    assert "def _probe_pressreader_resources" in source
    assert "def _finish_pressreader_collection" in source
    assert "pressreader_image_candidate_score" in source
    assert "PressReaderHdPdfThread" in source
    assert "self._valor_page_number += 1" in source


def test_v84_ui_identifies_hd_method_and_quality():
    source = PAGE.read_text(encoding="utf-8")
    assert 'method = "Imagens HD + PDF"' in source
    assert '"HD / imagens preservadas"' in source
