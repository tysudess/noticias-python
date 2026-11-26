from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v171.py"
RUN = ROOT / "run.py"


def _source():
    return MODULE.read_text(encoding="utf-8")


def test_v171_module_compiles_and_has_installer():
    source = _source()
    tree = ast.parse(source)
    names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    assert "install_art_studio_v171" in names
    assert "enhance_art_studio_page_v171" in names


def test_v171_is_loaded_after_v170_before_application_entrypoint():
    source = RUN.read_text(encoding="utf-8")
    pos170 = source.index("install_art_studio_v170()")
    pos171 = source.index("install_art_studio_v171()")
    pos_app = source.index("from monitor_noticias.app.application import main")
    assert pos170 < pos171 < pos_app


def test_both_color_themes_have_explicit_palette_tokens():
    source = _source()
    assert 'dark = theme == "escuro"' in source
    for token in ("panel", "panel_alt", "border", "accent", "text", "muted", "canvas_frame", "hover"):
        assert f'{token} =' in source
    assert "return f\"\"\"" in source


def test_left_and_right_workspaces_are_made_scrollable():
    source = _source()
    assert "_improve_tab_bars(left_tabs)" in source
    assert "_improve_tab_bars(inspector_tabs)" in source
    assert "QScrollArea(tab)" in source
    assert "setWidgetResizable(True)" in source
    assert "setVerticalScrollBarPolicy" in source


def test_scroll_wrapping_preserves_existing_widgets_and_layout_items():
    source = _source()
    assert "root_layout.takeAt(0)" in source
    assert "content_layout.addWidget(widget)" in source
    assert "content_layout.addLayout(child_layout)" in source
    assert "content_layout.addItem(item)" in source


def test_canvas_is_prioritized_without_replacing_scene_or_view():
    source = _source()
    assert "page.view.setMinimumSize(440, 360)" in source
    assert "SmartViewportUpdate" in source
    assert "page.view" in source
    assert "scene.clear" not in source
    assert "setScene(" not in source


def test_splitter_keeps_all_three_panels_resizable():
    source = _source()
    for token in ("left.setMinimumWidth", "center.setMinimumWidth", "right.setMinimumWidth", "setHandleWidth(7)", "setChildrenCollapsible(False)"):
        assert token in source


def test_theme_extension_is_installed_without_replacing_v170_extension():
    source = _source()
    assert "original_stylesheet = v161._skin_stylesheet" in source
    assert "return original_stylesheet(theme) + _visual_stylesheet(theme)" in source
    assert "_v171_skin_extension_installed" in source
