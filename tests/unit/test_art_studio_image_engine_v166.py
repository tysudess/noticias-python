from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from monitor_noticias.ui.art_studio_image_engine_v166 import (
    normalize_background_config,
    remove_background_by_corner_color,
)


def _image_bytes(width=120, height=90, background=(20, 190, 70, 255)):
    image = Image.new("RGBA", (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 18, 85, 72), fill=(210, 45, 35, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _open(raw):
    return Image.open(BytesIO(raw)).convert("RGBA")


def test_normalize_background_config_clamps_values_and_rejects_unknown_corner():
    config = normalize_background_config({
        "corner": "outside", "tolerance": 900, "softness": -10,
    })
    assert config == {"corner": "top_left", "tolerance": 255, "softness": 0}


def test_removes_only_the_background_region_connected_to_selected_corner():
    result = _open(remove_background_by_corner_color(_image_bytes(), "top_left", 0, 0))
    assert result.getpixel((2, 2))[3] == 0
    assert result.getpixel((60, 45))[3] == 255
    assert result.getpixel((110, 80))[3] == 0


def test_each_corner_can_be_used_as_the_reference_region():
    image = Image.new("RGBA", (40, 30), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 19, 29), fill=(30, 170, 60, 255))
    draw.rectangle((20, 0, 39, 29), fill=(40, 80, 210, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    left = _open(remove_background_by_corner_color(buffer.getvalue(), "top_left", 0, 0))
    right = _open(remove_background_by_corner_color(buffer.getvalue(), "top_right", 0, 0))
    assert left.getpixel((5, 10))[3] == 0
    assert left.getpixel((35, 10))[3] == 255
    assert right.getpixel((35, 10))[3] == 0
    assert right.getpixel((5, 10))[3] == 255


def test_higher_tolerance_removes_more_color_variation():
    image = Image.new("RGBA", (40, 30), (20, 180, 70, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 0, 19, 29), fill=(42, 180, 70, 255))
    draw.rectangle((20, 0, 39, 29), fill=(210, 30, 30, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    raw = buffer.getvalue()
    low = _open(remove_background_by_corner_color(raw, "top_left", 5, 0))
    high = _open(remove_background_by_corner_color(raw, "top_left", 30, 0))
    assert low.getpixel((15, 15))[3] == 255
    assert high.getpixel((15, 15))[3] == 0
    assert high.getpixel((30, 15))[3] == 255


def test_softness_creates_intermediate_alpha_on_the_cut_edge():
    raw = _image_bytes()
    crisp = _open(remove_background_by_corner_color(raw, "top_left", 0, 0))
    soft = _open(remove_background_by_corner_color(raw, "top_left", 0, 3))
    assert crisp.getchannel("A").getextrema()[0] == 0
    assert any(0 < value < 255 for value in set(soft.getchannel("A").get_flattened_data()))


def test_original_alpha_is_preserved_for_non_background_pixels():
    image = Image.new("RGBA", (50, 40), (20, 180, 70, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((15, 10, 35, 30), fill=(220, 30, 30, 128))
    image.putpixel((25, 20), (220, 30, 30, 80))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    result = _open(remove_background_by_corner_color(buffer.getvalue(), "top_left", 0, 0))
    assert result.getpixel((25, 20))[3] == 80
    assert result.getpixel((2, 2))[3] == 0


def test_invalid_data_and_oversized_inputs_fail_with_clear_errors():
    with pytest.raises(ValueError, match="abrir"):
        remove_background_by_corner_color(b"not-an-image")
    with pytest.raises(ValueError, match="40 MB"):
        remove_background_by_corner_color(b"x" * (40 * 1024 * 1024 + 1))


def test_images_smaller_than_two_pixels_are_rejected_safely():
    image = Image.new("RGBA", (1, 1), (20, 180, 70, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    with pytest.raises(ValueError, match="2 × 2"):
        remove_background_by_corner_color(buffer.getvalue())
