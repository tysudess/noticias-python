from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v146_adds_group_and_ungroup_actions():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    for token in (
        "def _group_selected(",
        "def _ungroup_selected(",
        "QGraphicsItemGroup",
        "Ctrl+G",
        "Ctrl+Shift+G",
        '"children": [_serialize_item(page, child) for child in children]',
    ):
        assert token in source


def test_v146_persists_group_contents_in_centralart_projects():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    assert '"kind": "group"' in source
    assert 'data.get("children", [])' in source
    assert 'page._serialize_item = lambda item: _serialize_item(page, item)' in source
    assert 'page._build_item_from_data = lambda data: _build_item(page, data)' in source


def test_v146_adds_photo_adjustments_with_alpha_preservation():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    for token in (
        "ImageEnhance.Brightness",
        "ImageEnhance.Contrast",
        "ImageEnhance.Color",
        "ImageEnhance.Sharpness",
        'alpha = image.getchannel("A")',
        "def _apply_photo_adjustments(",
        "class _PhotoAdjustDialog",
    ):
        assert token in source


def test_v146_adds_persisted_frame_and_shadow_effects():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    for token in (
        "QGraphicsDropShadowEffect",
        "def _apply_image_frame(",
        "def _apply_visual_effect(",
        'data["v146_effect"]',
        'data["v146_frame"]',
        "def _effect_from_data(",
    ):
        assert token in source


def test_v146_excludes_internal_frame_overlays_from_saved_layer_list():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    assert "def _top_level_items(" in source
    assert 'if child.data(FRAME_CHILD_KEY)' in source
    assert 'page._content_items = lambda: _top_level_items(page)' in source


def test_v146_is_installed_after_existing_v145_enhancements():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    v145 = source.index("enhance_art_studio_page(self.art_studio_page)")
    v146 = source.index("enhance_art_studio_page_v146(self.art_studio_page)")
    assert v145 < v146


def test_v146_keeps_existing_runtime_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v146.py")
    assert "from PIL import Image, ImageEnhance" in source
    assert "from PySide6.QtWidgets import" in source
    assert "import cv2" not in source
    assert "import numpy" not in source
