from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_view_compatibility_is_installed_before_main_window_creation():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    install_at = source.index("_install_deferred_view_compatibility()", source.index("def install_art_studio"))
    original_init_at = source.index("original_init = MainWindow.__init__")
    assert install_at < original_init_at


def test_deferred_view_proxy_supports_early_zoom_connection_and_real_view_assignment():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    for token in (
        "class _DeferredArtStudioView",
        "def actual_size(self)",
        "_art_studio_view_actual",
        "_art_studio_view_deferred",
        "ArtStudioPage.view = property(",
    ):
        assert token in source


def test_combined_integration_keeps_v145_and_v146_enhancements_in_order():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    v145 = source.index("enhance_art_studio_page(self.art_studio_page)")
    v146 = source.index("enhance_art_studio_page_v146(self.art_studio_page)")
    assert v145 < v146
