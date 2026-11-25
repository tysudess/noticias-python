from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v152_installs_after_v151_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v151()") < source.index("install_art_studio_v152()")
    assert source.index("install_art_studio_v152()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_v152_supports_horizontal_and_vertical_flip_with_center_preservation():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert '"flip_h", "flip_v"' in source
    assert "QTransform.fromScale(-1.0, 1.0)" in source
    assert "QTransform.fromScale(1.0, -1.0)" in source
    assert "center_before = item.mapToScene(item.boundingRect().center())" in source
    assert "correction = center_before - center_after" in source


def test_v152_rotates_multiple_objects_in_both_directions():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert '"rotate_left", "rotate_right"' in source
    assert "delta = -90.0 if operation == \"rotate_left\" else 90.0" in source


def test_v152_applies_opacity_to_multiple_editable_objects():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert "def _apply_batch_opacity(page)" in source
    assert "item.setOpacity(opacity)" in source


def test_v152_copies_and_pastes_compatible_styles():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    for token in ("def _copy_style(page)", "def _paste_style(page)", 'style["font"]', 'style["brush"]', 'style["frame"]'):
        assert token in source
    assert "_effect_from_data(item, deepcopy(effect))" in source


def test_v152_duplicates_multiple_objects_and_regenerates_history_ids():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert "def _duplicate_selection(page)" in source
    assert "page._serialize_item(item)" in source
    assert "page._build_item_from_data(serialized)" in source
    assert "def _renew_history_ids(item" in source
    assert "uuid.uuid4().hex" in source


def test_v152_keeps_multi_object_z_order_relative_order():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert "def _move_selection_to_extreme(page, direction: str)" in source
    assert "ordered = sorted(items, key=lambda item: item.zValue())" in source
    assert 'label = "frente"' in source
    assert 'label = "fundo"' in source


def test_v152_skips_locked_and_hidden_objects_in_batch_operations():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert "item.isVisible() and not bool(item.data(LOCKED_KEY))" in source
    assert "len(roots) - len(editable)" in source


def test_v152_has_a_dedicated_panel_and_selection_observers():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert '"TRANSFORMAÇÃO E EDIÇÃO EM LOTE"' in source
    assert '"artStudioTransformPanelV152"' in source
    assert "page.scene.selectionChanged.connect" in source
    assert "page.layers.currentItemChanged.connect" in source


def test_v152_does_not_add_runtime_dependencies_or_change_project_format():
    source = _read("src/monitor_noticias/ui/art_studio_v152.py")
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert "PROJECT_VERSION" not in source
    assert "pip install" not in source.lower()
