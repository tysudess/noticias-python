from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v156_installs_after_v155_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v155()") < source.index("install_art_studio_v156()")
    assert source.index("install_art_studio_v156()") < source.index("from monitor_noticias.app.application import main")


def test_v155_module_is_available_under_the_package_path_used_by_run():
    source = _read("run.py")
    assert "from monitor_noticias.ui.art_studio_v155 import install_art_studio_v155" in source
    assert (ROOT / "src/monitor_noticias/ui/art_studio_v155.py").is_file()


def test_v156_wraps_layer_panel_deletion_before_removal():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    delete = source.split("def _delete_from_layer_panel", 1)[1].split("def _wrap_v154_delete", 1)[0]
    assert "_capture_for_items(page, selected)" in delete
    assert "_v154._v156_original_delete_selected(page)" in delete
    assert "_record_deleted(page, snapshots, deletable)" in delete


def test_v156_captures_single_object_deletion_and_reconnects_delete_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    assert "def _delete_single_selected" in source
    assert "button.clicked.disconnect()" in source
    assert 'if action.text() == "Excluir objeto"' in source


def test_v156_cancels_deletion_when_a_safety_snapshot_cannot_be_created():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    capture = source.split("def _serialize_deletable", 1)[1].split("def _recycle_size", 1)[0]
    assert "raise RuntimeError" in capture
    selection = source.split("def _capture_for_items", 1)[1].split("def _record_deleted", 1)[0]
    assert "return [], []" in selection
    assert "nem todas as camadas puderam ser protegidas" in selection


def test_v156_restores_deleted_layers_with_original_serialized_data_and_identity():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    restore = source.split("def _restore_last_deleted", 1)[1].split("def _install_recycle_panel", 1)[0]
    assert "page._build_item_from_data(deepcopy(data))" in restore
    assert "item.setData(HISTORY_ID_KEY, identity)" in restore
    assert "page.scene.addItem(item)" in restore


def test_v156_recycle_bin_is_scoped_to_the_active_multipage_page():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    assert 'return _active_page_id(page) or "single-page-document"' in source
    assert 'batch.get("page_id") == _page_key(page)' in source


def test_v156_has_bounded_session_recycle_storage():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    assert "_MAX_RECYCLE_BATCHES = 12" in source
    assert "_MAX_RECYCLE_BYTES = 48 * 1024 * 1024" in source
    assert "while len(batches) > _MAX_RECYCLE_BATCHES or _recycle_size(batches) > _MAX_RECYCLE_BYTES" in source


def test_v156_adds_recycle_panel_and_restore_shortcut():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    assert "LIXEIRA TEMPORÁRIA" in source
    assert "Recuperar última exclusão" in source
    assert 'QKeySequence("Ctrl+Alt+Z")' in source


def test_v156_keeps_recovery_session_only_and_adds_no_external_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    assert "lixeira desta sessão" in source
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert "requests" not in source


def test_v156_restores_all_objects_as_a_batch_and_rolls_back_partial_failure():
    source = _read("src/monitor_noticias/ui/art_studio_v156.py")
    restore = source.split("def _restore_last_deleted", 1)[1].split("def _install_recycle_panel", 1)[0]
    assert "for data in batch.get(\"items\", [])" in restore
    assert "built.append(item)" in restore
    assert "for item in built:" in restore
    assert "for item in restored:" in restore


def test_misplaced_root_v155_test_keeps_repository_root_resolution():
    source = _read("test_art_studio_v155.py")
    assert "ROOT = Path(__file__).resolve().parent" in source
