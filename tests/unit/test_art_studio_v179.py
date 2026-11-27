from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import monitor_noticias.ui.art_studio_v179 as v179


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "run.py"
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v179.py"
V175 = ROOT / "src/monitor_noticias/ui/art_studio_v175.py"
V176 = ROOT / "src/monitor_noticias/ui/art_studio_v176.py"


class _FakeTabBar:
    def __init__(self):
        self.icons = {}

    def setTabIcon(self, index, icon):
        self.icons[index] = icon


def _fake_page():
    page = SimpleNamespace(
        v150_tab_bar=_FakeTabBar(),
        _v150_pages=[{"id": "page-1", "data": {}}],
        _v150_active_index=0,
        _v175_thumbnail_cache={},
    )
    return page


def test_v179_installs_after_v178_and_before_application_start():
    source = RUN.read_text(encoding="utf-8")
    assert source.index("install_art_studio_v178()") < source.index(
        "install_art_studio_v179()"
    )
    assert source.index("install_art_studio_v179()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_thumbnail_is_rendered_in_an_isolated_preview_and_updates_tab_icon():
    page = _fake_page()
    calls = []

    def preview_renderer(target, entry, size):
        calls.append((target, entry, size))
        return "preview-pixmap"

    icon_factory = lambda pixmap=None: ("icon", pixmap)
    size_factory = lambda width, height: (width, height)

    result = v179._render_page_thumbnail_isolated(
        page,
        0,
        preview_renderer=preview_renderer,
        icon_factory=icon_factory,
        size_factory=size_factory,
    )

    assert calls == [(page, page._v150_pages[0], (58, 42))]
    assert result == ("icon", "preview-pixmap")
    assert page._v175_thumbnail_cache["page-1"] == result
    assert page.v150_tab_bar.icons[0] == result
    assert page._v179_thumbnail_rendering is False


def test_thumbnail_renderer_skips_reentrant_calls():
    page = _fake_page()
    page._v179_thumbnail_rendering = True

    def unexpected_preview(*_args):
        raise AssertionError("A miniatura não deve ser renderizada novamente")

    assert v179._render_page_thumbnail_isolated(
        page,
        0,
        preview_renderer=unexpected_preview,
    ) is None


def test_thumbnail_renderer_does_not_render_non_active_or_invalid_pages():
    page = _fake_page()
    calls = []
    preview = lambda *_args: calls.append(True)

    assert v179._render_page_thumbnail_isolated(page, 1, preview_renderer=preview) is None
    assert v179._render_page_thumbnail_isolated(page, -1, preview_renderer=preview) is None
    assert calls == []


def test_thumbnail_preview_failure_is_logged_and_does_not_escape():
    page = _fake_page()

    def broken_preview(*_args):
        raise RuntimeError("Falha simulada na prévia")

    assert v179._render_page_thumbnail_isolated(
        page,
        0,
        preview_renderer=broken_preview,
        icon_factory=lambda value=None: value,
        size_factory=lambda width, height: (width, height),
    ) is None
    assert page._v179_thumbnail_rendering is False


def test_v179_uses_the_v176_helper_that_keeps_the_live_scene_untouched():
    source = MODULE.read_text(encoding="utf-8")
    preview_source = V176.read_text(encoding="utf-8")
    start = preview_source.index("def _render_page_preview")
    end = preview_source.index("\n\nclass _PageCard", start)
    preview_function = preview_source[start:end]

    assert "_render_page_preview" in source
    assert "_render_page_thumbnail = _render_page_thumbnail_isolated" in source
    assert "scene = QGraphicsScene()" in preview_function
    assert "page.scene.render" not in preview_function
    assert "scene.render(painter" in preview_function


def test_v179_module_and_run_file_parse():
    ast.parse(MODULE.read_text(encoding="utf-8"))
    ast.parse(RUN.read_text(encoding="utf-8"))


def test_v179_installer_is_idempotent_and_replaces_only_the_thumbnail_renderer():
    source = MODULE.read_text(encoding="utf-8")
    assert "if _INSTALLED:" in source
    assert "_render_page_thumbnail = _render_page_thumbnail_isolated" in source
    assert "_v179_thumbnail_guard_installed" in source


def test_real_editor_first_open_and_initial_thumbnail_timer(tmp_path):
    """Exercita as camadas do editor e os timers que rodam após a primeira abertura."""
    import runpy

    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

    # Executa os mesmos instaladores de compatibilidade usados pelo portable,
    # sem iniciar o restante da aplicação nem acessar rede/credenciais.
    runpy.run_path(str(RUN), run_name="_central_art_studio_runtime_test")

    from monitor_noticias.ui.art_studio_integration import (
        _enhance_art_studio_page,
        _install_deferred_view_compatibility,
    )
    from monitor_noticias.ui.art_studio_page import ArtStudioPage

    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    stack = QStackedWidget(window)
    window.setCentralWidget(stack)
    window.resize(1280, 800)

    try:
        _install_deferred_view_compatibility()
        page = ArtStudioPage(tmp_path, stack)
        _enhance_art_studio_page(page)
        stack.addWidget(page)
        stack.setCurrentWidget(page)
        window.show()
        app.processEvents()

        # A V175 agenda a primeira miniatura para 500 ms. Esperamos mais que
        # isso para exercitar a geração real, além dos demais callbacks Qt.
        QTest.qWait(1400)
        app.processEvents()

        pages = page._v150_pages
        page_id = str(pages[0].get("id") or 0)
        assert page._v145_installed
        assert page._v175_installed
        assert page._v179_thumbnail_rendering is False
        assert page_id in page._v175_thumbnail_cache
        assert not page.v150_tab_bar.tabIcon(0).isNull()
    finally:
        window.close()
        app.processEvents()
