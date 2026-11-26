from __future__ import annotations

import pytest

from monitor_noticias.ui.art_studio_workspace_engine_v175 import (
    contextual_actions,
    splitter_sizes_for_visibility,
    thumbnail_dimensions,
)


def test_thumbnail_keeps_square_page_proportion():
    assert thumbnail_dimensions(1080, 1080) == (34, 34)


def test_thumbnail_keeps_landscape_page_proportion():
    assert thumbnail_dimensions(1920, 1080) == (48, 27)


def test_thumbnail_keeps_portrait_page_proportion():
    assert thumbnail_dimensions(1080, 1920) == (19, 34)


@pytest.mark.parametrize("dimensions", [(0, 10), (10, 0), (-1, 10), (float("inf"), 10), (float("nan"), 1)])
def test_thumbnail_rejects_invalid_source_dimensions(dimensions):
    with pytest.raises(ValueError):
        thumbnail_dimensions(*dimensions)


def test_visible_split_sizes_sum_to_available_width():
    sizes = splitter_sizes_for_visibility(1500, (230, 950, 320))
    assert sum(sizes) == 1500
    assert all(value >= 0 for value in sizes)


def test_collapsing_left_panel_gives_released_width_to_canvas_and_right_panel():
    left, center, right = splitter_sizes_for_visibility(
        1500, (230, 950, 320), left_visible=False, right_visible=True
    )
    assert left == 0
    assert center + right == 1500
    assert center > right


def test_collapsing_right_panel_gives_released_width_to_canvas_and_left_panel():
    left, center, right = splitter_sizes_for_visibility(
        1500, (230, 950, 320), left_visible=True, right_visible=False
    )
    assert right == 0
    assert left + center == 1500
    assert center > left


def test_collapsing_both_side_panels_gives_entire_width_to_canvas():
    assert splitter_sizes_for_visibility(
        1500, (230, 950, 320), left_visible=False, right_visible=False
    ) == (0, 1500, 0)


def test_splitter_handles_zero_width_and_invalid_reference_shape():
    assert splitter_sizes_for_visibility(0, (230, 950, 320)) == (0, 0, 0)
    with pytest.raises(ValueError):
        splitter_sizes_for_visibility(1000, (200, 300))


def test_contextual_actions_for_empty_selection_are_empty():
    assert contextual_actions(selection_count=0) == ()


def test_contextual_actions_for_text_show_edit_duplicate_transform_delete():
    assert contextual_actions(selection_count=1, has_text=True) == (
        "duplicate", "edit_text", "transform", "delete"
    )


def test_contextual_actions_for_shape_open_shape_and_transform_tools():
    assert contextual_actions(selection_count=1, has_shape=True) == (
        "duplicate", "shape", "transform", "delete"
    )


def test_contextual_actions_for_group_offer_ungroup():
    assert contextual_actions(selection_count=1, has_group=True) == (
        "duplicate", "ungroup", "transform", "delete"
    )


def test_contextual_actions_for_multiple_objects_offer_group_only_when_supported():
    actions = contextual_actions(selection_count=3, can_group=True)
    assert actions == ("duplicate", "group", "transform", "delete")
    assert "group" not in contextual_actions(selection_count=3, can_group=False)
