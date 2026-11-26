from __future__ import annotations

import ast
import builtins
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v176.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_workspace_engine_v176.py"
RUN = ROOT / "run.py"


def read(path=MODULE):
    return path.read_text(encoding="utf-8")


def test_v176_installs_after_v175_and_before_application_entrypoint():
    source = read(RUN)
    assert source.index("install_art_studio_v175()") < source.index("install_art_studio_v176()")
    assert source.index("install_art_studio_v176()") < source.index("from monitor_noticias.app.application import main")


def test_v176_modules_parse_and_have_no_unresolved_global_names():
    source = read()
    ast.parse(source)
    ast.parse(read(ENGINE))
    table = symtable.symtable(source, str(MODULE), "exec")
    module_names = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
    }
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


def test_page_overview_has_preview_open_duplicate_rename_delete_and_reorder():
    source = read()
    for token in (
        "class _PageOverviewDialog", "_render_page_preview", "_open_page",
        "_duplicate_page", "_rename_page", "_delete_page", "_move_page",
        "Visão geral das páginas", "Ctrl+Shift+P",
    ):
        assert token in source


def test_page_previews_use_temporary_scene_and_never_clear_live_scene():
    source = read()
    assert "scene = QGraphicsScene()" in source
    assert "page._build_item_from_data(item_data)" in source
    assert "scene.clear()" in source
    assert "page.scene.clear(" not in source
    assert "page._serialize_item =" not in source
    assert "page._build_item_from_data =" not in source


def test_page_previews_support_solid_gradient_and_image_backgrounds():
    source = read()
    assert 'mode == "gradient"' in source
    assert 'mode == "image"' in source
    assert "_gradient_brush" in source
    assert "QPixmap" in source and "image_png_base64" in source


def test_page_overview_reuses_existing_page_actions_and_history():
    source = read()
    assert "from monitor_noticias.ui.art_studio_v150 import _switch_page" in source
    assert "from monitor_noticias.ui.art_studio_v150 import _duplicate_page" in source
    assert "from monitor_noticias.ui.art_studio_v150 import _delete_page" in source
    assert "from monitor_noticias.ui.art_studio_v150 import _tab_moved" in source
    assert "_capture_active_page(page)" in source


def test_summary_inspector_has_name_geometry_lock_and_transform_actions():
    source = read()
    for token in (
        "artStudioSummaryTabV176", "v176_object_name", "v176_geometry",
        "v176_lock_button", "v176_transform_button", "_toggle_selection_lock",
        "_rename_selected", "_open_transform_tab",
    ):
        assert token in source


def test_summary_uses_existing_locked_state_history_and_autosave():
    source = read()
    assert "LOCKED_KEY" in source
    assert "QGraphicsItem.GraphicsItemFlag.ItemIsMovable" in source
    assert "_schedule_history(page)" in source
    assert "_schedule_autosave(page)" in source
    assert "page._refresh_layers" in source
    assert "v176_duplicate_button" in source
    assert "v176_delete_button" in source


def test_v176_uses_existing_theme_and_provides_refined_light_dark_palettes():
    source = read()
    for token in ("#0D151E", "#172532", "#E9EEF2", "#FFFFFF", "#41B8B3", "#167E83"):
        assert token in source
    assert "_wrap_theme_stylesheet()" in source
    assert "_apply_theme(page)" in source
    assert "_visual_stylesheet" in source


def test_v176_does_not_change_project_format_or_build_workflows():
    source = read(RUN)
    assert "install_art_studio_v176()" in source
    assert "rebuild-planilhas-runtime" not in source
    module = read()
    assert ".centralart" in module
    assert "page.scene.clear(" not in module


def test_overview_uses_responsive_grid_and_delayed_thumbnail_rendering():
    source = read()
    assert "page_grid_columns(" in source
    assert "self._render_timer.setSingleShot(True)" in source
    assert "self._render_timer.setInterval(25)" in source
    assert "self._render_queue" in source
    assert "class _PageCard" in source
    assert "class _PageDragHandle" in source
    assert "artStudioPageDragHandleV176" in source
    assert "QMimeData" in source and "QDrag" in source


def test_context_inspector_handles_single_and_multiple_selection():
    source = read()
    assert "selection_summary(" in source
    assert "len(items) == 1" in source
    assert "Seleção mista" in source
    assert "Rotação" not in source or "summary['rotation']" in source
