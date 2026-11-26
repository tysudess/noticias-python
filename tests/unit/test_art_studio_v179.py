from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import monitor_noticias.ui.art_studio_v179 as v179


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "run.py"
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v179.py"


def test_v179_installs_after_v178_and_before_application_start():
    source = RUN.read_text(encoding="utf-8")
    assert source.index("install_art_studio_v178()") < source.index(
        "install_art_studio_v179()"
    )
    assert source.index("install_art_studio_v179()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_thumbnail_guard_keeps_v175_flag_active_until_queued_signal_window_ends():
    callbacks = []
    schedule = lambda delay, callback: callbacks.append((delay, callback))

    class FakePage:
        pass

    page = FakePage()
    page._v175_rendering_thumbnail = False

    calls = []

    def original_renderer(target, index):
        calls.append(index)
        target._v175_rendering_thumbnail = True
        target._v175_rendering_thumbnail = False

    guarded = v179._guard_thumbnail_renderer(original_renderer, schedule)
    guarded(page, 0)

    assert calls == [0]
    assert page._v175_rendering_thumbnail is True
    assert page._v179_thumbnail_rendering is True
    assert len(callbacks) == 1
    assert callbacks[0][0] == 120

    callbacks[0][1]()
    assert page._v175_rendering_thumbnail is False
    assert page._v179_thumbnail_rendering is False


def test_thumbnail_guard_prevents_reentrant_render():
    callbacks = []

    class FakePage:
        pass

    page = FakePage()
    page._v179_thumbnail_rendering = True

    def original_renderer(_page, _index):
        raise AssertionError("A renderização não deveria ser reentrante")

    guarded = v179._guard_thumbnail_renderer(original_renderer)
    assert guarded(page, 2) is None


def test_v179_module_and_run_file_parse():
    ast.parse(MODULE.read_text(encoding="utf-8"))
    ast.parse(RUN.read_text(encoding="utf-8"))


def test_v179_installer_is_idempotent_and_patches_only_thumbnail_renderer():
    source = MODULE.read_text(encoding="utf-8")
    assert "if _INSTALLED:" in source
    assert "_render_page_thumbnail = _guard_thumbnail_renderer(original)" in source
    assert "_v179_thumbnail_guard_installed" in source
