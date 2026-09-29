from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "src" / "monitor_noticias" / "ui" / "digital_newspapers_page.py"


def _function_source(name: str) -> str:
    source = PAGE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"Função não encontrada: {name}")


def test_v83_credential_fields_are_explicitly_editable_and_focusable():
    source = PAGE.read_text(encoding="utf-8")

    assert "self.credential_user.setReadOnly(False)" in source
    assert "self.credential_password.setReadOnly(False)" in source
    assert "self.credential_user.setFocusPolicy(Qt.FocusPolicy.StrongFocus)" in source
    assert "self.credential_password.setFocusPolicy(Qt.FocusPolicy.StrongFocus)" in source
    assert "self.credential_user.setMinimumHeight(38)" in source
    assert "self.credential_password.setMinimumHeight(38)" in source


def test_v83_cookie_updates_do_not_reload_credential_editor():
    source = PAGE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_session_changed":
            target = node
            break
    assert target is not None

    called_attrs = []
    for node in ast.walk(target):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_attrs.append(node.func.attr)

    assert "_refresh_providers" not in called_attrs
    assert "_load_selected_credentials" not in called_attrs

    segment = ast.get_source_segment(source, target) or ""
    assert "self.provider_table.item(row, 1)" in segment
    assert "item.setText(session)" in segment


def test_v83_right_panel_scrolls_instead_of_compressing_controls():
    source = PAGE.read_text(encoding="utf-8")

    assert "QScrollArea" in source
    assert 'action_scroll.setObjectName("digitalActionScroll")' in source
    assert "action_card.setMinimumHeight(620)" in source
    assert "action_scroll.setWidgetResizable(True)" in source
    assert "root.addLayout(content, 4)" in source
    assert "root.addWidget(history_card, 1)" in source
