from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_art_studio_installs_before_main_application_import():
    source = _read("run.py")
    install_at = source.index("install_art_studio()")
    app_import_at = source.index("from monitor_noticias.app.application import main")
    assert install_at < app_import_at


def test_art_studio_is_added_to_existing_tools_navigation_group():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    assert '"FERRAMENTAS"' in source
    assert '"ART_STUDIO"' in source
    assert '"Estúdio de Artes"' in source
    assert "MainWindow._build_sidebar = build_sidebar_with_art_studio" in source


def test_art_studio_supports_core_editor_features_and_local_projects():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    for token in (
        "def add_image(",
        "def add_text(",
        "def add_shape(",
        "def duplicate_selected(",
        "def bring_to_front(",
        "def send_to_back(",
        "def save_project(",
        "def open_project(",
        "def export_art(",
        '"image_png_base64"',
        '".centralart"',
        '"JPEG"',
        '"PNG"',
        '".pdf"',
    ):
        assert token in source


def test_art_studio_uses_no_new_third_party_runtime_packages():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    assert "from PIL import Image as PILImage" in source
    assert "import fabric" not in source.lower()
    assert "adobe" not in source.lower()


def test_art_studio_has_quick_templates_and_zoom_controls():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    for token in (
        "def apply_quick_template(",
        "Destaque de notícia",
        "Comunicado",
        "Convite",
        "Card informativo",
        "zoomChanged = Signal(int)",
        "def zoom_by(",
        "def actual_size(",
        "Ctrl+0",
    ):
        assert token in source


def test_art_studio_supports_object_transform_and_font_properties():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    for token in (
        "def apply_selected_transform(",
        "def center_selected(",
        "def change_selected_font(",
        "QDoubleSpinBox",
        "QFontDialog.getFont",
        '"opacity": float(item.opacity())',
        '"font_serialized": font.toString()',
        'item.setOpacity(max(0.1, min(1.0, float(data.get("opacity", 1.0)))))',
    ):
        assert token in source


def test_art_studio_canvas_dimensions_use_readable_vertical_fields():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    assert "left.setFixedWidth(184)" in source
    assert 'dimensions.addRow("Largura (px)", self.width_spin)' in source
    assert 'dimensions.addRow("Altura (px)", self.height_spin)' in source


def test_art_studio_v145_adds_crop_visibility_lock_and_alignment_tools():
    source = _read("src/monitor_noticias/ui/art_studio_v145.py")
    for token in (
        "def _crop_selected_image(",
        "class _ImageCropDialog",
        "def _toggle_visibility(",
        "def _toggle_lock(",
        "def _align_objects(",
        'data["visible"]',
        'data["locked"]',
        'data["history_id"]',
    ):
        assert token in source


def test_art_studio_v145_adds_undo_redo_with_debounced_scene_history():
    source = _read("src/monitor_noticias/ui/art_studio_v145.py")
    for token in (
        "QUndoStack",
        "QUndoCommand",
        "def _undo(",
        "def _redo(",
        "def _commit_history(",
        "page.scene.changed.connect",
        "QKeySequence.StandardKey.Undo",
        "QKeySequence.StandardKey.Redo",
    ):
        assert token in source


def test_art_studio_v145_is_installed_after_page_creation():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    assert "from monitor_noticias.ui.art_studio_v145 import enhance_art_studio_page" in source
    assert "enhance_art_studio_page(self.art_studio_page)" in source


def test_art_studio_v145_persists_layer_visibility_and_lock_state():
    source = _read("src/monitor_noticias/ui/art_studio_v145.py")
    assert 'data["visible"] = bool(item.isVisible())' in source
    assert 'data["locked"] = bool(item.data(LOCKED_KEY))' in source
    assert 'item.setVisible(bool(data.get("visible", True)))' in source
    assert 'item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)' in source


def test_art_studio_v145_crop_uses_pixel_bounds_and_keeps_transformed_position():
    source = _read("src/monitor_noticias/ui/art_studio_v145.py")
    assert "math.floor(rect.left())" in source
    assert "math.ceil(rect.right())" in source
    assert "item.mapToScene(QPointF(rect.left(), rect.top()))" in source
    assert "item.setPixmap(cropped)" in source


def test_art_studio_v145_blocks_mutations_of_locked_layers():
    source = _read("src/monitor_noticias/ui/art_studio_v145.py")
    assert "def _install_locked_item_guards(" in source
    assert "Desbloqueie a camada antes de excluí-la." in source
    assert "Desbloqueie ao menos uma camada para alinhá-la." in source
