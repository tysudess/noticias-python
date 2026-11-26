from __future__ import annotations

import pytest

from monitor_noticias.ui.art_studio_workspace_engine_v176 import (
    normalize_selection_bounds,
    page_grid_columns,
    page_preview_size,
    selection_summary,
)


def test_page_preview_keeps_square_ratio():
    assert page_preview_size(1080, 1080) == (142, 142)


def test_page_preview_keeps_landscape_ratio():
    assert page_preview_size(1920, 1080) == (232, 130)


def test_page_preview_keeps_portrait_ratio():
    assert page_preview_size(1080, 1920) == (80, 142)


@pytest.mark.parametrize("dimensions", [(0, 10), (10, 0), (-1, 10), (float("nan"), 4), (float("inf"), 2)])
def test_preview_rejects_invalid_dimensions(dimensions):
    with pytest.raises(ValueError):
        page_preview_size(*dimensions)


def test_grid_columns_adapt_to_available_width():
    assert page_grid_columns(250) == 1
    assert page_grid_columns(530) == 2
    assert page_grid_columns(820) == 3
    assert page_grid_columns(1400) == 4


def test_grid_columns_have_safe_bounds_for_small_and_negative_widths():
    assert page_grid_columns(0) == 1
    assert page_grid_columns(-100) == 1
    assert page_grid_columns(5000, max_columns=2) == 2


def test_selection_bounds_combines_multiple_objects():
    assert normalize_selection_bounds([(10, 20, 100, 40), (40, 5, 70, 80)]) == (10, 5, 100, 80)


def test_selection_bounds_returns_none_for_empty_selection():
    assert normalize_selection_bounds([]) is None


def test_selection_bounds_rejects_invalid_values():
    with pytest.raises(ValueError):
        normalize_selection_bounds([(0, 0, float("inf"), 2)])
    with pytest.raises(ValueError):
        normalize_selection_bounds([(1, 2, 3)])


def test_selection_summary_includes_rotation_and_opacity():
    result = selection_summary([(10, 20, 100, 60)], rotation=30, opacity=0.45)
    assert result == {
        "x": 10.0,
        "y": 20.0,
        "width": 100.0,
        "height": 60.0,
        "rotation": 30.0,
        "opacity": 0.45,
    }


def test_selection_summary_clamps_opacity():
    assert selection_summary([(0, 0, 10, 10)], opacity=1.7)["opacity"] == 1.0
    assert selection_summary([(0, 0, 10, 10)], opacity=-0.2)["opacity"] == 0.0


def test_selection_summary_rejects_non_finite_angle():
    with pytest.raises(ValueError):
        selection_summary([(0, 0, 10, 10)], rotation=float("nan"))
