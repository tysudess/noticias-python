from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v157_installs_after_v156_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v156()") < source.index("install_art_studio_v157()")
    assert source.index("install_art_studio_v157()") < source.index("from monitor_noticias.app.application import main")


def test_v157_uses_a_separate_recovery_file_without_changing_centralart_format():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert '".recovery" / "autosave.json"' in source
    assert '"schema": _RECOVERY_SCHEMA' in source
    assert "_v150._document_payload(page)" in source


def test_v157_writes_recovery_atomically():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "tempfile.mkstemp" in source
    assert "os.fsync" in source
    assert "os.replace" in source


def test_v157_debounces_autosave_and_observes_scene_and_history_changes():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "_AUTOSAVE_DELAY_MS = 2200" in source
    assert "page.scene.changed.connect" in source
    assert "history_timer.timeout.connect" in source
    assert "stack.indexChanged.connect" in source


def test_v157_limits_backup_size_and_age():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "_MAX_AUTOSAVE_BYTES = 160 * 1024 * 1024" in source
    assert "_RECOVERY_MAX_AGE_DAYS = 14" in source
    assert "stat.st_size > _MAX_AUTOSAVE_BYTES" in source


def test_v157_validates_recovery_before_replacing_the_open_session():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    recover = source.split("def _apply_recovered_project", 1)[1].split("def _recover_session", 1)[0]
    assert "_v150._validate_document(page, project)" in recover
    assert "current_payload = _v150._document_payload(page)" in recover
    assert "Falha ao restaurar também a sessão anterior" in recover


def test_v157_requires_explicit_user_confirmation_before_recovery():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "QMessageBox.question" in source
    assert "QMessageBox.StandardButton.No" in source
    assert "A sessão aberta será substituída" in source


def test_v157_clears_backup_after_successful_save_or_switch_to_another_document():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "project_changed.connect" in source
    assert "_clear_recovery(page)" in source
    assert "v150_module._new_project = new_project_with_recovery_cleanup" in source
    assert "v150_module._open_project = open_project_with_recovery_cleanup" in source


def test_v157_keeps_recovery_local_to_the_portable_art_studio_projects_directory():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "Path(page.projects_dir)" in source
    assert "import tempfile" in source
    assert "urllib" not in source
    assert "requests" not in source


def test_v157_cleans_recovery_when_a_different_document_is_opened_or_created():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "v150_module._new_project = new_project_with_recovery_cleanup" in source
    assert "v150_module._open_project = open_project_with_recovery_cleanup" in source
    assert "_page_signature(page) != before" in source


def test_v157_does_not_parse_large_backup_files_just_to_enable_the_toolbar_button():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    button_update = source.split("def _update_recovery_button", 1)[1].split("def _clear_recovery", 1)[0]
    assert "path.stat()" in button_update
    assert "_read_recovery(page)" not in button_update


def test_v157_marks_page_and_layer_structure_edits_as_dirty_for_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "page._v157_document_dirty = True" in source
    assert '"v150_add_page_button"' in source
    assert '"v150_duplicate_page_button"' in source
    assert "tab_bar.tabMoved.connect" in source
    assert "tab_bar.tabCloseRequested.connect" in source


def test_v157_clears_dirty_state_after_manual_save_or_document_replacement():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    clear = source.split("def _clear_recovery", 1)[1].split("def _apply_recovered_project", 1)[0]
    assert "page._v157_document_dirty = False" in clear


def test_v157_preserves_existing_versions_and_adds_no_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v157.py")
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert "install_art_studio_v156" not in source
