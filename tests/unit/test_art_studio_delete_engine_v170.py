from monitor_noticias.ui.art_studio_delete_engine_v170 import deletion_plan, selected_roots


class Item:
    def __init__(self, name, parent=None, locked=False, in_scene=True):
        self.name = name
        self.parent = parent
        self.locked = locked
        self.in_scene = in_scene


def test_selected_roots_removes_duplicates_and_descendants_of_selected_group():
    group = Item("group")
    child = Item("child", parent=group)
    sibling = Item("sibling", parent=group)
    other = Item("other")
    result = selected_roots(
        [child, group, sibling, child, other],
        parent_of=lambda item: item.parent,
    )
    assert result == [group, other]


def test_deletion_plan_only_returns_scene_items_and_preserves_locked_layers():
    normal = Item("normal")
    locked = Item("locked", locked=True)
    removed_from_scene = Item("stale", in_scene=False)
    deletable, preserved = deletion_plan(
        [normal, locked, removed_from_scene],
        parent_of=lambda item: item.parent,
        belongs_to_scene=lambda item: item.in_scene,
        is_locked=lambda item: item.locked,
    )
    assert deletable == [normal]
    assert preserved == [locked]


def test_deletion_plan_uses_parent_as_single_deletion_unit():
    group = Item("group")
    child_a = Item("a", parent=group)
    child_b = Item("b", parent=group)
    deletable, preserved = deletion_plan(
        [group, child_a, child_b],
        parent_of=lambda item: item.parent,
        belongs_to_scene=lambda item: item.in_scene,
        is_locked=lambda item: item.locked,
    )
    assert deletable == [group]
    assert preserved == []


def test_selection_can_delete_child_without_removing_unselected_parent():
    group = Item("group")
    child = Item("child", parent=group)
    deletable, _preserved = deletion_plan(
        [child],
        parent_of=lambda item: item.parent,
        belongs_to_scene=lambda item: item.in_scene,
        is_locked=lambda item: item.locked,
    )
    assert deletable == [child]


def test_locked_group_is_preserved_even_when_its_children_are_selected_too():
    group = Item("group", locked=True)
    child = Item("child", parent=group)
    deletable, preserved = deletion_plan(
        [group, child],
        parent_of=lambda item: item.parent,
        belongs_to_scene=lambda item: item.in_scene,
        is_locked=lambda item: item.locked,
    )
    assert deletable == []
    assert preserved == [group]
