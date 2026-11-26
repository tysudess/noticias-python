from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v169_after_v168_and_before_application_main():
    source = _read("run.py")
    v168 = source.index("install_art_studio_v168()")
    v169 = source.index("install_art_studio_v169()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v168 < v169 < main


def test_snap_uses_the_existing_selection_and_scene_delta_helpers():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "from monitor_noticias.ui.art_studio_v151 import _move_by_scene_delta, _movable_selection, _schedule_history" in source
    assert "moving, _skipped = _movable_selection(page)" in source
    assert "_move_by_scene_delta(item, dx, dy)" in source
    assert "_schedule_history(page)" in source


def test_snap_targets_exclude_selected_items_and_related_group_ancestors():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "if other in moving or not other.isVisible():" in source
    assert "self._related(other, item)" in source
    assert "first.isAncestorOf(second) or second.isAncestorOf(first)" in source


def test_guidelines_are_transparent_overlays_outside_scene_and_project_serialization():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "class _SnapGuidesOverlay(QWidget)" in source
    assert "WA_TransparentForMouseEvents" in source
    assert "WA_TranslucentBackground" in source
    assert "page.scene.addItem" not in source
    assert "_serialize_item" not in source


def test_user_can_toggle_snap_targets_guidelines_and_screen_threshold():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    for token in (
        "Ativar encaixe magnético", "Encaixar em outros objetos",
        "Encaixar nas bordas e no centro da página", "Encaixar na grade da aba Guias",
        "Encaixar nas guias de terços, centro e margens", "Mostrar guias inteligentes",
        "Sensibilidade do encaixe", "tabs.addTab(tab, \"⌖  Encaixe\")",
    ):
        assert token in source


def test_controller_uses_post_event_timer_for_graphics_view_drag_updates():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "QEvent.Type.MouseMove" in source
    assert "QEvent.Type.MouseButtonRelease" in source
    assert "self._timer.start(0)" in source
    assert "event.buttons() & Qt.MouseButton.LeftButton" in source


def test_text_editing_is_not_intercepted_by_magnetic_snap():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "def _is_text_being_edited" in source
    assert "focus.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction" in source
    assert "if self._is_text_being_edited(page):" in source


def test_snap_tab_installer_is_idempotent_and_config_is_normalized():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "_v169_snap_installed" in source
    assert "_v169_installed" in source
    assert "_v169_integration_installed" in source
    assert "normalize_snap_config" in source
    assert "controller.set_config(config)" in source


def test_snap_integrates_v168_grid_and_composition_guide_state():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "getattr(page, \"v168_guide_config\", {})" in source
    assert "composition_guide_positions" in source
    assert "guide_state.get(\"thirds_enabled\")" in source
    assert "guide_state.get(\"center_enabled\")" in source
    assert "guide_state.get(\"safe_area_enabled\")" in source
    assert "grid_combo.currentData()" in source
    assert "snap_to_grid=self.config[\"snap_to_grid\"]" in source


def test_grid_and_composition_snap_are_user_configurable():
    source = _read("src/monitor_noticias/ui/art_studio_v169.py")
    assert "page.v169_snap_grid = QCheckBox" in source
    assert "page.v169_snap_composition_guides = QCheckBox" in source
    assert "page.v169_snap_grid.isChecked()" in source
    assert "page.v169_snap_composition_guides.isChecked()" in source
