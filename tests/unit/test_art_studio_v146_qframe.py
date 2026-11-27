from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _integration_source() -> str:
    return (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")


def test_qframe_is_provided_to_v146_module_before_enhancer_runs():
    source = _integration_source()
    provide_at = source.index("art_studio_v146_module.QFrame = QFrame")
    enhancer_at = source.index("enhance_art_studio_page_v146,", source.index("def _enhance_art_studio_page"))
    loop_at = source.index("for enhance in enhancers:", enhancer_at)
    apply_at = source.index("enhance(page)", loop_at)
    assert provide_at < enhancer_at < loop_at < apply_at
    assert "from PySide6.QtWidgets import QFrame" in source


def test_v146_integration_keeps_v145_view_startup_compatibility():
    source = _integration_source()
    assert "class _DeferredArtStudioView" in source
    assert "_install_deferred_view_compatibility()" in source
    assert "enhance_art_studio_page," in source
    assert "enhance_art_studio_page_v146," in source
    assert "for enhance in enhancers:" in source
    assert "enhance(page)" in source


def test_v146_qframe_patch_targets_the_existing_module_and_real_lazy_page():
    source = _integration_source()
    assert "import monitor_noticias.ui.art_studio_v146 as art_studio_v146_module" in source
    assert "art_studio_v146_module.QFrame = QFrame" in source
    assert 'window.pages["ART_STUDIO"] = page' in source
    assert "page = ArtStudioPage(projects_dir, window.stack)" in source
