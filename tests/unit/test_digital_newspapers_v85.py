from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "src" / "monitor_noticias" / "ui" / "digital_newspapers_page.py"
BROWSER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "browser.py"
PRESSREADER = ROOT / "src" / "monitor_noticias" / "digital_newspapers" / "pressreader_hd.py"


def _function_source(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Função não encontrada: {name}")


def test_v85_selecting_newspaper_does_not_start_search():
    source = PAGE.read_text(encoding="utf-8")
    assert "cellClicked.connect" not in source
    selection = _function_source(PAGE, "_selection_changed")
    assert "download_current" not in selection
    assert "start_automatic_download" not in selection
    assert 'QPushButton("▶  Iniciar busca / baixar edição")' in source


def test_v85_status_is_isolated_per_provider():
    source = PAGE.read_text(encoding="utf-8")
    browser_for = _function_source(PAGE, "_browser_for")
    browser_status = _function_source(PAGE, "_browser_status")
    assert "pid=provider.id" in browser_for
    assert "provider_id != self._selected_provider_id" in browser_status
    assert "self._provider_status[provider_id] = text" in browser_status
    assert "self._provider_busy" in source


def test_v85_pressreader_uses_qt_request_interceptor_like_android_webview():
    source = BROWSER.read_text(encoding="utf-8")
    assert "QWebEngineUrlRequestInterceptor" in source
    assert "class DigitalNewspaperRequestInterceptor" in source
    assert "setUrlRequestInterceptor" in source
    assert "def _request_resource_seen" in source
    assert "pressreader_image_candidate_score" in source
    assert "self._pressreader_candidates" in source
    assert "pressreader_image_page_number" in source


def test_v85_pressreader_also_checks_dom_images_and_keeps_page_active():
    source = BROWSER.read_text(encoding="utf-8")
    assert "document.images" in source
    assert "img.currentSrc" in source
    assert "img.srcset" in source
    assert "self.page.setVisible(True)" in source
    assert "QWebEnginePage.LifecycleState.Active" in source
    assert "self.view.resize(1800, 2800)" in source
    assert "self.view.setZoomFactor(1.8)" in source


def test_v85_hd_images_are_saved_separately_and_not_deleted_after_pdf():
    source = PRESSREADER.read_text(encoding="utf-8")
    assert 'pages_dir = self.output_path.parent / "paginas_hd"' in source
    assert 'f"pagina-{page_number:03d}{suffix}"' in source
    assert "salva separadamente" in source
    assert '"PressReader - imagens HD + PDF"' in source
    # V86: imagens válidas de tentativas anteriores não são apagadas no início.
    run_source = _function_source(PRESSREADER, "run")
    assert "shutil.rmtree(pages_dir, ignore_errors=True)" not in run_source
    assert "pages_dir.mkdir(parents=True, exist_ok=True)" in run_source
