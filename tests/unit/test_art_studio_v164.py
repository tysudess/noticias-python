from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v163_then_v164_before_application_main():
    source = _read("run.py")
    v163 = source.index("install_art_studio_v163()")
    v164 = source.index("install_art_studio_v164()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v163 < v164 < main


def test_image_lab_is_added_as_a_dedicated_inspector_tab():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert 'tabs.addTab(image_page, "Imagem")' in source
    assert 'image_page.setObjectName("artStudioImageToolsPageV164")' in source
    for token in (
        "FILTRO FOTOGRÁFICO", "AJUSTES FINOS", "ENQUADRAMENTO E MÁSCARA",
        "BORDA DA IMAGEM", "Aplicar ajustes", "Restaurar original",
    ):
        assert token in source


def test_image_edit_pipeline_supports_filters_crop_masks_and_borders():
    source = _read("src/monitor_noticias/ui/art_studio_image_engine_v164.py")
    for token in (
        '"vivid"', '"mono"', '"sepia"', '"cool"', '"warm"', '"cinematic"',
        '"1:1"', '"4:5"', '"16:9"', '"3:2"', '"9:16"',
        '"rounded"', '"circle"', '"hexagon"', '"arch"',
        "ImageEnhance.Brightness", "ImageEnhance.Contrast", "ImageEnhance.Color",
        "ImageEnhance.Sharpness", "GaussianBlur", "_add_border",
    ):
        assert token in source


def test_original_image_and_edit_configuration_are_persisted_in_existing_item_data():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "ORIGINAL_IMAGE_DATA_KEY = 164" in source
    assert "IMAGE_EDIT_CONFIG_DATA_KEY = 165" in source
    assert 'data["v164_image_source_png_base64"] = str(original)' in source
    assert 'data["v164_image_edit_config"] = config' in source
    assert "page._v146_base_serialize = serialize_with_image_edits" in source
    assert "page._v146_base_build = build_with_image_edits" in source


def test_group_child_images_are_covered_by_wrapping_v146_base_serializers():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert 'getattr(page, "_v146_base_serialize", None)' in source
    assert 'getattr(page, "_v146_base_build", None)' in source
    assert "page._v146_base_serialize = serialize_with_image_edits" in source
    assert "page._v146_base_build = build_with_image_edits" in source
    assert "isinstance(item, QGraphicsPixmapItem)" in source


def test_edits_are_reversible_and_registered_in_history_and_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "item.setData(ORIGINAL_IMAGE_DATA_KEY, source_b64)" in source
    assert "item.setData(ORIGINAL_IMAGE_DATA_KEY, None)" in source
    assert "timer.start()" in source
    assert "_schedule_autosave(page)" in source
    assert "item.setPixmap(pixmap)" in source


def test_image_tools_reject_multiple_hidden_or_locked_non_image_selections():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "len(selected) != 1" in source
    assert "not isinstance(selected[0], QGraphicsPixmapItem)" in source
    assert "not item.isVisible()" in source
    assert "item.data(LOCKED_KEY)" in source


def test_large_images_are_limited_and_invalid_edit_metadata_does_not_break_project_open():
    engine = _read("src/monitor_noticias/ui/art_studio_image_engine_v164.py")
    ui = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "MAX_IMAGE_SOURCE_BYTES = 20 * 1024 * 1024" in engine
    assert "MAX_IMAGE_PIXELS = 25_000_000" in engine
    assert 'log.warning("Não foi possível reaplicar os ajustes V164' in ui


def test_installer_is_idempotent_and_runs_after_component_library():
    source = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "_v164_image_serialization_installed" in source
    assert "_v164_image_panel_installed" in source
    assert "_v164_installed" in source
    assert "_v164_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source


def test_image_engine_config_clamps_values_and_uses_known_enum_values():
    from monitor_noticias.ui.art_studio_image_engine_v164 import normalize_image_edit_config

    config = normalize_image_edit_config({
        "preset": "not-a-filter", "brightness": 99, "contrast": -99,
        "saturation": 5, "sharpness": -1, "blur": 500,
        "crop": "custom", "mask": "unknown", "border_width": 999,
        "border_color": "red",
    })
    assert config["preset"] == "original"
    assert config["brightness"] == 2.5
    assert config["contrast"] == 0.0
    assert config["saturation"] == 3.0
    assert config["sharpness"] == 0.0
    assert config["blur"] == 15.0
    assert config["crop"] == "original"
    assert config["mask"] == "none"
    assert config["border_width"] == 32
    assert config["border_color"] == "#FFFFFF"
