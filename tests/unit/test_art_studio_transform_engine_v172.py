from __future__ import annotations

import pytest

from monitor_noticias.ui.art_studio_transform_engine_v172 import (
    alignment_delta,
    clamp_opacity,
    distribution_offsets,
    has_locked_descendant,
    proportional_size,
    selected_roots,
)


class Node:
    def __init__(self, parent=None):
        self.parent = parent


def test_selected_roots_deduplicates_and_removes_selected_descendants():
    parent = Node()
    child = Node(parent)
    grandchild = Node(child)
    other = Node()
    assert selected_roots(
        [child, parent, child, grandchild, other],
        lambda item: item.parent,
    ) == [parent, other]



def test_proportional_size_uses_width_as_driver():
    assert proportional_size(400, 200, 600, 900, keep_ratio=True, changed_axis="width") == (600, 300)


def test_proportional_size_uses_height_as_driver():
    assert proportional_size(400, 200, 600, 450, keep_ratio=True, changed_axis="height") == (900, 450)


def test_proportional_size_allows_independent_axes_when_unlocked():
    assert proportional_size(400, 200, 600, 450, keep_ratio=False) == (600, 450)


def test_proportional_size_clamps_zero_dimensions():
    assert proportional_size(0, 0, 0, -1, keep_ratio=False) == (1, 1)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("left", (-50, 0)),
        ("center-h", (50, 0)),
        ("right", (150, 0)),
        ("top", (0, -50)),
        ("center-v", (0, 50)),
        ("bottom", (0, 150)),
    ],
)
def test_alignment_delta_for_all_six_page_anchors(mode, expected):
    assert alignment_delta((50, 50, 100, 100), (0, 0, 300, 300), mode) == expected


def test_alignment_delta_respects_nonzero_page_origin():
    assert alignment_delta((15, 30, 20, 20), (10, 20, 100, 80), "right") == (75, 0)


def test_alignment_delta_rejects_unknown_mode():
    with pytest.raises(ValueError):
        alignment_delta((0, 0, 1, 1), (0, 0, 10, 10), "middle-ish")


def test_distribution_offsets_equalizes_gaps_and_preserves_extremes():
    offsets = distribution_offsets([(0, 10), (30, 40), (90, 100)])
    moved = [(0 + offsets[0], 10 + offsets[0]), (30 + offsets[1], 40 + offsets[1]), (90 + offsets[2], 100 + offsets[2])]
    gaps = [moved[1][0] - moved[0][1], moved[2][0] - moved[1][1]]
    assert gaps[0] == pytest.approx(gaps[1])
    assert moved[0][0] == 0
    assert moved[-1][1] == 100


def test_distribution_offsets_preserves_original_order_mapping_for_unsorted_input():
    offsets = distribution_offsets([(90, 100), (0, 10), (30, 40)])
    assert offsets[1] == pytest.approx(0)
    assert offsets[0] == pytest.approx(0)
    assert offsets[2] == pytest.approx(15)


def test_distribution_offsets_handles_duplicate_intervals_deterministically():
    offsets = distribution_offsets([(0, 10), (0, 10), (20, 30)])
    assert len(offsets) == 3
    assert offsets[0] == pytest.approx(0)
    assert offsets[2] == pytest.approx(0)


def test_distribution_requires_three_items():
    with pytest.raises(ValueError):
        distribution_offsets([(0, 10), (20, 30)])


@pytest.mark.parametrize(("value", "expected"), [(-10, 0.0), (0, 0.0), (35, 0.35), (100, 1.0), (150, 1.0)])
def test_clamp_opacity(value, expected):
    assert clamp_opacity(value) == pytest.approx(expected)


def test_group_with_locked_descendant_is_protected_from_transformations():
    root = Node()
    unlocked_child = Node(root)
    locked_child = Node(unlocked_child)
    assert has_locked_descendant(
        root,
        children_of=lambda item: [child for child in (unlocked_child, locked_child) if child.parent is item],
        is_locked=lambda item: item is locked_child,
    )


def test_group_without_locked_descendants_can_be_transformed():
    root = Node()
    child = Node(root)
    assert not has_locked_descendant(
        root,
        children_of=lambda item: [child] if item is root else [],
        is_locked=lambda _item: False,
    )
