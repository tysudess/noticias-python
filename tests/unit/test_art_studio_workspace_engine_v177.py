from __future__ import annotations

import math
import pytest

from monitor_noticias.ui.art_studio_workspace_engine_v177 import (
    layer_context_actions,
    layer_order_z_values,
    library_grid_columns,
    nearest_zoom_preset,
    zoom_factor_to_target,
)


def test_library_grid_switches_between_one_and_two_columns():
    assert library_grid_columns(0) == 1
    assert library_grid_columns(120) == 1
    assert library_grid_columns(195) == 2
    assert library_grid_columns(700) == 2


def test_library_grid_has_safe_bounds_for_custom_width_and_column_limits():
    assert library_grid_columns(900, max_columns=4) == 4
    assert library_grid_columns(900, min_card_width=180, max_columns=4) == 4
    assert library_grid_columns(-50) == 1


def test_library_grid_never_uses_invalid_minimum_card_width_or_gap():
    assert library_grid_columns(180, min_card_width=1, gap=-4) >= 1


def test_layer_z_order_keeps_first_row_at_front():
    assert layer_order_z_values(4) == (4.0, 3.0, 2.0, 1.0)


def test_layer_z_order_empty_and_single_layer():
    assert layer_order_z_values(0) == ()
    assert layer_order_z_values(1) == (1.0,)


def test_context_menu_empty_selection_has_no_actions():
    assert layer_context_actions(selection_count=0, all_unlocked=True) == ()


def test_context_menu_single_unlocked_image_has_full_layer_actions():
    assert layer_context_actions(
        selection_count=1, all_unlocked=True, single_kind="image"
    ) == ("rename", "visibility", "lock", "duplicate", "front", "back", "delete")


def test_context_menu_single_group_adds_ungroup():
    assert "ungroup" in layer_context_actions(
        selection_count=1, all_unlocked=True, single_kind="group"
    )


def test_context_menu_locked_layer_hides_destructive_transform_actions_but_keeps_delete():
    actions = layer_context_actions(selection_count=1, all_unlocked=False, single_kind="text")
    assert actions == ("rename", "visibility", "lock", "delete")


def test_context_menu_multiple_selection_offers_group_when_unlocked():
    actions = layer_context_actions(selection_count=3, all_unlocked=True)
    assert actions == ("lock", "duplicate", "front", "back", "group", "delete")


def test_context_menu_multiple_selection_with_locked_layer_keeps_safe_actions():
    actions = layer_context_actions(selection_count=3, all_unlocked=False)
    assert actions == ("lock", "delete")


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [(100, 50, 0.5), (50, 100, 2.0), (125, 200, 1.6), (75, 75, 1.0)],
)
def test_zoom_factor_to_target(current, target, expected):
    assert zoom_factor_to_target(current, target) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("current", "target"),
    [(0, 100), (-1, 100), (float("nan"), 100), (100, float("inf")), (100, 5), (100, 501)],
)
def test_zoom_factor_rejects_invalid_values(current, target):
    with pytest.raises(ValueError):
        zoom_factor_to_target(current, target)


def test_nearest_zoom_preset_chooses_closest_and_breaks_ties_downward():
    assert nearest_zoom_preset(102) == 100
    assert nearest_zoom_preset(112.5) == 100
    assert nearest_zoom_preset(180) == 200


def test_nearest_zoom_preset_rejects_invalid_zoom_or_empty_presets():
    with pytest.raises(ValueError):
        nearest_zoom_preset(math.nan)
    with pytest.raises(ValueError):
        nearest_zoom_preset(100, presets=())
