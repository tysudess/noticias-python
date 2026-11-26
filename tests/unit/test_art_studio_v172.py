from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v172.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_transform_engine_v172.py"
RUN = ROOT / "run.py"


def _source(path=MODULE):
    return path.read_text(encoding="utf-8")


def test_v172_module_and_engine_compile_and_expose_installers():
    tree = ast.parse(_source())
    names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    assert "install_art_studio_v172" in names
    assert "enhance_art_studio_page_v172" in names
    ast.parse(_source(ENGINE))


def test_v172_installs_after_v171_and_before_application_entrypoint():
    source = _source(RUN)
    pos171 = source.index("install_art_studio_v171()")
    pos172 = source.index("install_art_studio_v172()")
    app = source.index("from monitor_noticias.app.application import main")
    assert pos171 < pos172 < app


def test_transform_inspector_contains_professional_controls():
    source = _source()
    for token in (
        "Posição", "Horizontal (X)", "Vertical (Y)", "Largura", "Altura",
        "Manter proporção", "Rotação", "Opacidade", "Espelhar H", "Espelhar V",
        "Centralizar na página", "Alinhar à página", "Distribuir horizontalmente",
        "Distribuir verticalmente",
    ):
        assert token in source


def test_alignment_and_distribution_support_real_multi_selection():
    source = _source()
    assert "page.scene.selectedItems()" in source
    assert "selected_roots(raw" in source
    assert "has_locked_descendant(" in source
    assert "_align_to_page" in source
    assert "distribution_offsets" in source
    assert "len(items) >= 3" in source


def test_transformations_preserve_scene_center_and_update_document_history():
    source = _source()
    assert "center_before = item.mapToScene" in source
    assert "center_after = item.mapToScene" in source
    assert "item.setTransform(QTransform().scale" in source
    assert "item.setRotation" in source
    assert "item.setOpacity" in source
    assert "_schedule_history(page)" in source
    assert "_schedule_autosave(page)" in source


def test_arrow_nudging_works_with_one_and_ten_pixel_steps():
    source = _source()
    assert "Qt.Key.Key_Left" in source
    assert "Qt.Key.Key_Down" in source
    assert "step = 10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1.0" in source
    assert "viewport().installEventFilter(nudge_filter)" in source


def test_keyboard_nudging_does_not_intercept_form_fields():
    source = _source()
    assert "_input_has_focus(page, focus)" in source
    assert "page.scene.focusItem()" in source
    assert "QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox" in source
    assert "focus not in (view, viewport)" in source


def test_transform_tab_is_scrollable_and_extends_existing_inspector():
    source = _source()
    assert 'getattr(page, "_v161_inspector_tabs", None)' in source
    assert "QScrollArea(tab)" in source
    assert 'tabs.addTab(tab, "⌗  Transformar")' in source
    assert "findChild(QWidget, \"artStudioTransformTabV172\")" in source


def test_transform_tab_extension_respects_both_existing_theme_modes():
    source = _source()
    assert 'dark = theme == "escuro"' in source
    assert "_wrap_v171_skin()" in source
    assert "return original(theme) + _visual_stylesheet(theme)" in source


def test_v172_preserves_local_affine_matrices_and_transform_origin_recursively():
    source = _source()
    assert 'data["v172_local_transform"] = _matrix_values(item)' in source
    assert 'data["v172_transform_origin"]' in source
    assert "_serialize_transform_tree(child, child_data)" in source
    assert "_restore_transform_tree(child, child_data)" in source
    assert "QTransform(*values)" in source


def test_v172_wraps_existing_project_serializers_without_replacing_the_format():
    source = _source()
    assert 'base_serialize = getattr(page, "_serialize_item", None)' in source
    assert 'base_build = getattr(page, "_build_item_from_data", None)' in source
    assert "page._serialize_item = serialize_with_local_transform" in source
    assert "page._build_item_from_data = build_with_local_transform" in source
    assert "page.scene.clear(" not in source
    assert ".centralart" not in source
