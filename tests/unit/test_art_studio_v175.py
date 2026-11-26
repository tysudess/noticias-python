from __future__ import annotations

import ast
import builtins
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v175.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_workspace_engine_v175.py"
RUN = ROOT / "run.py"


def read(path=MODULE):
    return path.read_text(encoding="utf-8")


def test_v175_installs_after_v174_and_before_application_entrypoint():
    source = read(RUN)
    assert source.index("install_art_studio_v174()") < source.index("install_art_studio_v175()")
    assert source.index("install_art_studio_v175()") < source.index("from monitor_noticias.app.application import main")


def test_v175_module_and_engine_compile_and_have_no_unresolved_globals():
    ast.parse(read())
    ast.parse(read(ENGINE))
    table = symtable.symtable(read(), str(MODULE), "exec")
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


def test_v175_adds_independent_collapsible_left_and_right_panels():
    source = read()
    assert "_install_panel_toggles(page)" in source
    assert '"left"' in source and '"right"' in source
    assert "panel.setVisible(bool(visible))" in source
    assert "splitter_sizes_for_visibility(" in source
    assert "v175_left_panel_toggle" in source
    assert "v175_right_panel_toggle" in source


def test_v175_installs_floating_context_toolbar_in_canvas_viewport():
    source = read()
    assert "class _ContextToolbarViewportFilter" in source
    assert "frame = QFrame(viewport)" in source
    assert "scene.selectionChanged.connect" in source
    assert "_position_context_toolbar" in source
    assert "Duplicar" in source and "Excluir" in source
    assert "Editar texto" in source and "Transformar" in source


def test_context_toolbar_reuses_existing_editor_actions_instead_of_reimplementing_them():
    source = read()
    for name in ("duplicate_button", "edit_text_button", "delete_button", "forward_button", "backward_button"):
        assert f'"{name}"' in source
    assert "button.click()" in source


def test_v175_uses_existing_selection_and_respects_canvas_background_and_helpers():
    source = read()
    assert "selected_roots(selected" in source
    assert "not item.data(FRAME_CHILD_KEY)" in source
    assert "item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY" in source


def test_v175_generates_lightweight_page_thumbnails_without_full_resolution_render():
    source = read()
    assert "QPixmap(58, 42)" in source
    assert "page.scene.render(painter, target, source" in source
    assert "page._v175_thumbnail_cache" in source
    assert "timer.setInterval(700)" in source
    assert "tab_bar.setIconSize(QSize(40, 28))" in source


def test_v175_thumbnail_render_hides_editor_overlays_and_restores_visibility():
    source = read()
    for name in ("_v150_grid_lines", "_v150_guide_lines", "_v148_handles", "_v173_handles"):
        assert name in source
    assert "overlay.setVisible(was_visible)" in source


def test_v175_has_coherent_light_and_dark_professional_palette():
    source = read()
    for token in ("#0D1722", "#142334", "#E9EFF4", "#FCFDFE", "#4CC5C7", "#D7B56D"):
        assert token in source
    assert "_wrap_theme_stylesheet()" in source
    assert "QTabBar::tab:selected" in source
    assert "QFrame#artStudioPanel" in source
    assert "QFrame#artStudioWorkspace" in source


def test_v175_does_not_clear_scene_or_replace_project_serializers():
    source = read()
    assert "page.scene.clear(" not in source
    assert "page._serialize_item =" not in source
    assert "page._build_item_from_data =" not in source
    assert ".centralart" not in source


def test_v175_does_not_add_third_party_dependencies_or_change_portable_builds():
    source = read(RUN)
    assert "PIL" not in source
    assert "PySide6" not in source
    assert "install_art_studio_v175()" in source
    assert "rebuild-planilhas-runtime" not in source


def test_v175_scopes_global_gold_border_patch_out_of_the_studio_only():
    source = read()
    assert "_install_gold_border_exclusions()" in source
    assert "_inside_art_studio(widget)" in source
    assert "gold_borders_patch._append_page_rules = append_without_studio" in source
    assert "gold_borders_patch._force_widget_border = force_without_studio" in source
    assert "QWidget#artStudioPage QTabBar::tab" in source


def test_v175_uses_readable_compact_tabs_and_real_page_icon_thumbnails():
    source = read()
    assert "tab_bar.setIconSize(QSize(40, 28))" in source
    assert "tab_bar.setMaximumHeight(34)" in source
    assert "font-size:9px" in source
    assert "tab_bar.setTabIcon(index" in source


def test_v175_thumbnail_refresh_is_debounced_and_does_not_reschedule_its_own_overlays():
    source = read()
    assert "timer.setSingleShot(True)" in source
    assert "timer.setInterval(700)" in source
    assert "_v175_rendering_thumbnail" in source
    assert "if not getattr(page, \"_v175_rendering_thumbnail\", False)" in source


def test_v175_context_actions_are_disabled_for_locked_objects_and_locked_groups():
    source = read()
    assert "LOCKED_KEY" in source
    assert "_selection_is_editable(items)" in source
    assert "button.setEnabled(editable)" in source
    assert "_has_locked_descendant(item)" in source


def test_contextual_toolbar_repositions_after_canvas_drag_and_zoom_scroll():
    source = read()
    assert "page.scene.changed.connect(lambda *_args: position_timer.start())" in source
    assert "QEvent.Type.Wheel, QEvent.Type.Scroll" in source
    assert "available_width = max(120, viewport.width() - 16)" in source


def test_inspector_heading_is_clear_and_independent_from_layer_tab_title():
    source = read()
    assert 'heading.setText("PROPRIEDADES")' in source
    assert 'heading.setText("ELEMENTOS")' in source


def test_thumbnail_cache_is_initialized_once_and_scene_preview_is_debounced():
    source = read()
    assert source.count("page._v175_thumbnail_cache = {}") == 1
    assert "timer.setInterval(700)" in source
    assert "_v175_rendering_thumbnail" in source


def test_contextual_toolbar_refreshes_after_text_edit_focus_out():
    source = read()
    assert "QEvent.Type.MouseButtonRelease, QEvent.Type.FocusIn" in source
    assert "_sync_context_toolbar(page)" in source


def test_contextual_more_menu_is_disabled_for_locked_objects():
    source = read()
    assert 'if key == "more":' in source
    assert "button.setEnabled(editable)" in source


def test_v175_reapplies_custom_palette_after_global_theme_update():
    source = read()
    assert "_apply_theme_from_ref(ref, force=True)" in source
