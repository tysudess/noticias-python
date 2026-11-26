from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "run.py"
MODULE = ROOT / "src/monitor_noticias/ui/art_studio_v178.py"
V174 = ROOT / "src/monitor_noticias/ui/art_studio_v174.py"
V175 = ROOT / "src/monitor_noticias/ui/art_studio_v175.py"
V176 = ROOT / "src/monitor_noticias/ui/art_studio_v176.py"
V177 = ROOT / "src/monitor_noticias/ui/art_studio_v177.py"


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            result.setdefault((node.level, node.module), set()).update(
                alias.name for alias in node.names
            )
    return result


def test_v178_is_installed_after_v177_and_before_application_start():
    source = RUN.read_text(encoding="utf-8")
    assert source.index("install_art_studio_v177()") < source.index(
        "install_art_studio_v178()"
    )
    assert source.index("install_art_studio_v178()") < source.index(
        "from monitor_noticias.app.application import main"
    )


def test_v178_uses_the_layout_parent_instead_of_uninitialized_page_attribute():
    source = MODULE.read_text(encoding="utf-8")
    assert "parent = layout.parentWidget() or page" in source
    assert "button = QToolButton(parent)" in source
    assert "page.v175_context_toolbar" not in source
    assert "art_studio_v175._add_context_button = add_context_button" in source


def test_recent_studio_layers_import_qpalette_from_qtgui():
    for path in (V174, V175, V176, V177):
        imports = _imports(path)
        uses_qpalette = any("QPalette" in names for names in imports.values())
        if uses_qpalette:
            assert "QPalette" in imports.get((0, "PySide6.QtGui"), set()), path
            assert "QPalette" not in imports.get(
                (0, "PySide6.QtWidgets"), set()
            ), path


def test_v178_installer_is_idempotent_and_uses_existing_v175_action_router():
    source = MODULE.read_text(encoding="utf-8")
    assert "if _INSTALLED:" in source
    assert "_v178_context_toolbar_parent_fixed" in source
    assert "art_studio_v175._context_action(page, action)" in source


def test_v178_module_and_run_file_parse():
    ast.parse(MODULE.read_text(encoding="utf-8"))
    ast.parse(RUN.read_text(encoding="utf-8"))
