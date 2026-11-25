from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_qframe_is_provided_to_v146_module_before_enhancer_runs():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    provide_at = source.index("art_studio_v146_module.QFrame = QFrame")
    enhance_at = source.index("enhance_art_studio_page_v146(self.art_studio_page)")
    assert provide_at < enhance_at
    assert "from PySide6.QtWidgets import QFrame" in source


def test_v146_integration_keeps_v145_view_startup_compatibility():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    assert "class _DeferredArtStudioView" in source
    assert "_install_deferred_view_compatibility()" in source
    assert "enhance_art_studio_page(self.art_studio_page)" in source


def test_v146_qframe_patch_targets_the_existing_module_not_a_replacement_page():
    source = (ROOT / "src/monitor_noticias/ui/art_studio_integration.py").read_text(encoding="utf-8")
    assert "import monitor_noticias.ui.art_studio_v146 as art_studio_v146_module" in source
    assert "art_studio_v146_module.QFrame = QFrame" in source
    assert "self.pages[\"ART_STUDIO\"] = self.art_studio_page" in source
