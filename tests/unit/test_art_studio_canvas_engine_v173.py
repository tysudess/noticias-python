from __future__ import annotations

import pytest

from monitor_noticias.ui.art_studio_canvas_engine_v173 import (
    normalize_stroke_style,
    normalize_stroke_width,
    resized_rect,
    resize_bounds_for_handles,
    rotation_delta,
    snap_rotation,
    uniform_scale_factor,
)


def test_bottom_right_handle_resizes_rectangle_in_both_axes():
    assert resized_rect((10, 20, 100, 60), (150, 100), (1, 1)) == (10, 20, 140, 80)


def test_top_left_handle_keeps_opposite_corner_fixed():
    assert resized_rect((10, 20, 100, 60), (-20, -10), (-1, -1)) == (-20, -10, 130, 90)


def test_left_edge_keeps_right_edge_fixed():
    assert resized_rect((10, 20, 100, 60), (-15, 24), (-1, 0)) == (-15, 20, 125, 60)


def test_bottom_edge_keeps_top_edge_fixed():
    assert resized_rect((10, 20, 100, 60), (15, 140), (0, 1)) == (10, 20, 100, 120)


def test_resize_clamps_to_minimum_size():
    assert resized_rect((0, 0, 50, 40), (100, 100), (-1, -1), minimum=12) == (38, 28, 12, 12)


def test_resize_with_ratio_preserves_starting_ratio_from_corner():
    x, y, width, height = resized_rect((0, 0, 160, 80), (320, 180), (1, 1), keep_ratio=True)
    assert width / height == pytest.approx(2.0)
    assert (x, y) == (0, 0)


@pytest.mark.parametrize(
    ("direction", "pointer", "expected"),
    [
        ((1, 1), (200, 100), 2.0),
        ((-1, -1), (-100, -50), 2.0),
        ((1, 1), (25, 12.5), 0.25),
    ],
)
def test_uniform_scale_uses_opposite_anchor(direction, pointer, expected):
    assert uniform_scale_factor((0, 0, 100, 50), pointer, direction) == pytest.approx(expected)


def test_uniform_scale_clamps_lower_and_upper_bounds():
    assert uniform_scale_factor((0, 0, 100, 50), (-100, -50), (1, 1), minimum_factor=0.1) == 0.1
    assert uniform_scale_factor((0, 0, 100, 50), (900, 450), (1, 1), maximum_factor=4.0) == 4.0


def test_rotation_delta_crosses_positive_and_negative_angle_boundary():
    assert rotation_delta((1, 0), (0, 1)) == pytest.approx(90.0)
    assert rotation_delta((1, 0), (0, -1)) == pytest.approx(-90.0)
    assert rotation_delta((-1, 0), (0, 1)) == pytest.approx(-90.0)


def test_rotation_delta_returns_zero_for_center_vector():
    assert rotation_delta((0, 0), (10, 10)) == 0.0


@pytest.mark.parametrize(("value", "expected"), [(7, 0), (7.4, 0), (7.6, 15), (-7.6, -15), (22, 15), (23, 30)])
def test_snap_rotation_uses_fifteen_degree_steps(value, expected):
    assert snap_rotation(value, 15) == expected


def test_snap_rotation_rejects_invalid_increment():
    with pytest.raises(ValueError):
        snap_rotation(30, 0)


@pytest.mark.parametrize(("value", "expected"), [("solid", "solid"), ("dash", "dash"), ("dot", "dot"), ("unknown", "solid"), (None, "solid")])
def test_normalize_stroke_style(value, expected):
    assert normalize_stroke_style(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(-3, 0), (0, 0), (2.5, 2.5), (48, 48), (100, 48)])
def test_normalize_stroke_width(value, expected):
    assert normalize_stroke_width(value) == expected


def test_handle_layout_produces_eight_evenly_positioned_handles():
    points = resize_bounds_for_handles((10, 20, 100, 60), [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)])
    assert points == [
        (10, 20), (60, 20), (110, 20), (110, 50),
        (110, 80), (60, 80), (10, 80), (10, 50),
    ]


def test_resized_rect_rejects_invalid_direction_and_non_finite_values():
    with pytest.raises(ValueError):
        resized_rect((0, 0, 10, 10), (2, 2), (0, 0))
    with pytest.raises(ValueError):
        resized_rect((0, 0, 10, 10), (float("nan"), 5), (1, 1))


def test_uniform_scale_rejects_edge_handles():
    with pytest.raises(ValueError):
        uniform_scale_factor((0, 0, 100, 50), (100, 50), (1, 0))
