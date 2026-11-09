from __future__ import annotations

import pytest

from monitor_noticias.video_editor.output_format import (
    LANDSCAPE_16_9_FORMAT,
    ORIGINAL_FORMAT,
    decode_resolution_choice,
    encode_resolution_choice,
    landscape_canvas_dimensions,
)


def test_original_choice_is_not_encoded_or_changed():
    assert encode_resolution_choice("Original", ORIGINAL_FORMAT) == "Original"
    assert decode_resolution_choice("Original") == (ORIGINAL_FORMAT, "Original")


def test_landscape_choice_round_trips_with_resolution():
    encoded = encode_resolution_choice("720p", LANDSCAPE_16_9_FORMAT)
    assert decode_resolution_choice(encoded) == (LANDSCAPE_16_9_FORMAT, "720p")


def test_landscape_720p_uses_1280_by_720_canvas():
    assert landscape_canvas_dimensions({"width": 1080, "height": 1920}, "720p") == (1280, 720)


def test_landscape_1080p_uses_1920_by_1080_canvas():
    assert landscape_canvas_dimensions({"width": 720, "height": 1280}, "1080p") == (1920, 1080)


def test_landscape_original_uses_source_long_side_without_upscaling():
    assert landscape_canvas_dimensions({"width": 720, "height": 1280}, "Original") == (1280, 720)
    assert landscape_canvas_dimensions({"width": 1920, "height": 1080}, "Original") == (1920, 1080)
    assert landscape_canvas_dimensions({"width": 640, "height": 360}, "Original") == (640, 360)


def test_landscape_original_caps_canvas_at_full_hd():
    assert landscape_canvas_dimensions({"width": 2160, "height": 3840}, "Original") == (1920, 1080)


def test_every_landscape_canvas_is_even_and_16_by_9_approximately():
    for resolution in ("Original", "360p", "480p", "720p", "1080p"):
        width, height = landscape_canvas_dimensions({"width": 1080, "height": 1920}, resolution)
        assert width % 2 == 0
        assert height % 2 == 0
        assert width / height == pytest.approx(16 / 9, abs=0.003)
