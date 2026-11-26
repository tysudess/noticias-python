from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v160_after_v159_and_before_application_main():
    source = _read("run.py")
    v159 = source.index("install_art_studio_v159()")
    v160 = source.index("install_art_studio_v160()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v159 < v160 < main


def test_letter_spacing_uses_qtextcharformat_and_absolute_spacing():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "setFontLetterSpacingType(QFont.SpacingType.AbsoluteSpacing)" in source
    assert "setFontLetterSpacing(value)" in source
    assert "cursor.mergeCharFormat(char_format)" in source


def test_letter_spacing_preserves_history_and_autosave():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "_v145_history_timer" in source
    assert "_schedule_autosave(page)" in source
    assert "QTextCursor.SelectionType.Document" in source


def test_letter_spacing_controls_require_one_visible_unlocked_text_layer():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "len(selected) != 1" in source
    assert "isinstance(selected[0], QGraphicsTextItem)" in source
    assert "selected[0].isVisible()" in source
    assert "selected[0].data(LOCKED_KEY)" in source


def test_sidebar_uses_section_icon_color_with_light_theme_contrast():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "_darken_for_light_theme(icon_color)" in source
    assert "apply_widget_theme_stylesheet(icon, theme)" in source
    assert "icon.setVisible(True)" in source
    assert "item.icon_wrap.setVisible(True)" in source


def test_compact_mode_includes_custom_art_studio_navigation_item():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "sidebar.findChildren(SidebarNavItem)" in source
    assert 'findChildren(..., "sidebarNavItem")' in source
    assert "item.text.setVisible(not compact)" in source


def test_sidebar_patch_is_idempotent_and_does_not_replace_navigation_structure():
    source = _read("src/monitor_noticias/ui/art_studio_v160.py")
    assert "_v160_icon_patch_installed" in source
    assert "_v160_sidebar_compact_patch_installed" in source
    assert "original_set_compact(window, compact)" in source
    assert "self.nav_buttons" not in source
