from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/monitor_noticias/ui/art_studio_v170.py"


def test_compact_header_targets_only_requested_status_and_account_controls():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_compact_main_header")
    names = {
        elt.value for node in ast.walk(function)
        if isinstance(node, (ast.Tuple, ast.List))
        for elt in node.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }
    assert {
        "proxy_chip", "auto_chip", "clock",
        "_auth_user_label", "_auth_account_button", "_auth_logout_button",
    } <= names
    assert "_auth_account_button" in names
    assert "_auth_logout_button" in names


def test_compact_header_does_not_change_login_runtime_or_tray_actions():
    source = SOURCE.read_text(encoding="utf-8")
    header = source.split("def _compact_main_header", 1)[1].split("def _polish_workspace", 1)[0]
    assert "runtime.logout" not in header
    assert "setEnabled(False)" not in header
    assert "_hide_global_header_widget(window, name)" in header
