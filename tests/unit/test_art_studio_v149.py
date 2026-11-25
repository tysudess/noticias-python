from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v149_is_installed_after_v148_and_before_application_startup():
    source = _read("run.py")
    v148 = source.index("install_art_studio_v148()")
    v149 = source.index("install_art_studio_v149()")
    app = source.index("from monitor_noticias.app.application import main")
    assert v148 < v149 < app


def test_v149_adds_position_inspector_for_selected_objects():
    source = _read("src/monitor_noticias/ui/art_studio_v149.py")
    for token in (
        "POSIÇÃO DO OBJETO",
        "v149_x_spin",
        "v149_y_spin",
        "def _apply_position(",
        "Horizontal (X)",
        "Vertical (Y)",
        "Aplicar posição",
    ):
        assert token in source


def test_v149_adds_fill_and_outline_controls_for_shapes():
    source = _read("src/monitor_noticias/ui/art_studio_v149.py")
    for token in (
        "APARÊNCIA DA FORMA",
        "def _choose_fill(",
        "def _choose_outline(",
        "def _apply_outline_width(",
        'data["v149_outline"]',
        "def serialize_with_outline(",
        "def build_with_outline(",
    ):
        assert token in source


def test_v149_supports_precise_arrow_nudging_and_text_edit_safety():
    source = _read("src/monitor_noticias/ui/art_studio_v149.py")
    for token in (
        "def _nudge_selected(",
        "Qt.Key.Key_Left",
        "Qt.Key.Key_Right",
        "Qt.KeyboardModifier.ShiftModifier",
        "focus_item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction",
        'QKeySequence("Ctrl+D")',
    ):
        assert token in source


def test_v149_preserves_v148_compatibility_and_existing_history():
    source = _read("src/monitor_noticias/ui/art_studio_v149.py")
    assert "_v145_history_timer" in source
    assert "page._v146_base_serialize" in source
    assert "page._v146_base_build" in source
    assert "LOCKED_KEY" in source
    assert "artStudioLayersScroll" in source


def test_v149_uses_existing_qt_components_only():
    source = _read("src/monitor_noticias/ui/art_studio_v149.py")
    assert "from PySide6" in source
    assert "import fabric" not in source.lower()
    assert "import cv2" not in source.lower()
