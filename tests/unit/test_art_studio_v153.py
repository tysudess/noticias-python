from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v153_installs_after_v152_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v152()") < source.index("install_art_studio_v153()")
    assert source.index("install_art_studio_v153()") < source.index("from monitor_noticias.app.application import main")


def test_v153_does_not_destroy_resize_handles_during_mouse_move():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    move = source.split("def _resize_handle_move", 1)[1].split("def _resize_handle_release", 1)[0]
    assert "_v148_sync_handles" not in move
    assert "_position_handles(target)" in move
    assert "sceneTransform().inverted()" in source


def test_v153_resizes_text_and_image_while_preserving_anchor_and_center():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    assert "target.setTextWidth(new_width)" in source
    assert "_anchor_scene - new_anchor" in source
    assert "center_before - center_after" in source
    assert "item.setScale(item.scale() * factor)" in source
    assert "transform.m11() * sx" in source
    assert "transform.m22() * sy" in source


def test_v153_keeps_image_transform_and_ratio_controls_consistent():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    assert "item.transform().mapRect(item.boundingRect())" in source
    assert "page.v148_ratio_check.isChecked()" in source
    assert "QTransform(" in source


def test_v153_restores_existing_scene_objects_and_avoids_insertion_overlap():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    assert "def _restore_previous_objects" in source
    assert "def _place_in_free_area" in source
    assert "existing.scene() is not page.scene" in source
    assert "_place_in_free_area(page, item, previous_items)" in source


def test_v153_adds_compact_sidebar_toggle_without_removing_navigation_items():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    assert "sidebar.setFixedWidth(82 if compact else 236)" in source
    assert "item.text.setVisible(not compact)" in source
    assert "item.icon_wrap" in source
    assert "Expandir barra lateral" in source
    assert "SidebarNavItem" in source


def test_v153_preserves_existing_dependencies_and_project_format():
    source = _read("src/monitor_noticias/ui/art_studio_v153.py")
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert ".centralart" in source
    assert "json.dump" not in source
