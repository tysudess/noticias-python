from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v159_installs_after_v158_and_before_application_startup():
    source = _read("run.py")
    assert source.index("install_art_studio_v158()") < source.index("install_art_studio_v159()")
    assert source.index("install_art_studio_v159()") < source.index("from monitor_noticias.app.application import main")


def test_v159_adds_word_spacing_and_paragraph_line_spacing():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert "setFontWordSpacing(value)" in source
    assert "setLineHeight(" in source
    assert "LineHeightTypes.ProportionalHeight" in source


def test_v159_preserves_rich_text_by_using_text_cursor_formats():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert "cursor.mergeCharFormat(char_format)" in source
    assert "cursor.mergeBlockFormat(block_format)" in source
    assert "cursor.select(QTextCursor.SelectionType.Document)" in source


def test_v159_only_edits_one_visible_unlocked_text_layer():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert "len(selected) != 1" in source
    assert "isinstance(selected[0], QGraphicsTextItem)" in source
    assert "item.data(LOCKED_KEY)" in source
    assert "item.isVisible()" in source


def test_v159_updates_history_and_v157_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert "history_timer.start()" in source
    assert "_schedule_autosave(page)" in source
    assert "from monitor_noticias.ui.art_studio_v157 import _schedule_autosave" in source


def test_v159_adds_controls_to_existing_text_toolbar_without_new_dependencies():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert 'getattr(page, "v147_text_toolbar", None)' in source
    assert "artStudioWordSpacingV159" in source
    assert "artStudioLineSpacingV159" in source
    assert "requests" not in source
    assert "PIL" not in source


def test_v159_does_not_change_the_centralart_project_schema():
    source = _read("src/monitor_noticias/ui/art_studio_v159.py")
    assert ".centralart" in source
    assert "PROJECT_FORMAT" not in source
    assert "json.dump" not in source
