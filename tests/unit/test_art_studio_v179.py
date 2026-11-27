from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import monitor_noticias.ui.art_studio_v179 as v179

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "run.py"
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v179.py"
V175 = ROOT / "src/monitor_noticias/ui/art_studio_v175.py"
V176 = ROOT / "src/monitor_noticias/ui/art_studio_v176.py"
V177 = ROOT / "src/monitor_noticias/ui/art_studio_v177.py"


class _FakeTabBar:
    def __init__(self):
        self.icons = {}

    def setTabIcon(self, index, icon):
        self.icons[index] = icon


def _fake_page():
    return SimpleNamespace(
        v150_tab_bar=_FakeTabBar(),
        _v150_pages=[{"id": "page-1", "data": {}}],
        _v150_active_index=0,
        _v175_thumbnail_cache={},
    )


def test_v179_installs_after_v178_and_before_application_start():
    source = RUN.read_text(encoding="utf-8")
    assert source.index("install_art_studio_v178()") < source.index("install_art_studio_v179()")
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

    assert v179._render_page_thumbnail_isolated(page, 0, preview_renderer=unexpected_preview) is None


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


def test_theme_refresh_callback_skips_destroyed_page_wrapper():
    class FakePage:
        alive = False

    page = FakePage()
    calls = []
    guarded = v179._guard_theme_refresh_callback(
        lambda _ref, *_args, **_kwargs: calls.append("called"),
        validity_check=lambda target: target.alive,
    )
    import weakref

    assert guarded(weakref.ref(page), force=True) is None
    assert calls == []
    page.alive = True
    assert guarded(weakref.ref(page), force=True) is None
    assert calls == ["called"]


def test_v179_installs_lifetime_guards_for_visual_theme_callbacks():
    source = MODULE.read_text(encoding="utf-8")
    for version, path in ((175, V175), (176, V176), (177, V177)):
        module_source = path.read_text(encoding="utf-8")
        assert "def _apply_theme_from_ref" in module_source
        assert f"art_studio_v{version}" in source
    assert "_guard_theme_refresh_callback" in source
    assert "shiboken6.isValid(value)" in source


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
    assert "_install_theme_refresh_lifetime_guards()" in source


def test_real_sidebar_click_loads_editor_gradually_and_survives_initial_timers(tmp_path):
    """Exercita o clique real, carga V145–V177 e timers iniciais em subprocesso."""
    script = textwrap.dedent(
        r"""
        import runpy
        import sys
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QWidget

        app = QApplication.instance() or QApplication([])
        runpy.run_path(sys.argv[1], run_name="_central_art_studio_runtime_test")

        from monitor_noticias.ui.main_window import MainWindow
        from monitor_noticias.ui.sidebar_widgets import SidebarNavItem

        window = QMainWindow()
        stack = QStackedWidget(window)
        window.setCentralWidget(stack)
        window.stack = stack
        window.resize(1280, 800)

        placeholder = QWidget(stack)
        stack.addWidget(placeholder)
        window._art_studio_placeholder = placeholder
        window._art_studio_loading_label = QLabel("Aguardando abertura", placeholder)
        window.pages = {"ART_STUDIO": placeholder}
        window._art_studio_projects_dir = sys.argv[2]
        window.art_studio_page = None
        window._art_studio_building_page = None
        window._art_studio_ready = False
        window._art_studio_loading = False
        window._art_studio_suppress_error_dialog = True
        window.nav_buttons = {}
        window.title = QLabel("Central", window)
        window.subtitle = QLabel("", window)
        window.header_identity = QWidget(window)
        window._current = "HOME"
        window._state_signature = lambda: "test-state"
        window._last_refresh_signature = None

        nav = SidebarNavItem(
            icon_text="✎",
            label_text="Estúdio de Artes",
            icon_color="#F4B719",
            parent=window,
        )
        window.art_studio_nav = nav
        nav.clicked.connect(MainWindow._open_art_studio.__get__(window, MainWindow))

        window.show()
        nav.click()
        assert window._art_studio_loading is True
        assert stack.currentWidget() is placeholder

        # Espera até 15 segundos pela execução das 33 camadas em eventos separados.
        for _ in range(300):
            if window._art_studio_ready:
                break
            QTest.qWait(50)

        assert window._art_studio_ready is True
        page = window.art_studio_page
        assert page is not None
        assert stack.currentWidget() is page
        assert window.pages["ART_STUDIO"] is page
        assert page._v145_installed
        assert page._v175_installed
        assert page._v177_installed

        # Aguarda miniaturas e filtros de tema agendados pelas últimas camadas.
        QTest.qWait(1800)
        page_id = str(page._v150_pages[0].get("id") or 0)
        assert page_id in page._v175_thumbnail_cache
        assert not page.v150_tab_bar.tabIcon(0).isNull()

        window.close()
        QTest.qWait(100)
        app.quit()
        """
    )
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-c", script, str(RUN), str(tmp_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, (
        "O teste do clique real e da abertura gradual do Estúdio falhou.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
