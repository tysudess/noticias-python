from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_v147_uses_inline_text_items_without_modal_text_entry():
    source = _read("src/monitor_noticias/ui/art_studio_v147.py")
    for token in (
        "class InlineTextItem(QGraphicsTextItem)",
        "def begin_inline_edit(",
        "def mouseDoubleClickEvent(",
        "def add_text_inline(",
        "Digite seu texto",
        "Qt.TextInteractionFlag.TextEditorInteraction",
        'page.edit_text_button.setText("Editar no canvas")',
    ):
        assert token in source
    assert "QInputDialog" not in source


def test_v147_adds_adobe_like_inline_format_toolbar():
    source = _read("src/monitor_noticias/ui/art_studio_v147.py")
    for token in (
        "QFontComboBox",
        "v147_font_size",
        "v147_bold_button",
        "v147_italic_button",
        "v147_underline_button",
        "v147_color_button",
        "v147_align_combo",
        "def _apply_text_format(",
        "def _apply_alignment(",
        "artStudioInlineTextToolbar",
    ):
        assert token in source


def test_v147_preserves_legacy_text_projects_and_v146_groups():
    source = _read("src/monitor_noticias/ui/art_studio_v147.py")
    for token in (
        "def _promote_text_item(",
        "page._v146_base_build = base_build_inline",
        "page._build_item_from_data = build_inline",
        'data["html"] = item.toHtml()',
        'rich_html = data.get("html")',
        "item.setHtml(str(rich_html))",
        "replacement.setData(key, value)",
        "replacement.setTextWidth(item.textWidth())",
    ):
        assert token in source


def test_v147_compacts_right_panel_inside_scroll_area():
    source = _read("src/monitor_noticias/ui/art_studio_v147.py")
    for token in (
        "def _install_scrollable_layers_panel(",
        "QScrollArea(panel)",
        "scroll.setWidgetResizable(True)",
        "layers.setMaximumHeight(150)",
        "panel.setFixedWidth(300)",
        "artStudioLayersScroll",
    ):
        assert token in source


def test_v147_is_installed_after_v145_and_v146():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    start = source.index("def _enhance_art_studio_page")
    v145 = source.index("enhance_art_studio_page,", start)
    v146 = source.index("enhance_art_studio_page_v146,", start)
    v147 = source.index("enhance_art_studio_page_v147,", start)
    loop = source.index("for enhance in enhancers:", start)
    apply_call = source.index("enhance(page)", loop)
    assert v145 < v146 < v147 < loop < apply_call


def test_v147_keeps_the_v145_view_and_v146_qframe_fixes():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    start = source.index("def _enhance_art_studio_page")
    qframe_at = source.index("art_studio_v146_module.QFrame = QFrame", start)
    v146_at = source.index("enhance_art_studio_page_v146,", start)
    assert "class _DeferredArtStudioView" in source
    assert "_install_deferred_view_compatibility()" in source
    assert qframe_at < v146_at
