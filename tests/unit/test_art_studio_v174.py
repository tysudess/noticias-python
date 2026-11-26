from __future__ import annotations

import ast
import symtable
from pathlib import Path
import builtins

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v174.py"
ENGINE = ROOT / "src/monitor_noticias/ui/art_studio_layout_engine_v174.py"
RUN = ROOT / "run.py"


def read(path=MODULE):
    return path.read_text(encoding="utf-8")


def test_v174_installs_after_v173_and_before_application_entrypoint():
    source = read(RUN)
    assert source.index("install_art_studio_v173()") < source.index("install_art_studio_v174()")
    assert source.index("install_art_studio_v174()") < source.index("from monitor_noticias.app.application import main")


def test_global_footer_and_editor_bottom_status_strip_are_removed():
    source = read()
    assert '"footer_left"' in source or "footer_left" in source
    assert '"footer_right"' in source or "footer_right" in source
    assert "_hide_global_footer(window)" in source
    assert "page.status_label" in source
    assert "status.hide()" in source
    assert "status.setMaximumSize(0, 0)" in source


def test_pages_bar_is_compacted_and_remains_collapsible():
    source = read()
    assert "compact_pages_bar_metrics(expanded=True)" in source
    assert "bar.setMaximumHeight(metrics[\"height\"])" in source
    assert "toggle.setCheckable(True)" in source
    assert "bar.setVisible(bool(visible))" in source
    assert 'toggle.setText("Páginas" if visible else "Páginas +")' in source


def test_workspace_reserves_more_width_for_canvas_than_side_panels():
    source = read()
    assert "workspace_split_sizes(total)" in source
    assert "center.setMinimumWidth(560)" in source
    assert "left.setMaximumWidth(258)" in source
    assert "right.setMaximumWidth(348)" in source
    assert "splitter.setHandleWidth(5)" in source


def test_inspector_tabs_use_compact_scrollable_labels():
    source = read()
    assert "bar.setUsesScrollButtons(True)" in source
    assert "bar.setElideMode(Qt.TextElideMode.ElideRight)" in source
    assert '"⇄  Composição": "Compor"' in source
    assert '"⌗  Transformar": "Transformar"' in source


def test_no_scene_reset_or_project_format_replacement():
    source = read()
    assert "page.scene.clear(" not in source
    assert "page._serialize_item =" not in source
    assert "page._build_item_from_data =" not in source
    assert ".centralart" not in source


def test_v174_module_and_engine_compile_and_have_no_unresolved_global_names():
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


def test_pages_bar_uses_the_active_theme_palette():
    source = read()
    assert "colors = _theme_tokens(page)" in source
    assert "QFrame#artStudioPagesBar" in source
    assert "colors['panel_alt']" in source
    assert "colors['border']" in source
