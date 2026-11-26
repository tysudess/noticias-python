from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v163_after_v162_and_before_application_main():
    source = _read("run.py")
    v162 = source.index("install_art_studio_v162()")
    v163 = source.index("install_art_studio_v163()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v162 < v163 < main


def test_component_library_contains_thirteen_professional_templates():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "TEMPLATES: tuple[_Template, ...]" in source
    assert "QLabel(\"13 componentes disponíveis\", panel)" in source
    for key in (
        '"lower-third"', '"info-card"', '"quote-card"', '"stat-card"',
        '"urgent-alert"', '"agenda-card"', '"comparison"', '"cta-button"',
        '"official-seal"', '"source-line"', '"report-cover"', '"three-points"',
        '"section-banner"',
    ):
        assert key in source


def test_templates_use_only_item_types_already_supported_by_group_serializer():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert '_Element("rect"' in source
    assert '_Element("ellipse"' in source
    assert '_Element("text"' in source
    assert 'QGraphicsRectItem(' in source
    assert 'QGraphicsEllipseItem(' in source
    assert 'InlineTextItem(element.value)' in source
    assert "QGraphicsPixmapItem" not in source
    assert "QGraphicsPolygonItem" not in source
    assert "QGraphicsLineItem" not in source


def test_every_template_element_uses_a_palette_role_and_valid_geometry():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert '"primary":' in source
    assert '"accent":' in source
    assert '"surface":' in source
    assert "palette[element.color]" in source
    assert "element.width" in source
    assert "element.height" in source


def test_library_supports_search_and_category_filtering():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert 'QLineEdit(panel)' in source
    assert 'setPlaceholderText("⌕  Buscar componente…")' in source
    assert 'addItem("Todas as categorias", "all")' in source
    assert "matches_query" in source
    assert "matches_category" in source
    assert "_refresh_template_cards(page)" in source


def test_four_color_palettes_are_available_for_new_components():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    for key in ("institucional", "oceano", "urgente", "neutro"):
        assert f'"{key}": {{' in source
    assert "page.v163_palette_combo.currentData()" in source
    assert "_restyle_template_cards(page)" in source


def test_template_creation_groups_native_objects_and_sets_layer_metadata():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "page.scene.createItemGroup(children)" in source
    assert 'group.setData(ITEM_KIND_KEY, "group")' in source
    assert "group.setData(ITEM_NAME_KEY, template.title)" in source
    assert "page._make_movable(group, \"group\", template.title)" in source


def test_template_insertion_uses_transactional_insert_history_and_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "page._make_movable(group, \"group\", template.title)" in source
    assert "_schedule_autosave(page)" in source
    assert "_v148_sync_handles" in source
    assert "As camadas existentes" in source or "camadas" in source.casefold()


def test_component_limit_is_respected_before_creating_a_group():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "MAX_ITEMS_PER_PAGE" in source
    assert "current_count >= MAX_ITEMS_PER_PAGE" in source
    assert "page._content_items()" in source


def test_template_components_remain_grouped_but_can_be_ungrouped_for_editing():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert 'group.setData(ITEM_KIND_KEY, "group")' in source
    assert "Desagrupe para editar textos e formas separadamente" in source
    assert "v146_ungroup_button" not in source


def test_library_is_added_to_existing_elements_tab_without_replacing_existing_tools():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert 'tabs = getattr(page, "_v161_left_tabs", None)' in source
    assert "insert_page = tabs.widget(0)" in source
    assert "layout.insertWidget(insert_at, panel)" in source
    assert "add_image_button" not in source
    assert "page.scene =" not in source


def test_project_format_and_existing_serializers_are_not_modified():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert ".centralart" in source
    assert "PROJECT_FORMAT" not in source
    assert "_serialize_item" not in source
    assert "_build_item_from_data" not in source


def test_installer_is_idempotent_and_runs_once_after_existing_editor_setup():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "_v163_installed" in source
    assert "_v163_library_installed" in source
    assert "_v163_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source


def test_component_card_tooltips_describe_dimensions_and_editing_workflow():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "template.description" in source
    assert "template.width" in source
    assert "template.height" in source
    assert "Insira e desagrupe para personalizar cada parte" in source


def test_failed_group_creation_cleans_up_partial_scene_items():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "except Exception:" in source
    assert "if item.scene() is page.scene:" in source
    assert "page.scene.removeItem(item)" in source


def test_library_panel_is_inserted_before_existing_layout_stretch():
    source = _read("src/monitor_noticias/ui/art_studio_v163.py")
    assert "insert_at = max(0, layout.count() - 1)" in source
    assert "layout.insertWidget(insert_at, panel)" in source
