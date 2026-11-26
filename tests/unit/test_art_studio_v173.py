from __future__ import annotations

import ast
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src/monitor_noticias/ui/art_studio_v173.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_canvas_engine_v173.py"
RUN = ROOT / "run.py"


def _read(path=UI):
    return path.read_text(encoding="utf-8")


def test_v173_installs_after_v172_and_before_application_entrypoint():
    source = _read(RUN)
    assert source.index("install_art_studio_v172()") < source.index("install_art_studio_v173()")
    assert source.index("install_art_studio_v173()") < source.index("from monitor_noticias.app.application import main")


def test_v173_installs_canvas_handles_for_vector_shapes_and_groups():
    source = _read()
    assert "QGraphicsRectItem, QGraphicsEllipseItem" in source
    assert "QGraphicsItemGroup" in source
    assert "_DirectResizeHandle" in source
    assert "_install_canvas_handles(page)" in source


def test_v173_supports_rotation_handle_and_shift_snap():
    source = _read()
    assert "class _RotationHandle" in source
    assert "rotation_delta(" in source
    assert "snap_rotation(delta, 15.0)" in source
    assert "ItemIgnoresTransformations" in source


def test_v173_handles_remain_out_of_serialized_group_children():
    source = _read()
    assert "setData(FRAME_CHILD_KEY, True)" in source
    assert "setData(RESIZE_HANDLE_KEY, True)" in source
    assert "_remove_custom_handles" in source


def test_v173_protects_hidden_locked_and_locked_descendant_objects():
    source = _read()
    assert "not item.isVisible()" in source
    assert "bool(item.data(LOCKED_KEY))" in source
    assert "_has_locked_child(item)" in source


def test_v173_shape_inspector_supports_fill_outline_width_and_styles():
    source = _read()
    for label in ("Preenchimento", "Contorno", "Espessura", "Estilo", "Tracejado", "Pontilhado"):
        assert label in source
    assert "QColorDialog.ColorDialogOption.ShowAlphaChannel" in source
    assert "QPen" in source and "QBrush" in source


def test_v173_shape_stroke_is_serialized_and_restored_for_group_children():
    source = _read()
    assert 'data["v173_shape_stroke"]' in source
    assert 'config = data.get("v173_shape_stroke")' in source
    assert "page._v146_base_serialize = serialize_shape" in source
    assert "page._v146_base_build = build_shape" in source


def test_v173_does_not_replace_scene_or_project_format():
    source = _read()
    assert "page.scene.clear(" not in source
    assert "page._serialize_item =" not in source
    assert "page._build_item_from_data =" not in source


def test_v173_updates_history_and_autosave_after_direct_canvas_edits():
    source = _read()
    assert "_schedule_history(page)" in source
    assert "_schedule_autosave(page)" in source


def test_v173_engine_exposes_pure_geometry_and_style_helpers():
    tree = ast.parse(_read(ENGINE))
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {
        "resized_rect", "uniform_scale_factor", "rotation_delta",
        "snap_rotation", "normalize_stroke_style", "normalize_stroke_width",
    } <= names


def test_v173_ui_module_has_no_unresolved_global_names():
    source = _read()
    table = symtable.symtable(source, str(UI), "exec")
    module_names = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
    }
    import builtins
    missing = []
    def visit(scope):
        for symbol in scope.get_symbols():
            if (
                symbol.is_global() and symbol.is_referenced()
                and symbol.get_name() not in module_names
                and not hasattr(builtins, symbol.get_name())
            ):
                missing.append(symbol.get_name())
        for child in scope.get_children():
            visit(child)
    visit(table)
    assert not missing, sorted(set(missing))
