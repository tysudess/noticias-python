from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v161_after_v160_before_application_main():
    source = _read("run.py")
    v160 = source.index("install_art_studio_v160()")
    v161 = source.index("install_art_studio_v161()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v160 < v161 < main


def test_left_workspace_is_split_into_elements_and_page_tabs():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert 'QTabWidget(content)' in source
    assert 'tabs.setObjectName("artStudioElementsTabs")' in source
    assert 'tabs.addTab(insert_page, "＋  Elementos")' in source
    assert 'tabs.addTab(page_page, "▧  Página")' in source
    for name in ("add_image_button", "add_text_button", "preset_combo", "v150_gradient_bg_button"):
        assert f'getattr(page, "{name}"' in source


def test_right_inspector_has_four_professional_work_areas():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert 'tabs.setObjectName("artStudioInspectorTabs")' in source
    for name in ("Camadas", "Design", "Composição", "Proteção"):
        assert name in source
    for panel in (
        "artStudioObjectSizePanel",
        "artStudioPositionPanel",
        "artStudioCompositionPanelV151",
        "artStudioIntegrityPanelV155",
        "artStudioRecyclePanelV156",
    ):
        assert panel in source


def test_existing_widgets_and_layouts_are_moved_not_recreated():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "source.takeAt(0)" in source
    assert "targets[category].addWidget(widget)" in source
    assert "targets[category].addLayout(child_layout)" in source
    assert "source.addWidget(tabs)" in source


def test_layer_actions_stay_in_layers_tab_and_object_controls_stay_in_design():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "layer_action_targets" in source
    assert "property_targets" in source
    assert 'return "layers"' in source
    assert 'return "design"' in source


def test_visual_system_has_distinct_light_and_dark_palettes():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert 'if dark:' in source
    assert 'window = "#0B1724"' in source
    assert 'window = "#EEF3F7"' in source
    assert 'QFrame#artStudioWorkspace' in source
    assert 'QFrame#artStudioToolbar' in source
    assert 'QFrame#artStudioPanel' in source


def test_theme_switch_refreshes_the_editor_without_rebuilding_the_scene():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "QEvent.Type.PaletteChange" in source
    assert "QEvent.Type.ApplicationPaletteChange" in source
    assert "_apply_skin(page)" in source
    assert "page.scene" not in source
    assert "_serialize_item" not in source


def test_editor_canvas_and_project_storage_are_not_replaced():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "page.view.setStyleSheet" in source
    assert "page.view" in source
    assert "page._width" not in source
    assert "page._height" not in source
    assert ".centralart" in source


def test_header_and_element_buttons_receive_clearer_hierarchy():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "ESTÚDIO DE ARTES" in source
    assert "DESIGN • COMPOSIÇÃO • CRIAÇÃO" in source
    assert "_polish_element_actions(page)" in source
    assert "QLabel#artStudioBrandTitle" in source


def test_installation_is_idempotent_and_only_wraps_main_window_once():
    source = _read("src/monitor_noticias/ui/art_studio_v161.py")
    assert "_v161_installed" in source
    assert "_v161_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source
