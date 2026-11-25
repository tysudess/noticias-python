from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v154_installs_after_v153_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v153()") < source.index("install_art_studio_v154()")
    assert source.index("install_art_studio_v154()") < source.index("from monitor_noticias.app.application import main")


def test_v154_enables_extended_selection_in_layer_panel():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    assert "QAbstractItemView.SelectionMode.ExtendedSelection" in source
    assert "itemSelectionChanged.connect" in source
    assert "_sync_scene_from_layer_list" in source


def test_v154_keeps_scene_and_layer_selection_synchronized():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    assert "_sync_layer_list_from_scene" in source
    assert "page.scene.clearSelection()" in source
    assert "item.setSelected(True)" in source
    assert "_v154_syncing" in source


def test_v154_adds_layer_name_filter_and_direct_rename():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    assert "Filtrar camadas pelo nome" in source
    assert "textChanged.connect" in source
    assert "QInputDialog.getText" in source
    assert '"F2"' in source


def test_v154_adds_layer_context_menu_and_batch_actions():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    for action in ("Mostrar / ocultar", "Bloquear / desbloquear", "Duplicar seleção", "Agrupar seleção", "Excluir seleção"):
        assert action in source
    assert "_toggle_visibility_selected" in source
    assert "_toggle_lock_selected" in source
    assert "_delete_selected" in source


def test_v154_preserves_locked_layers_when_bulk_deleting():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    delete = source.split("def _delete_selected", 1)[1].split("def _schedule_history", 1)[0]
    assert "not bool(item.data(LOCKED_KEY))" in delete
    assert "bloqueada(s) preservada(s)" in delete


def test_v154_preserves_layer_selection_when_refreshing_layer_rows():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    assert "def _refresh_layers_with_multiselection" in source
    assert "_restore_layer_rows" in source
    assert "blockSignals(True)" in source


def test_v154_does_not_change_legacy_project_format_or_add_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v154.py")
    assert "PROJECT_VERSION" not in source
    assert "PROJECT_FORMAT" not in source
    assert "PySide6" in source
    assert "PIL" not in source
    assert "json.dump" not in source
