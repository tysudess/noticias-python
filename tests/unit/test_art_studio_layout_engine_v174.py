from __future__ import annotations

import pytest

from monitor_noticias.ui.art_studio_layout_engine_v174 import (
    compact_pages_bar_metrics,
    workspace_split_sizes,
)


@pytest.mark.parametrize("width", [620, 780, 1024, 1280, 1440, 1600, 1920, 2560])
def test_split_sizes_are_nonnegative_and_exactly_fill_available_width(width):
    sizes = workspace_split_sizes(width)
    assert len(sizes) == 3
    assert all(value >= 0 for value in sizes)
    assert sum(sizes) == width


def test_large_workspace_prioritizes_center_canvas():
    left, center, right = workspace_split_sizes(1700)
    assert left <= 258
    assert right <= 348
    assert center > left + right
    assert center >= 1000


def test_regular_workspace_respects_panel_and_canvas_minimums():
    left, center, right = workspace_split_sizes(1500)
    assert left >= 184
    assert center >= 560
    assert right >= 246


def test_compact_pages_bar_reduces_height_and_control_dimensions():
    metrics = compact_pages_bar_metrics()
    assert metrics["height"] == 46
    assert metrics["button_height"] == 28
    assert metrics["vertical_margin"] == 4
    collapsed = compact_pages_bar_metrics(expanded=False)
    assert collapsed["height"] == 0


def test_split_sizes_stay_valid_for_narrow_windows():
    for width in range(1, 620):
        left, center, right = workspace_split_sizes(width)
        assert min(left, center, right) >= 0
        assert left + center + right == width
