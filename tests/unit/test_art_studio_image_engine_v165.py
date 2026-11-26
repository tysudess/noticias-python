from base64 import b64encode, b64decode
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw
import pytest

from monitor_noticias.ui.art_studio_image_engine_v165 import (
    DEFAULT_ADVANCED_IMAGE_CONFIG,
    normalize_advanced_image_config,
    render_image_source_v165,
)
from monitor_noticias.ui.art_studio_image_engine_v164 import render_image_source


def _source(width=800, height=600):
    image = Image.new("RGBA", (width, height), (230, 70, 35, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width // 4, height), fill=(25, 180, 90, 255))
    draw.rectangle((width * 3 // 4, 0, width - 1, height), fill=(35, 80, 220, 255))
    draw.ellipse((width // 3, height // 4, width * 2 // 3, height * 3 // 4), fill=(245, 210, 40, 180))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return b64encode(buffer.getvalue()).decode("ascii")


def _open(raw):
    return Image.open(BytesIO(raw)).convert("RGBA")


def test_default_advanced_config_is_stable_and_matches_v164_render():
    source = _source()
    base = {"preset": "vivid", "brightness": 1.1, "crop": "4:5"}
    expected = _open(render_image_source(source, base))
    actual = _open(render_image_source_v165(source, base, {}))
    assert actual.size == expected.size
    assert ImageChops.difference(actual, expected).getbbox() is None
    assert normalize_advanced_image_config(DEFAULT_ADVANCED_IMAGE_CONFIG) == DEFAULT_ADVANCED_IMAGE_CONFIG


def test_advanced_config_clamps_numbers_and_rotation_values():
    config = normalize_advanced_image_config({
        "temperature": 900, "tint": -900, "highlights": float("nan"),
        "shadows": -900, "vignette": 500, "fade": -2,
        "crop_zoom": 50, "focus_x": -10, "focus_y": 140,
        "rotation": 45, "flip_h": "false", "flip_v": 0,
    })
    assert config["temperature"] == 100
    assert config["tint"] == -100
    assert config["highlights"] == 0
    assert config["shadows"] == -100
    assert config["vignette"] == 100
    assert config["fade"] == 0
    assert config["crop_zoom"] == 3
    assert config["focus_x"] == 0
    assert config["focus_y"] == 100
    assert config["rotation"] == 0
    assert config["flip_h"] is False
    assert config["flip_v"] is False


def test_temperature_tint_highlights_shadows_vignette_and_fade_change_pixels():
    source = _source()
    base = {}
    original = render_image_source_v165(source, base, {})
    settings = (
        {"temperature": 85}, {"temperature": -85}, {"tint": 80},
        {"tint": -80}, {"highlights": 80}, {"shadows": -80},
        {"vignette": 85}, {"fade": 85},
    )
    for config in settings:
        assert render_image_source_v165(source, base, config) != original


def test_focal_crop_preserves_requested_ratio_and_zoom_changes_crop_size():
    source = _source(800, 600)
    normal = _open(render_image_source_v165(source, {"crop": "16:9"}, {}))
    zoomed = _open(render_image_source_v165(source, {"crop": "16:9"}, {"crop_zoom": 2}))
    assert normal.size == (800, 450)
    assert zoomed.size == (400, 225)
    assert round(zoomed.width / zoomed.height, 5) == round(16 / 9, 5)


def test_focal_position_selects_different_regions_without_changing_dimensions():
    source = _source(800, 600)
    left = _open(render_image_source_v165(source, {"crop": "4:5"}, {
        "crop_zoom": 1.5, "focus_x": 0, "focus_y": 50,
    }))
    right = _open(render_image_source_v165(source, {"crop": "4:5"}, {
        "crop_zoom": 1.5, "focus_x": 100, "focus_y": 50,
    }))
    assert left.size == right.size == (320, 400)
    assert ImageChops.difference(left, right).getbbox() is not None


def test_zoom_without_fixed_ratio_keeps_original_aspect_ratio():
    source = _source(800, 600)
    result = _open(render_image_source_v165(source, {}, {"crop_zoom": 2.0}))
    assert result.size == (400, 300)


def test_rotations_swap_dimensions_and_reflections_reposition_pixels():
    source = _source(800, 600)
    rotated = _open(render_image_source_v165(source, {}, {"rotation": 90}))
    assert rotated.size == (600, 800)
    original = _open(render_image_source_v165(source, {}, {}))
    mirrored = _open(render_image_source_v165(source, {}, {"flip_h": True}))
    assert mirrored.size == original.size
    assert ImageChops.difference(mirrored, original).convert("RGB").getbbox() is not None


def test_advanced_processing_preserves_alpha_channel_and_transparency():
    source = _source()
    result = _open(render_image_source_v165(source, {"mask": "circle"}, {
        "temperature": 65, "vignette": 45, "rotation": 90,
    }))
    assert result.getchannel("A").getextrema()[0] == 0
    assert result.getchannel("A").getextrema()[1] > 0


def test_invalid_source_is_rejected_with_clear_error():
    with pytest.raises(ValueError, match="inválida"):
        render_image_source_v165("not-base64", {}, {})
