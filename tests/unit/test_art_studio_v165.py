from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v165_after_v164_before_application_main():
    source = _read("run.py")
    v164 = source.index("install_art_studio_v164()")
    v165 = source.index("install_art_studio_v165()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v164 < v165 < main


def test_advanced_controls_are_added_to_existing_image_lab():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert 'findChild(QScrollArea, "artStudioImageToolsScrollV164")' in source
    assert 'panel.setObjectName("artStudioImageAdvancedCardV165")' in source
    for token in (
        "Temperatura · frio / quente", "Matiz · verde / magenta", "Realces",
        "Sombras", "Vinheta", "Desbotamento", "Zoom do corte",
        "Ponto focal horizontal", "Ponto focal vertical", "90° direita",
        "Espelhar horizontal", "Espelhar vertical",
    ):
        assert token in source


def test_existing_apply_and_restore_buttons_are_upgraded_without_duplicate_processing():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "page.v164_apply_button.clicked.disconnect()" in source
    assert "page.v164_apply_button.clicked.connect(lambda: _apply_all_image_edits(page))" in source
    assert "page.v164_restore_button.clicked.disconnect()" in source
    assert "page.v164_restore_button.clicked.connect(lambda: _restore_all_image_edits(page))" in source
    assert "render_image_source_v165(str(source_b64), base_config, advanced_config)" in source


def test_image_source_and_both_config_layers_are_persisted_in_same_item_data():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "ADVANCED_IMAGE_CONFIG_DATA_KEY = 166" in source
    assert 'data["v165_image_advanced_config"] = config' in source
    assert 'data.get("v164_image_source_png_base64")' in source
    assert 'data.get("v164_image_edit_config")' in source
    assert 'data.get("v165_image_advanced_config")' in source
    assert "page._v146_base_serialize = serialize_with_advanced_image" in source
    assert "page._v146_base_build = build_with_advanced_image" in source


def test_image_finish_is_non_destructive_and_uses_v164_original_source():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "item.data(ORIGINAL_IMAGE_DATA_KEY)" in source
    assert "encode_image_source(_pixmap_to_png_bytes(item.pixmap()))" in source
    assert "item.setData(ORIGINAL_IMAGE_DATA_KEY, str(source_b64))" in source
    assert "item.setData(ADVANCED_IMAGE_CONFIG_DATA_KEY" in source
    assert "_restore_original_image(page)" in source


def test_apply_tracks_history_autosave_and_layer_refresh():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "_v145_history_timer" in source
    assert "_schedule_autosave(page)" in source
    assert "page._refresh_layers(select_item=item)" in source
    assert "page.scene.update()" in source


def test_advanced_controls_only_apply_to_one_visible_unlocked_image():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "item = _selected_image(page)" in source
    assert "_selected_image(page)" in source
    # The shared V164 selector enforces type, visibility, scene ownership and lock state.
    v164 = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "len(selected) != 1" in v164
    assert "not item.isVisible()" in v164
    assert "item.data(LOCKED_KEY)" in v164


def test_restore_clears_advanced_metadata_and_resets_all_added_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "item.setData(ADVANCED_IMAGE_CONFIG_DATA_KEY, None)" in source
    assert "DEFAULT_ADVANCED_IMAGE_CONFIG.items()" in source
    assert "_restore_original_image(page)" in source


def test_serialization_extension_is_idempotent_and_keeps_v164_build_fallback():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "_v165_image_serialization_installed" in source
    assert "previous_serialize(item)" in source
    assert "previous_build(data)" in source
    assert "page._v165_previous_base_build = previous_build" in source
    assert "log.warning(\"Não foi possível reaplicar o acabamento V165" in source


def test_installer_is_idempotent_and_runs_after_v164():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    assert "_v165_advanced_controls_installed" in source
    assert "_v165_installed" in source
    assert "_v165_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source


def test_four_quick_finish_presets_are_available_and_load_values_without_applying():
    source = _read("src/monitor_noticias/ui/art_studio_v165.py")
    for key in ("natural", "portrait", "editorial", "night"):
        assert f'"{key}": {{' in source
    assert 'page.v165_apply_preset_button = QPushButton("Carregar estilo", panel)' in source
    assert "_apply_finish_preset_to_controls(page)" in source
    assert "Confira os valores e clique em Aplicar todos os ajustes" in source
    assert "render_image_source_v165" not in source[source.index("def _apply_finish_preset_to_controls"):source.index("def _read_advanced_config")]
