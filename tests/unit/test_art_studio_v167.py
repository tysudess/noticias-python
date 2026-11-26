from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v167_after_v166_and_before_main():
    source = _read("run.py")
    v166 = source.index("install_art_studio_v166()")
    v167 = source.index("install_art_studio_v167()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v166 < v167 < main


def test_typography_toolbar_is_added_to_existing_inline_text_toolbar():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    assert 'getattr(page, "v147_text_toolbar", None)' in source
    assert 'QPushButton("Aa+ Tipografia", toolbar)' in source
    assert 'QKeySequence("Ctrl+Shift+T")' in source


def test_typography_dialog_exposes_professional_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    for token in (
        "QFontComboBox", "Família tipográfica", "Peso", "Espaço entre letras",
        "Espaço entre palavras", "Entrelinha", "Espaço após parágrafo",
        "Transformação de caixa", "Alinhamento", "Contorno da letra",
        "Realçar texto com fundo", "Aplicar à seleção",
    ):
        assert token in source


def test_text_selection_must_be_single_visible_unlocked_and_belong_to_scene():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    assert "len(selected) != 1" in source
    assert "item.scene() is not page.scene" in source
    assert "not item.isVisible()" in source
    assert "item.data(LOCKED_KEY)" in source


def test_formatting_uses_rich_text_cursor_and_persists_through_existing_html_serializer():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    assert "cursor.mergeCharFormat(char_format)" in source
    assert "cursor.mergeBlockFormat(block_format)" in source
    assert "_schedule_autosave(page)" in source
    assert "_v145_history_timer" in source
    # A V167 não substitui o serializador HTML existente; aplica formatação
    # diretamente ao QTextDocument já mantido pelo fluxo V147.
    assert "QTextCharFormat" in source and "QTextBlockFormat" in source
    assert "block.lineHeightType()" in source
    assert "char.textOutline()" in source
    assert "_v146_base_serialize =" not in source


def test_dialog_cancelling_does_not_apply_formatting():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    assert "if dialog.exec() != QDialog.DialogCode.Accepted:" in source
    assert "return\n    _apply_typography(page, item, dialog.result_config())" in source


def test_typography_installer_is_idempotent_and_versioned_after_v166():
    source = _read("src/monitor_noticias/ui/art_studio_v167.py")
    assert "_v167_installed" in source
    assert "_v167_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source
