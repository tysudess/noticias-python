from __future__ import annotations

import ast
import builtins
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v177.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_workspace_engine_v177.py"
RUN = ROOT / "run.py"


def read(path=MODULE):
    return path.read_text(encoding="utf-8")


def test_v177_installs_after_v176_and_before_application_entrypoint():
    source = read(RUN)
    assert source.index("install_art_studio_v176()") < source.index("install_art_studio_v177()")
    assert source.index("install_art_studio_v177()") < source.index("from monitor_noticias.app.application import main")


def test_v177_modules_parse_and_have_no_unresolved_global_names():
    source = read()
    ast.parse(source)
    ast.parse(read(ENGINE))
    table = symtable.symtable(source, str(MODULE), "exec")
    module_names = {
        symbol.get_name() for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
    }
    missing = []

    def visit(scope):
        for symbol in scope.get_symbols():
            if symbol.is_global() and symbol.is_referenced() and symbol.get_name() not in module_names and not hasattr(builtins, symbol.get_name()):
                missing.append(symbol.get_name())
        for child in scope.get_children():
            visit(child)

    visit(table)
    assert not missing, sorted(set(missing))


def test_component_library_replaces_plain_buttons_with_visual_template_tiles():
    source = read()
    assert "_upgrade_component_library(page)" in source
    assert "QToolButton" in source
    assert "ToolButtonTextUnderIcon" in source
    assert "_template_preview_icon" in source
    assert "TEMPLATES" in source
    assert "PALETTES" in source


def test_component_tiles_remain_searchable_and_palette_aware():
    source = read()
    assert "page.v163_template_buttons = tiles" in source
    assert "_restyle_component_tiles(page)" in source
    assert "setProperty(\"templateKey\"" in source
    assert "v163_palette_combo.currentIndexChanged" in source


def test_component_grid_reflows_between_one_and_two_columns():
    source = read()
    assert "library_grid_columns(panel.width() - 18" in source
    assert "_layout_component_tiles(page)" in source
    assert "_LibraryPanelFilter" in source
    assert "QEvent.Type.Resize" in source


def test_layer_list_has_custom_delegate_with_type_visibility_and_lock_states():
    source = read()
    assert "class _LayerDelegate(QStyledItemDelegate)" in source
    for token in ("image", "text", "shape", "group", "LOCKED_KEY", "item.isVisible()"):
        assert token in source
    assert "layers.setItemDelegate(_LayerDelegate(page, layers))" in source


def test_layer_panel_supports_internal_drag_reorder_and_updates_z_order():
    source = read()
    assert "QAbstractItemView.DragDropMode.InternalMove" in source
    assert "layers.model().rowsMoved.connect" in source
    assert "layer_order_z_values(len(ordered))" in source
    assert "_schedule_history(page)" in source
    assert "_schedule_autosave(page)" in source


def test_layer_context_menu_reuses_existing_editor_actions():
    source = read()
    assert "setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)" in source
    assert "QItemSelectionModel.SelectionFlag.ClearAndSelect" in source
    for token in ("v145_visibility_button", "v145_lock_button", "duplicate_button", "forward_button", "backward_button", "v170_layers_delete_button"):
        assert token in source
    assert "QInputDialog.getText" in source


def test_zoom_presets_and_shortcuts_use_existing_canvas_view_methods():
    source = read()
    for token in ("Ajustar", "25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%"):
        assert token in source
    for shortcut in ("Ctrl+0", "Ctrl+1", "Ctrl+2"):
        assert shortcut in source
    assert "page.view.zoom_by(factor)" in source
    assert "page.view_fit()" in source


def test_canvas_meta_tracks_current_page_and_page_count():
    source = read()
    assert "artStudioCanvasMetaV177" in source
    assert "_v150_active_index" in source
    assert "len(getattr(page, \"_v150_pages\", []))" in source
    assert "tab_bar.currentChanged.connect(refresh)" in source


def test_v177_extends_active_theme_without_replacing_v176_palette():
    source = read()
    assert "_wrap_skin()" in source
    assert "art_studio_v161._skin_stylesheet = stylesheet_with_v177" in source
    assert "_visual_stylesheet(theme)" in source


def test_v177_does_not_clear_live_scene_or_replace_project_serializers():
    source = read()
    assert "page.scene.clear(" not in source
    assert "page._serialize_item =" not in source
    assert "page._build_item_from_data =" not in source
    assert ".centralart" not in source


def test_v177_does_not_change_build_workflows_or_add_dependencies():
    source = read(RUN)
    assert "install_art_studio_v177()" in source
    assert "rebuild-planilhas-runtime" not in source
    assert "appimage" not in source.casefold()


def test_v177_installation_is_idempotent():
    source = read()
    assert "if getattr(page, \"_v177_installed\", False):" in source
    assert "_v177_integration_installed" in source
    assert "if _INSTALLED:" in source


def test_qt_types_are_imported_from_their_actual_pyside6_modules():
    tree = ast.parse(read())
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            imports.setdefault((node.level, node.module), set()).update(alias.name for alias in node.names)
    assert "QItemSelectionModel" in imports[(0, "PySide6.QtCore")]
    assert "QShortcut" in imports[(0, "PySide6.QtGui")]
    assert "QItemSelectionModel" not in imports[(0, "PySide6.QtWidgets")]
    assert "QShortcut" not in imports[(0, "PySide6.QtWidgets")]
