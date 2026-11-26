from base64 import b64encode
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw

from monitor_noticias.ui.art_studio_image_engine_v164 import (
    normalize_image_edit_config,
    render_image_source,
)


def _sample_source(width=800, height=600):
    image = Image.new("RGBA", (width, height), (220, 80, 40, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((width // 8, height // 6, width * 7 // 8, height * 5 // 6), fill=(30, 120, 210, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return b64encode(buffer.getvalue()).decode("ascii")


def _open_rendered(source, config):
    return Image.open(BytesIO(render_image_source(source, config))).convert("RGBA")


def test_render_original_preserves_source_dimensions_and_pixels():
    source = _sample_source()
    result = _open_rendered(source, {})
    original = Image.open(BytesIO(__import__("base64").b64decode(source))).convert("RGBA")
    assert result.size == (800, 600)
    assert ImageChops.difference(result, original).getbbox() is None


def test_crop_ratios_produce_expected_dimensions_without_scaling():
    source = _sample_source(800, 600)
    assert _open_rendered(source, {"crop": "1:1"}).size == (600, 600)
    assert _open_rendered(source, {"crop": "4:5"}).size == (480, 600)
    assert _open_rendered(source, {"crop": "16:9"}).size == (800, 450)
    assert _open_rendered(source, {"crop": "3:2"}).size == (800, 533)
    assert _open_rendered(source, {"crop": "9:16"}).size == (338, 600)


def test_circle_hexagon_arch_and_rounded_masks_create_transparency():
    source = _sample_source()
    for mask in ("circle", "hexagon", "arch", "rounded"):
        result = _open_rendered(source, {"mask": mask})
        alpha = result.getchannel("A")
        assert alpha.getextrema()[0] == 0
        assert alpha.getextrema()[1] == 255
    assert _open_rendered(source, {"mask": "circle"}).size == (600, 600)


def test_photo_presets_create_distinct_renderings():
    source = _sample_source()
    original = render_image_source(source, {})
    for preset in ("vivid", "mono", "sepia", "cool", "warm", "cinematic"):
        assert render_image_source(source, {"preset": preset}) != original


def test_fine_adjustments_change_pixels_and_blur_is_applied():
    source = _sample_source()
    original = render_image_source(source, {})
    adjusted = render_image_source(source, {
        "brightness": 1.4, "contrast": 1.35, "saturation": 0.5,
        "sharpness": 2.0, "blur": 2.0,
    })
    assert adjusted != original


def test_border_is_added_and_color_is_reflected_at_outer_edge():
    source = _sample_source()
    rendered = _open_rendered(source, {"border_width": 8, "border_color": "#D6B66D"})
    assert rendered.getpixel((4, 4))[:3] == (214, 182, 109)


def test_circle_border_is_drawn_around_the_mask_not_a_rectangle():
    source = _sample_source()
    rendered = _open_rendered(source, {"mask": "circle", "border_width": 8, "border_color": "#D6B66D"})
    assert rendered.getpixel((0, 0))[3] == 0
    assert rendered.getpixel((rendered.width // 2, 4))[3] > 0


def test_invalid_data_raises_clear_error_and_oversized_images_are_rejected():
    import pytest
    with pytest.raises(ValueError, match="inválida"):
        render_image_source("not-base64", {})
    source = _sample_source(5001, 5001)
    with pytest.raises(ValueError, match="25 milhões"):
        render_image_source(source, {})


def test_config_normalization_is_stable_when_applied_repeatedly():
    source = _sample_source()
    config = normalize_image_edit_config({"preset": "sepia", "mask": "circle", "border_width": 5})
    assert normalize_image_edit_config(config) == config
    assert render_image_source(source, config) == render_image_source(source, normalize_image_edit_config(config))
