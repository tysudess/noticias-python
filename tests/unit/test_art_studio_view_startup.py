import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _source() -> str:
    return (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")


def _function(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_view_compatibility_is_installed_before_deferred_page_construction():
    source = _source()
    create_function = ast.unparse(_function(source, "_create_art_studio_page"))
    compatibility_at = create_function.index("_install_deferred_view_compatibility()")
    constructor_at = create_function.index("ArtStudioPage(projects_dir, window.stack)")
    assert compatibility_at < constructor_at


def test_deferred_view_proxy_supports_early_zoom_connection_and_real_view_assignment():
    source = _source()
    for token in (
        "class _DeferredArtStudioView",
        "def actual_size(self)",
        "_art_studio_view_actual",
        "_art_studio_view_deferred",
        "ArtStudioPage.view = property(",
    ):
        assert token in source


def test_combined_integration_keeps_v145_and_v146_enhancements_in_order():
    source = _source()
    start = source.index("def _enhance_art_studio_page")
    v145 = source.index("enhance_art_studio_page,", start)
    v146 = source.index("enhance_art_studio_page_v146,", start)
    loop = source.index("for enhance in enhancers:", start)
    apply_call = source.index("enhance(page)", loop)
    assert v145 < v146 < loop < apply_call


def test_view_compatibility_is_not_installed_by_main_window_startup_wrapper():
    source = _source()
    startup_function = ast.unparse(_function(source, "init_with_art_studio"))
    assert "_install_deferred_view_compatibility" not in startup_function
    assert "ArtStudioPage" not in startup_function
