from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v158_installs_after_v157_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v157()") < source.index("install_art_studio_v158()")
    assert source.index("install_art_studio_v158()") < source.index("from monitor_noticias.app.application import main")


def test_v158_adds_rich_text_highlight_and_clear_highlight():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "def _choose_highlight" in source
    assert "fmt.setBackground(QBrush(color))" in source
    assert "def _clear_highlight" in source
    assert "setBackground(QBrush(Qt.BrushStyle.NoBrush))" in source


def test_v158_preserves_other_character_formatting_when_clearing_highlight():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "cursor.mergeCharFormat(char_format)" in source
    assert "cursor.select(QTextCursor.SelectionType.Document)" in source
    assert "as demais formatações foram preservadas" in source


def test_v158_supports_strikethrough_superscript_and_subscript():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "setFontStrikeOut" in source
    assert "AlignSuperScript" in source
    assert "AlignSubScript" in source
    assert "AlignNormal" in source


def test_v158_includes_five_typography_presets():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    for name in ("Título", "Subtítulo", "Corpo", "Legenda", "Destaque"):
        assert f'"{name}"' in source
    assert "setFontPixelSize" in source
    assert "setFontWeight" in source


def test_v158_only_edits_a_single_visible_unlocked_text_layer():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "len(selected) != 1" in source
    assert "item.isVisible()" in source
    assert "item.data(LOCKED_KEY)" in source


def test_v158_records_text_changes_in_history_and_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "history_timer.start()" in source
    assert "_schedule_autosave(page)" in source
    assert "from monitor_noticias.ui.art_studio_v157 import _schedule_autosave" in source


def test_v158_does_not_change_project_format_or_add_external_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert ".centralart" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "PIL" not in source


def test_v158_adds_compact_toolbar_controls_and_selection_sync():
    source = _read("src/monitor_noticias/ui/art_studio_v158.py")
    assert "v147_text_toolbar" in source
    assert "page.scene.selectionChanged.connect" in source
    assert "artStudioTextPresetV158" in source
    assert "artStudioTextHighlightV158" in source
