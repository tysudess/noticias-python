from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v150_installs_after_v149_and_before_application_startup():
    source = _read("run.py")
    v149 = source.index("install_art_studio_v149()")
    v150 = source.index("install_art_studio_v150()")
    app = source.index("from monitor_noticias.app.application import main")
    assert v149 < v150 < app


def test_v150_adds_multiple_pages_with_add_duplicate_rename_delete_and_reorder():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "MAX_PAGES = 30",
        "MAX_BACKGROUND_PIXELS = 25_000_000",
        "MAX_TOTAL_RENDER_PIXELS = 80_000_000",
        "def _add_page(",
        "def _duplicate_page(",
        "def _delete_page(",
        "def _rename_page(",
        "def _tab_moved(",
        "QTabBar",
        "setMovable(True)",
        "setTabsClosable(True)",
        "tabCloseRequested.connect",
    ):
        assert token in source


def test_v150_saves_and_opens_multipage_documents_and_keeps_legacy_projects():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        '"pages": deepcopy(page._v150_pages)',
        '"active_page_index": int(page._v150_active_index)',
        "def _validate_document(",
        "def _legacy_page_data(",
        "def _open_project(",
        "def _save_project(",
        "def _restore_page_data(",
    ):
        assert token in source


def test_v150_adds_solid_gradient_and_embedded_image_backgrounds():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        '"mode": "solid"',
        '"mode": "gradient"',
        '"mode": "image"',
        "QLinearGradient",
        "def _choose_gradient_background(",
        "def _choose_background_image(",
        '"image_png_base64"',
        "def _apply_background(",
    ):
        assert token in source


def test_v150_adds_reusable_element_library_without_new_object_types():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "BIBLIOTECA DE ELEMENTOS",
        "Etiqueta",
        "Faixa de título",
        "Selo",
        "Botão",
        "Chamada",
        "Número",
        "scene.createItemGroup",
        "def _install_group_identity_persistence(",
        "data[\"history_id\"] = str(identity)",
        'background.setData(ITEM_KIND_KEY, "shape")',
        'text_item.setData(ITEM_KIND_KEY, "text")',
    ):
        assert token in source


def test_v150_adds_smart_guides_and_grid_that_are_hidden_from_export():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "Guias inteligentes",
        "def _snap_dragged_item(",
        "def _snap_axis(",
        "def _set_grid(",
        "def render_without_guides(",
        "page._v150_original_render_art()",
    ):
        assert token in source


def test_v150_adds_advanced_letter_and_line_spacing_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "TIPOGRAFIA AVANÇADA",
        "v150_letter_spacing",
        "v150_line_spacing",
        "setFontLetterSpacing",
        "LineHeightTypes.ProportionalHeight",
    ):
        assert token in source


def test_v150_exports_all_pages_to_pdf_with_memory_guard():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    assert "def _export_all_pages_pdf(" in source
    assert "save_all=True" in source
    assert "append_images=rendered[1:]" in source
    assert "MAX_TOTAL_RENDER_PIXELS" in source


def test_v150_uses_existing_runtime_dependencies_only():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    assert "from PySide6" in source
    assert "from PIL import Image as PILImage" in source
    assert "import fabric" not in source.lower()
    assert "import cv2" not in source.lower()


def test_v150_imports_palette_for_light_and_dark_pages_toolbar():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    gui_imports = source.split("from PySide6.QtGui import (", 1)[1].split(")", 1)[0]
    widget_imports = source.split("from PySide6.QtWidgets import (", 1)[1].split(")", 1)[0]
    assert "QPalette," in gui_imports
    assert "QPalette," not in widget_imports
    assert "page.palette().color(QPalette.ColorRole.Window)" in source


def test_v150_preserves_background_in_project_and_undo_redo_snapshots():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "def _install_history_snapshot_compatibility(",
        "page._project_data = project_data_with_background",
        'data["v150_background"] = deepcopy(',
        "page._v145_restore_snapshot = restore_history_snapshot",
        "_restore_page_data(page, project, fit=True, reset_history=False)",
        '"v150_background": deepcopy(active.get("v150_background", {}))',
    ):
        assert token in source


def test_v150_user_facing_resource_limits_match_enforced_constants():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    assert "excede 25 milhões de pixels." in source
    assert "deve ter até 25 milhões de pixels." in source
    assert "80 milhões de pixels. Exporte menos páginas por vez." in source



def test_v150_keeps_independent_undo_stacks_for_each_page():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    for token in (
        "def _bind_history_stack(",
        "def _activate_page_history(",
        "page._v150_page_histories",
        "_flush_active_history(page)",
        "reset_history=False",
        "page._v145_history = stack",
    ):
        assert token in source


def test_v150_page_ids_survive_save_and_reorder_and_are_recreated_for_duplicates():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    assert '"id": uuid.uuid4().hex' in source
    assert 'clone["id"] = uuid.uuid4().hex' in source
    assert '"id": page_id' in source
    assert '"pages": deepcopy(page._v150_pages)' in source


def test_v150_restores_history_baseline_after_multipage_pdf_export():
    source = _read("src/monitor_noticias/ui/art_studio_v150.py")
    assert "active_selection = [" in source
    assert "page._v145_last_snapshot = _v145_snapshot(page)" in source
    assert "page._v145_active_item = selected_item" in source
