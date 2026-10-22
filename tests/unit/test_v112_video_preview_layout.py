from __future__ import annotations

from pathlib import Path

from monitor_noticias.ui.video_preview_layout_patch import (
    PREVIEW_MAX_HEIGHT,
    PREVIEW_MIN_HEIGHT,
    preview_height_for_width,
)

ROOT = Path(__file__).resolve().parents[2]


def test_preview_uses_near_16_9_height_on_desktop():
    assert preview_height_for_width(960) == 540
    assert preview_height_for_width(1180) == PREVIEW_MAX_HEIGHT == 660


def test_preview_height_adapts_for_narrower_windows():
    assert preview_height_for_width(640) == PREVIEW_MIN_HEIGHT == 360
    assert preview_height_for_width(800) == 450


def test_preview_height_is_bounded_and_handles_invalid_width():
    assert preview_height_for_width(3000) == 660
    assert preview_height_for_width(0) == 360
    assert preview_height_for_width(-100) == 360


def test_preview_patch_is_installed_from_composition():
    composition = (ROOT / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    assert "install_video_preview_layout_patch" in composition
    patch = (ROOT / "src/monitor_noticias/ui/video_preview_layout_patch.py").read_text(encoding="utf-8")
    assert "cls._apply_reference_style = apply_large_preview" in patch
    assert "cls.resizeEvent = resize_with_large_preview" in patch
    assert "QTimer.singleShot(0, deferred_update)" in patch
