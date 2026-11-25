from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v155_installs_after_v154_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v154()") < source.index("install_art_studio_v155()")
    assert source.index("install_art_studio_v155()") < source.index("from monitor_noticias.app.application import main")


def test_v155_module_is_stored_under_the_importable_package_path():
    assert (ROOT / "src/monitor_noticias/ui/art_studio_v155.py").is_file()


def test_v155_replaces_legacy_creation_wrappers_with_base_transaction():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "ArtStudioPage._make_movable(page, item, kind, name)" in source
    assert "page._make_movable = lambda item, kind, name" in source
    assert "_transactional_make_movable" in source


def test_v155_serializes_existing_layers_and_restores_missing_layers():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "def _capture_scene" in source
    assert "deepcopy(page._serialize_item(item))" in source
    assert 'data["history_id"] = identity' in source
    assert "def _restore_missing" in source
    assert "page._build_item_from_data(deepcopy(data))" in source


def test_v155_cancels_new_insertion_if_previous_layers_cannot_be_recovered():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    transaction = source.split("def _transactional_make_movable", 1)[1].split("def _recovery_candidates", 1)[0]
    assert "missing = previous_ids - current_ids" in transaction
    assert "A nova inserção foi cancelada" in transaction
    assert "page.scene.removeItem(item)" in transaction


def test_v155_adds_manual_recovery_for_the_previous_insertion_snapshot():
    source = _read("src/monitor_noticias/ui/art_studio_v155.py")
    assert "def _recover_previous_layers" in source
    assert "Verificar / recuperar camadas" in source
    assert "QMessageBox.StandardButton.Yes" in source
