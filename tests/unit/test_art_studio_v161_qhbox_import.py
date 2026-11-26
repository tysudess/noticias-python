from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/monitor_noticias/ui/art_studio_v161.py"


def test_every_used_qtwidgets_symbol_is_imported_from_qtwidgets():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "PySide6.QtWidgets":
            imported.update(alias.asname or alias.name for alias in node.names)
    used = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "QHBoxLayout"
    }
    assert "QHBoxLayout" in used
    assert used <= imported


def test_header_horizontal_layout_has_required_import():
    source = SOURCE.read_text(encoding="utf-8")
    import_block = source.split("from PySide6.QtWidgets import (", 1)[1].split(")", 1)[0]
    assert "QHBoxLayout," in import_block
    assert "row = QHBoxLayout(brand)" in source
