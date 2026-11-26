from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v162_after_v161_before_application_main():
    source = _read("run.py")
    v161 = source.index("install_art_studio_v161()")
    v162 = source.index("install_art_studio_v162()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v161 < v162 < main


def test_workspace_is_rebuilt_as_a_three_panel_qsplitter():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "QSplitter(Qt.Orientation.Horizontal, page)" in source
    assert 'splitter.setObjectName("artStudioWorkspaceSplitterV162")' in source
    assert "for widget in (left, center, right):" in source
    assert "workspace_layout.addWidget(splitter)" in source


def test_splitter_panels_are_resizable_and_canvas_keeps_a_safe_minimum():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "left.setMinimumWidth(180)" in source
    assert "left.setMaximumWidth(350)" in source
    assert "right.setMinimumWidth(265)" in source
    assert "right.setMaximumWidth(445)" in source
    assert "center.setMinimumWidth(430)" in source
    assert "splitter.setChildrenCollapsible(False)" in source
    assert "_SplitterInitialSizeFilter" in source
    assert "QEvent.Type.Show" in source


def test_focus_mode_hides_panels_and_restores_previous_split_sizes():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "page._v162_saved_split_sizes = current_sizes" in source
    assert "left.hide()" in source
    assert "right.hide()" in source
    assert "left.show()" in source
    assert "right.show()" in source
    assert "splitter.setSizes(value)" in source


def test_focus_mode_has_toolbar_button_and_keyboard_shortcut():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert 'button.setObjectName("artStudioFocusButtonV162")' in source
    assert 'action.setShortcut("Ctrl+Shift+F")' in source
    assert "button.toggled.connect" in source


def test_selection_inspector_reports_type_name_dimensions_and_position():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    for token in (
        '"text": "TEXTO"',
        '"image": "IMAGEM"',
        '"shape": "FORMA"',
        '"group": "GRUPO"',
        "ITEM_NAME_KEY",
        "sceneBoundingRect()",
        '"{bounds.width():.0f} × {bounds.height():.0f} px"',
        '"   ·   X {bounds.x():.0f}"',
        '"   ·   Y {bounds.y():.0f}"',
    ):
        assert token in source


def test_selection_summary_updates_on_selection_and_scene_changes_with_debounce():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "timer.setSingleShot(True)" in source
    assert "timer.setInterval(90)" in source
    assert "page.scene.selectionChanged.connect(timer.start)" in source
    assert "page.scene.changed.connect(lambda *_args: timer.start())" in source


def test_selection_summary_is_inserted_into_design_inspector_tab():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert 'tabs.widget(1)' in source
    assert 'card.setObjectName("artStudioSelectionCardV162")' in source
    assert "layout.insertWidget(2, card)" in source


def test_v162_does_not_replace_canvas_scene_serialization_or_project_format():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "page.scene =" not in source
    assert "_serialize_item" not in source
    assert "_build_item_from_data" not in source
    assert "PROJECT_FORMAT" not in source


def test_installer_and_workspace_installation_are_idempotent():
    source = _read("src/monitor_noticias/ui/art_studio_v162.py")
    assert "_v162_integration_installed" in source
    assert "_v162_installed" in source
    assert "_v162_splitter_installed" in source
    assert "original_init(self, *args, **kwargs)" in source
