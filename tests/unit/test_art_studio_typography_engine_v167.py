import pytest

from monitor_noticias.ui.art_studio_typography_engine_v167 import (
    DEFAULT_TYPOGRAPHY_CONFIG,
    TYPOGRAPHY_PRESETS,
    normalize_typography_config,
    typography_preset,
)


def test_default_typography_config_is_valid_and_deterministic():
    normalized = normalize_typography_config(DEFAULT_TYPOGRAPHY_CONFIG)
    assert normalized == DEFAULT_TYPOGRAPHY_CONFIG
    assert normalize_typography_config({}) == DEFAULT_TYPOGRAPHY_CONFIG


def test_numeric_settings_are_clamped_and_non_finite_values_fall_back():
    config = normalize_typography_config({
        "font_size": 9000,
        "weight": 777,
        "letter_spacing": -900,
        "word_spacing": float("inf"),
        "line_spacing": 20,
        "paragraph_spacing": 999,
        "outline_width": float("nan"),
    })
    assert config["font_size"] == 600
    assert config["weight"] == 800
    assert config["letter_spacing"] == -20
    assert config["word_spacing"] == 0
    assert config["line_spacing"] == 80
    assert config["paragraph_spacing"] == 120
    assert config["outline_width"] == 0


def test_enum_values_are_normalized_to_supported_choices():
    config = normalize_typography_config({"capitalization": "weird", "alignment": "diagonal"})
    assert config["capitalization"] == "mixed"
    assert config["alignment"] == "left"


def test_color_values_reject_invalid_css_values_and_keep_safe_defaults():
    config = normalize_typography_config({
        "outline_color": "url(javascript:alert(1))",
        "highlight_color": "red",
        "text_color": "#abc",
    })
    assert config["outline_color"] == "#102A43"
    assert config["highlight_color"] == "#F2D777"
    assert config["text_color"] == "#102A43"


def test_boolean_values_parse_common_portuguese_and_english_strings():
    config = normalize_typography_config({
        "italic": "sim", "underline": "false", "highlight_enabled": "on",
        "use_text_color": "não",
    })
    assert config["italic"] is True
    assert config["underline"] is False
    assert config["highlight_enabled"] is True
    assert config["use_text_color"] is False


@pytest.mark.parametrize("name", list(TYPOGRAPHY_PRESETS))
def test_each_typography_preset_produces_a_complete_safe_config(name):
    result = typography_preset(name)
    assert set(result) == set(DEFAULT_TYPOGRAPHY_CONFIG)
    assert 8 <= result["font_size"] <= 600
    assert result["alignment"] in {"left", "center", "right", "justify"}


def test_unknown_preset_falls_back_to_defaults():
    assert typography_preset("missing") == DEFAULT_TYPOGRAPHY_CONFIG
