from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v151_installs_after_v150_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v150()") < source.index("install_art_studio_v151()")
    assert source.index("install_art_studio_v151()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_v151_aligns_multiple_selected_objects_on_all_six_axes():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    for mode in ("left", "center_x", "right", "top", "center_y", "bottom"):
        assert f'"{mode}"' in source
    assert "def _align_selection(" in source
    assert "_selection_bounds(items)" in source
    assert "sceneBoundingRect()" in source


def test_v151_distributes_objects_with_uniform_spacing_horizontally_and_vertically():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "def _distribute_selection(" in source
    assert 'axis == "horizontal"' in source
    assert 'axis != "vertical"' in source
    assert "available_gap = (trailing - leading - sum(sizes)) / (len(items) - 1)" in source
    assert "if len(items) < 3:" in source


def test_v151_moves_nested_objects_in_scene_coordinates():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "def _move_by_scene_delta(" in source
    assert "parent.mapFromScene" in source
    assert "item.moveBy(target.x() - origin.x(), target.y() - origin.y())" in source


def test_v151_ignores_selected_descendants_when_their_group_is_selected():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "def _selected_roots(" in source
    assert "selected_set = set(selected)" in source
    assert "while parent is not None:" in source
    assert "if parent in selected_set:" in source


def test_v151_preserves_locked_and_hidden_layer_protection():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "item.isVisible() and not bool(item.data(LOCKED_KEY))" in source
    assert "len(roots) - len(eligible)" in source


def test_v151_supports_single_step_layer_reordering_without_reordering_group_children():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "def _move_layer_one_step(" in source
    assert "if item.parentItem() is None" in source
    assert "for index, item in enumerate(stack, 1):" in source
    assert "item.setZValue(float(index))" in source


def test_v151_adds_selection_commands_and_updates_controls_on_selection_changes():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    for function in ("_select_all", "_invert_selection", "_clear_selection", "_sync_controls"):
        assert f"def {function}(" in source
    assert "page.scene.selectionChanged.connect(lambda: _sync_controls(page))" in source


def test_v151_has_a_dedicated_composition_panel_and_keyboard_shortcuts():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert '"artStudioCompositionPanelV151"' in source
    assert "Ctrl+Alt+Shift+H" in source
    assert "Ctrl+Alt+Shift+V" in source
    assert "Ctrl+Alt+]" in source
    assert "Ctrl+Alt+[" in source


def test_v151_uses_only_existing_qt_dependencies_and_keeps_legacy_layers():
    source = _read("src/monitor_noticias/ui/art_studio_v151.py")
    assert "from PySide6" in source
    assert "PIL" not in source
    assert "art_studio_v150" not in source  # the previous layer is installed by run.py
    assert "install_art_studio_v150()" in _read("run.py")
