from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v148_is_installed_after_existing_art_studio_integration():
    source = _read("run.py")
    assert source.index("install_art_studio()") < source.index("install_art_studio_v148()")
    assert source.index("install_art_studio_v148()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_v148_preserves_existing_objects_when_adding_new_content():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    assert "def _capture_existing_objects(" in source
    assert "def _restore_missing_objects(" in source
    assert "def add_without_replacing_existing(" in source
    assert "original_make_movable(item, kind, name)" in source
    assert "_restore_missing_objects(page, before)" in source


def test_v148_provides_drag_handles_for_images_and_text_boxes():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    assert "class _ResizeHandle(QGraphicsRectItem)" in source
    assert "isinstance(target, QGraphicsTextItem)" in source
    assert "isinstance(target, QGraphicsPixmapItem)" in source
    assert "target.setTextWidth(new_width)" in source
    assert "target.setScale(self._start_scale * factor)" in source


def test_v148_adds_precise_image_and_text_dimensions_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    for token in (
        "AJUSTE DE TAMANHO",
        "Manter proporção da imagem",
        "def _apply_dimensions(",
        "def _flip_image(",
        "Espelhar ↔",
        "Espelhar ↕",
        "v148_text_width_spin",
    ):
        assert token in source


def test_v148_persists_free_image_transform_in_project_file():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    assert 'data["v148_transform"]' in source
    assert 'data["v148_transform_origin"]' in source
    assert "item.setTransform(QTransform(*(float(value) for value in values)))" in source


def test_v148_does_not_clear_scene_when_adding_objects():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    add = source.split("def add_without_replacing_existing", 1)[1].split("page._make_movable =", 1)[0]
    assert "scene.clear(" not in add
    assert "original_make_movable(item, kind, name)" in add


def test_v148_uses_existing_runtime_dependencies_only():
    source = _read("src/monitor_noticias/ui/art_studio_v148.py")
    assert "from PySide6" in source
    assert "import PIL" not in source
    assert "import fabric" not in source.lower()
