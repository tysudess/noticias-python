from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QWidget

from monitor_noticias.ui import (
    art_studio_integration,
    art_studio_v174,
    art_studio_v175,
    art_studio_v176,
    art_studio_v177,
)
from monitor_noticias.ui import art_studio_v176_performance_patch as performance_patch
from monitor_noticias.ui.art_studio_v176_performance_patch import (
    _install_visual_refinements_without_theme_rebuild,
    install_art_studio_v176_performance_patch,
)

ROOT = Path(__file__).resolve().parents[2]


def _app():
    return QApplication.instance() or QApplication([])


def test_v176_visual_refinements_do_not_reapply_the_full_theme(monkeypatch):
    _app()
    page = QWidget()

    def unexpected_theme_rebuild(_page):
        raise AssertionError(
            "A V176 não deve reaplicar o stylesheet global: a V175/V161 já o aplicou."
        )

    monkeypatch.setattr(art_studio_v176, "_apply_theme", unexpected_theme_rebuild)
    _install_visual_refinements_without_theme_rebuild(page)


def test_v176_patch_is_installed_before_the_enhancer_queue_runs(monkeypatch):
    # A instalação modifica funções globais dos módulos. Guardamos tudo para
    # que este teste não deixe estado residual para outros testes da Central.
    modules = {
        art_studio_v174: (
            "_refresh_theme_styles",
            "_art_studio_perf_refresh_guard",
        ),
        art_studio_v175: (
            "_install_visual_refinements",
            "_render_page_thumbnail",
            "_central_theme_refresh_guard_installed",
            "_apply_theme_from_ref",
            "_art_studio_perf_visuals_installed",
            "_art_studio_perf_thumbnail_deferred",
        ),
        art_studio_v176: (
            "_install_visual_refinements",
            "_install_page_overview",
            "_install_inspector_summary",
            "_central_v176_performance_patch",
        ),
        art_studio_v177: (
            "_apply_theme",
            "_art_studio_perf_theme_installed",
        ),
        art_studio_integration: (
            "_advance_art_studio_loading",
            "_start_art_studio_loading",
            "_show_art_studio",
            "_art_studio_perf_fast_loader",
        ),
    }
    before = {
        module: {
            name: getattr(module, name, None)
            for name in names
        }
        for module, names in modules.items()
    }
    old_installed = performance_patch._INSTALLED

    monkeypatch.setattr(performance_patch, "_INSTALLED", False)
    try:
        install_art_studio_v176_performance_patch()
        assert art_studio_v176._install_visual_refinements is _install_visual_refinements_without_theme_rebuild
        assert art_studio_v176._install_page_overview is not before[art_studio_v176]["_install_page_overview"]
        assert art_studio_v176._install_inspector_summary is not before[art_studio_v176]["_install_inspector_summary"]
        assert art_studio_v174._refresh_theme_styles is not before[art_studio_v174]["_refresh_theme_styles"]
        assert art_studio_v175._install_visual_refinements is not before[art_studio_v175]["_install_visual_refinements"]
        assert art_studio_v177._apply_theme is not before[art_studio_v177]["_apply_theme"]
        assert art_studio_integration._advance_art_studio_loading is not before[art_studio_integration]["_advance_art_studio_loading"]
    finally:
        for module, attrs in before.items():
            for name, value in attrs.items():
                if value is None:
                    try:
                        delattr(module, name)
                    except AttributeError:
                        pass
                else:
                    setattr(module, name, value)
        performance_patch._INSTALLED = old_installed


def test_integration_hides_internal_layer_numbers_from_loading_message():
    source = (
        ROOT / "src/monitor_noticias/ui/art_studio_integration.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    advance = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_advance_art_studio_loading"
    )
    body = ast.unparse(advance)
    assert "V176" not in body
    assert "Preparando os componentes do Estúdio de Artes" in body


def test_v176_performance_patch_has_no_global_stylesheet_application():
    source = (
        ROOT / "src/monitor_noticias/ui/art_studio_v176_performance_patch.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_install_visual_refinements_without_theme_rebuild"
    )

    calls = []
    for node in ast.walk(target):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.append(node.func.attr)

    assert "_apply_theme" not in calls
    assert "findChild" in calls
    assert "findChildren" in calls
