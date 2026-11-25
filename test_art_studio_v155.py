from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v155_installs_after_v154_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v154()") < source.index("install_art_studio_v155()")
    assert source.index("install_art_studio_v155()") < source.index("from monitor_noticias.app.application import main")


def test_v155_replaces_legacy_creation_wrappers_with_base_transaction():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "ArtStudioPage._make_movable(page, item, kind, name)" in source
    assert "page._make_movable = lambda item, kind, name" in source
    assert "_transactional_make_movable" in source


def test_v155_serializes_every_existing_top_level_layer_before_insertion():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "def _capture_scene" in source
    assert "deepcopy(page._serialize_item(item))" in source
    assert "data[\"history_id\"] = identity" in source
    assert "CANVAS_BG_KEY" in source


def test_v155_restores_missing_layers_by_rebuilding_from_serialized_data():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    restore = source.split("def _restore_missing", 1)[1].split("def _move_scene_delta", 1)[0]
    assert "page._build_item_from_data(deepcopy(data))" in restore
    assert "page.scene.addItem(item)" in restore
    assert "present[identity] = item" in restore


def test_v155_cancels_new_insertion_if_previous_layers_cannot_be_recovered():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    transaction = source.split("def _transactional_make_movable", 1)[1].split("def _recovery_candidates", 1)[0]
    assert "missing = previous_ids - current_ids" in transaction
    assert "A nova inserção foi cancelada" in transaction
    assert "page.scene.removeItem(item)" in transaction


def test_v155_uses_dense_free_area_search_and_keeps_existing_objects_above_on_collision():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "range(17)" in source
    assert "overlap_area * 100_000.0" in source
    assert "lower_z - 0.01" in source
    assert "_place_new_object(page, item, previous_ids)" in source


def test_v155_adds_manual_recovery_for_previous_insertion_snapshot():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "_v155_last_safe_snapshot" in source
    assert "def _recover_previous_layers" in source
    assert "Verificar / recuperar camadas" in source
    assert "QMessageBox.StandardButton.Yes" in source


def test_v155_limits_recovery_to_the_same_multipage_document_page():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "def _active_page_id" in source
    assert "_v155_recovery_page_id" in source
    assert "!= _active_page_id(page)" in source


def test_v155_keeps_existing_project_format_and_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert ".centralart" not in source or "Não altera o formato .centralart" in source
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert "json.dump" not in source
