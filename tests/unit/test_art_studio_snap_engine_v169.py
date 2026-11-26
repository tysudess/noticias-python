import math

from monitor_noticias.ui.art_studio_snap_engine_v169 import (
    DEFAULT_SNAP_CONFIG,
    VALID_THRESHOLDS,
    compute_smart_snap,
    normalize_snap_config,
)


def test_default_snap_config_is_deterministic():
    assert normalize_snap_config({}) == DEFAULT_SNAP_CONFIG
    assert normalize_snap_config(DEFAULT_SNAP_CONFIG) == DEFAULT_SNAP_CONFIG


def test_snap_config_parses_flags_and_normalizes_threshold():
    config = normalize_snap_config({
        "enabled": "sim", "snap_to_objects": 0,
        "snap_to_page": "false", "show_guides": "on", "threshold_px": 11,
    })
    assert config == {
        "enabled": True,
        "snap_to_objects": False,
        "snap_to_page": False,
        "snap_to_grid": False,
        "snap_to_composition_guides": True,
        "show_guides": True,
        "threshold_px": 10,
    }
    assert config["threshold_px"] in VALID_THRESHOLDS


def test_horizontal_snap_uses_nearest_edge_alignment():
    result = compute_smart_snap(
        (90, 100, 190, 180),
        [(200, 20, 300, 120)],
        (0, 0, 500, 400),
        1.0,
        12,
        snap_to_objects=True,
        snap_to_page=False,
    )
    assert result["dx"] == 10
    assert result["x_guide"] == 200
    assert result["x_relation"] == "end:start"
    assert result["dy"] == 0
    assert result["y_guide"] is None


def test_center_to_center_has_stable_alignment():
    result = compute_smart_snap(
        (95, 120, 195, 220),
        [(110, 40, 210, 140)],
        (0, 0, 500, 400),
        1.0,
        16,
        snap_to_objects=True,
        snap_to_page=False,
    )
    # X centers differ by 15 px; Y centers differ by -80 and do not snap.
    assert result["dx"] == 15
    assert result["x_guide"] == 160
    assert result["x_relation"] == "center:center"
    assert result["dy"] == 0


def test_page_edges_and_center_are_valid_snap_targets():
    edge = compute_smart_snap(
        (4, 30, 104, 90), [], (0, 0, 400, 300), 1, 6,
        snap_to_objects=False, snap_to_page=True,
    )
    center = compute_smart_snap(
        (145, 20, 245, 80), [], (0, 0, 400, 300), 1, 6,
        snap_to_objects=False, snap_to_page=True,
    )
    assert edge["dx"] == -4
    assert edge["x_guide"] == 0
    assert center["dx"] == 5
    assert center["x_guide"] == 200


def test_threshold_is_measured_in_screen_pixels_and_scales_with_zoom():
    source = (90, 0, 195, 100)
    target = [(200, 300, 300, 400)]
    at_100 = compute_smart_snap(source, target, (0, 0, 500, 500), 1, 8, snap_to_page=False)
    at_200 = compute_smart_snap(source, target, (0, 0, 500, 500), 2, 8, snap_to_page=False)
    assert at_100["dx"] == 5  # 5 scene units = 5 screen pixels.
    assert at_200["dx"] == 0  # 5 scene units = 10 screen pixels, outside tolerance.


def test_snap_respects_disabled_target_families():
    result = compute_smart_snap(
        (90, 30, 190, 130), [(200, 30, 300, 130)], (0, 0, 400, 300), 1, 20,
        snap_to_objects=False, snap_to_page=False,
    )
    assert result["dx"] == result["dy"] == 0
    assert result["x_guide"] is None
    assert result["y_guide"] is None


def test_invalid_or_non_finite_geometry_never_produces_nan_deltas():
    result = compute_smart_snap(
        (float("nan"), 0, 10, 10), [(10, 10, 20, 20)], (0, 0, 100, 100), 1, 8
    )
    assert result["dx"] == 0
    assert result["dy"] == 0
    assert math.isfinite(result["threshold_scene"])


def test_threshold_zero_allows_exact_alignment_only():
    exact = compute_smart_snap(
        (0, 0, 100, 100), [(0, 200, 100, 300)], (0, 0, 500, 500), 1, 0,
        snap_to_page=False,
    )
    near = compute_smart_snap(
        (1, 0, 101, 100), [(0, 200, 100, 300)], (0, 0, 500, 500), 1, 0,
        snap_to_page=False,
    )
    assert exact["dx"] == 0 and exact["x_guide"] == 50
    assert near["dx"] == 0 and near["x_guide"] is None


def test_snap_to_grid_aligns_nearest_anchor_with_configured_grid():
    result = compute_smart_snap(
        (91, 100, 231, 150), [], (0, 0, 500, 500), 1, 10,
        snap_to_objects=False, snap_to_page=False,
        snap_to_grid=True, grid_step=50, grid_origin=(0, 0),
    )
    assert result["dx"] == 9
    assert result["x_guide"] == 100
    assert result["x_relation"] == "grid:start"


def test_grid_origin_follows_canvas_offset_not_global_zero():
    result = compute_smart_snap(
        (130, 20, 249, 80), [], (100, 0, 600, 400), 1, 5,
        snap_to_objects=False, snap_to_page=False,
        snap_to_grid=True, grid_step=50, grid_origin=(100, 0),
    )
    assert result["dx"] == 1
    assert result["x_guide"] == 250
    assert result["x_relation"] == "grid:end"


def test_composition_guides_are_valid_independent_snap_targets():
    result = compute_smart_snap(
        (90, 20, 193, 100), [], (0, 0, 600, 400), 1, 8,
        snap_to_objects=False, snap_to_page=False,
        extra_x_lines=[200], extra_y_lines=[106],
    )
    assert result["dx"] == 7
    assert result["x_guide"] == 200
    assert result["x_relation"] == "guide:end"
    assert result["dy"] == 6
    assert result["y_guide"] == 106
    assert result["y_relation"] == "guide:end"


def test_grid_and_composition_snap_can_be_disabled_without_affecting_object_snap():
    grid_disabled = compute_smart_snap(
        (91, 20, 191, 100), [], (0, 0, 600, 400), 1, 10,
        snap_to_objects=False, snap_to_page=False, snap_to_grid=False,
        grid_step=50,
    )
    guides_disabled = compute_smart_snap(
        (90, 20, 193, 100), [], (0, 0, 600, 400), 1, 8,
        snap_to_objects=False, snap_to_page=False,
    )
    assert grid_disabled["x_guide"] is None
    assert guides_disabled["x_guide"] is None
