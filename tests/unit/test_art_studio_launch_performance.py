from __future__ import annotations

import ast
import weakref
from pathlib import Path
from types import SimpleNamespace

from monitor_noticias.ui.art_studio_v176_performance_patch import (
    _guard_refresh_on_theme_change,
    _make_fast_loader_callback,
    _make_thumbnail_renderer_deferred,
    _restyle_v177_tiles_only,
)

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "src/monitor_noticias/ui/art_studio_v176_performance_patch.py"


def test_v174_refresh_runs_only_when_theme_really_changes():
    class Page:
        pass

    page = Page()
    page.theme = "escuro"
    calls = []
    guarded = _guard_refresh_on_theme_change(
        lambda _ref: calls.append("refresh"), lambda target: target.theme
    )
    ref = weakref.ref(page)

    guarded(ref)
    guarded(ref)
    assert calls == ["refresh"]

    page.theme = "claro"
    guarded(ref)
    guarded(ref)
    assert calls == ["refresh", "refresh"]


def test_v177_restyles_component_tiles_without_rebuilding_global_stylesheet():
    page = SimpleNamespace()
    calls = []
    _restyle_v177_tiles_only(
        page,
        lambda _page: "escuro",
        lambda _page: calls.append("tiles"),
    )
    assert calls == ["tiles"]
    assert page._art_studio_v177_tiles_theme == "escuro"


def test_loader_callback_promotes_active_timer_to_zero():
    class Timer:
        def __init__(self):
            self.active = True
            self.single = True
            self.value = 15

        def isActive(self):
            return self.active

        def isSingleShot(self):
            return self.single

        def interval(self):
            return self.value

        def setInterval(self, value):
            self.value = value

    timer = Timer()
    window = SimpleNamespace(_art_studio_load_timer=timer)
    calls = []

    def original(target):
        calls.append(target)
        target._art_studio_load_timer.value = 15

    wrapped = _make_fast_loader_callback(original)
    wrapped(window)
    assert calls == [window]
    assert timer.value == 0


def test_thumbnail_is_skipped_while_editor_is_loading():
    owner = SimpleNamespace(_art_studio_loading=True)
    page = SimpleNamespace(window=lambda: owner)
    calls = []
    wrapped = _make_thumbnail_renderer_deferred(
        lambda *_args: calls.append("render")
    )

    assert wrapped(page, 0) is None
    assert calls == []
    owner._art_studio_loading = False
    wrapped(page, 0)
    assert calls == ["render"]


def test_performance_patch_installs_all_deferred_optimizations():
    source = PATCH.read_text(encoding="utf-8")
    ast.parse(source)
    assert "_guard_refresh_on_theme_change" in source
    assert "_install_visual_refinements_without_theme_rebuild" in source
    assert "_restyle_v177_tiles_only" in source
    assert "_make_fast_loader_callback" in source
    assert "_make_thumbnail_renderer_deferred" in source
    assert "_schedule_first_thumbnail" in source


def test_performance_patch_keeps_existing_installers_intact():
    source = PATCH.read_text(encoding="utf-8")
    # O patch apenas substitui rotinas de acabamento redundantes; não remove
    # módulos, funções ou ferramentas do Estúdio.
    assert "delattr(" not in source
    assert ".pop(" not in source
    assert "enhance_art_studio_page" not in source
