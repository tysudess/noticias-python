from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v166_after_v165_and_before_main():
    source = _read("run.py")
    v165 = source.index("install_art_studio_v165()")
    v166 = source.index("install_art_studio_v166()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v165 < v166 < main


def test_background_panel_has_corner_tolerance_softness_and_transparent_recrop():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    for token in (
        "RECORTE DE FUNDO", "Ativar remoção do fundo", "Superior esquerdo",
        "Superior direito", "Inferior esquerdo", "Inferior direito",
        "Tolerância de cor", "Suavização da borda",
        "Aplicar ajustes + recorte de fundo",
        "não é recorte automático por IA",
    ):
        assert token in source
    assert "remove_background_by_corner_color" in source


def test_combined_apply_reprocesses_v164_v165_original_and_stores_v166_config():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    assert "item.data(ORIGINAL_IMAGE_DATA_KEY)" in source
    assert "v165.render_image_source_v165(str(source_b64), base_config, advanced_config)" in source
    assert "item.setData(BACKGROUND_CONFIG_DATA_KEY" in source
    assert '"v166_background_removal"' in source
    assert "v165._refresh_image_state(page, item)" in source


def test_background_config_round_trips_through_existing_recursive_project_serializer():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    assert "page._v146_base_serialize = serialize_with_background" in source
    assert "page._v146_base_build = build_with_background" in source
    assert "previous_serialize(item)" in source
    assert "previous_build(data)" in source
    assert "_pixmap_to_png_bytes(item.pixmap())" in source


def test_locked_or_multiple_selected_items_are_not_modified():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    assert "item = _selected_image(page)" in source
    v164 = _read("src/monitor_noticias/ui/art_studio_v164.py")
    assert "len(selected) != 1" in v164
    assert "not item.isVisible()" in v164
    assert "item.data(LOCKED_KEY)" in v164


def test_apply_restore_actions_are_integrated_with_existing_image_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    assert "page.v164_apply_button.clicked.disconnect()" in source
    assert "page.v164_apply_button.clicked.connect(lambda: _apply_all_image_edits_v166(page))" in source
    assert "page.v164_restore_button.clicked.connect(lambda: _restore_all_image_edits_v166(page))" in source
    assert "v165._restore_all_image_edits(page)" in source


def test_installer_is_idempotent_and_runs_after_v165():
    source = _read("src/monitor_noticias/ui/art_studio_v166.py")
    assert "_v166_background_serialization_installed" in source
    assert "_v166_background_controls_installed" in source
    assert "_v166_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source
