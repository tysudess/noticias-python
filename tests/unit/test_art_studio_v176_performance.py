from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QWidget

from monitor_noticias.ui import art_studio_v176
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
            "A V176 não deve reaplicar o stylesheet global: a V175 já o aplicou."
        )

    monkeypatch.setattr(art_studio_v176, "_apply_theme", unexpected_theme_rebuild)
    _install_visual_refinements_without_theme_rebuild(page)


def test_v176_patch_is_installed_before_the_enhancer_queue_runs(monkeypatch):
    original_visual = art_studio_v176._install_visual_refinements
    original_overview = art_studio_v176._install_page_overview
    original_summary = art_studio_v176._install_inspector_summary
    old_marker = getattr(art_studio_v176, "_central_v176_performance_patch", False)
    old_installed = performance_patch._INSTALLED
    monkeypatch.setattr(art_studio_v176, "_central_v176_performance_patch", False, raising=False)
    monkeypatch.setattr(performance_patch, "_INSTALLED", False)

    try:
        install_art_studio_v176_performance_patch()
        assert art_studio_v176._install_visual_refinements is _install_visual_refinements_without_theme_rebuild
        assert art_studio_v176._install_page_overview is not original_overview
        assert art_studio_v176._install_inspector_summary is not original_summary
    finally:
        art_studio_v176._install_visual_refinements = original_visual
        art_studio_v176._install_page_overview = original_overview
        art_studio_v176._install_inspector_summary = original_summary
        art_studio_v176._central_v176_performance_patch = old_marker
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

    # Qt widgets são acessados como atributos (page.findChild), não como
    # funções globais (findChild). O teste anterior só reconhecia ast.Name e
    # por isso falhava mesmo quando o código já continha as chamadas corretas.
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
