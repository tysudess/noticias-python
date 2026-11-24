from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_art_studio_view_startup_compatibility_is_installed_before_page_creation():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    install_at = source.index("_install_deferred_view_compatibility()")
    page_create_at = source.index("ArtStudioPage(projects_dir, self)")
    assert install_at < page_create_at


def test_deferred_view_proxy_forwards_actual_size_after_canvas_creation():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    assert "class _DeferredArtStudioView" in source
    assert 'page.__dict__.get("_art_studio_view_actual")' in source
    assert 'view.actual_size()' in source
    assert "ArtStudioPage.view = property(" in source


def test_actual_canvas_is_returned_after_art_studio_assigns_it():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    assert 'page.__dict__["_art_studio_view_actual"] = view' in source
    assert 'actual = page.__dict__.get("_art_studio_view_actual")' in source

