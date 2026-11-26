import math

from monitor_noticias.ui.art_studio_guides_engine_v168 import (
    DEFAULT_GUIDE_CONFIG,
    composition_guide_positions,
    normalize_guide_config,
    visible_grid_positions,
)


def test_default_guide_config_is_deterministic():
    assert normalize_guide_config({}) == DEFAULT_GUIDE_CONFIG
    assert normalize_guide_config(DEFAULT_GUIDE_CONFIG) == DEFAULT_GUIDE_CONFIG


def test_config_normalization_clamps_unknown_grid_step_and_parses_flags():
    normalized = normalize_guide_config({
        "grid_enabled": "sim", "grid_step": 37,
        "thirds_enabled": 1, "center_enabled": "false", "safe_area_enabled": "on",
    })
    assert normalized == {
        "grid_enabled": True, "grid_step": 50, "thirds_enabled": True,
        "center_enabled": False, "safe_area_enabled": True,
    }


def test_grid_positions_respect_canvas_and_visible_bounds():
    grid = visible_grid_positions((1000, 800), (125, 80, 380, 260), 50, 1.0)
    assert grid["vertical"] == [150, 200, 250, 300, 350]
    assert grid["horizontal"] == [100, 150, 200, 250]
    assert grid["effective_step"] == 50
    assert all(0 <= x <= 1000 for x in grid["vertical"])
    assert all(0 <= y <= 800 for y in grid["horizontal"])


def test_grid_adapts_to_low_zoom_and_limits_dense_lines():
    dense = visible_grid_positions((5000, 5000), (0, 0, 5000, 5000), 10, 0.01)
    assert dense["effective_step"] >= 1400
    assert len(dense["vertical"]) <= 180
    assert len(dense["horizontal"]) <= 180


def test_grid_rejects_invalid_canvas_and_zoom_values():
    assert visible_grid_positions((0, 800), (0, 0, 100, 100), 50, 1) == {
        "vertical": [], "horizontal": [], "effective_step": 0.0,
    }
    assert visible_grid_positions((100, 100), (0, 0, 100, 100), 50, math.nan)["vertical"] == []


def test_composition_guides_are_correct_for_standard_canvas():
    guides = composition_guide_positions((1200, 800))
    assert guides["vertical_thirds"] == [400, 800]
    assert guides["horizontal_thirds"] == [800 / 3, 1600 / 3]
    assert guides["center"] == (600, 400)
    assert guides["safe_rect"] == (60, 40, 1140, 760)


def test_composition_guides_handle_invalid_dimensions():
    assert composition_guide_positions((0, 800))["center"] is None
    assert composition_guide_positions((100, -2))["safe_rect"] is None
