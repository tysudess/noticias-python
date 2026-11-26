from __future__ import annotations

import ast
import builtins
from pathlib import Path
import symtable

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src/monitor_noticias/ui"
VERSIONS = range(161, 170)


def _module_path(version: int) -> Path:
    return UI / f"art_studio_v{version}.py"


def _undefined_globals(source: str, filename: str) -> list[tuple[str, str]]:
    """Detecta referências globais não importadas/definidas, inclusive em funções."""
    table = symtable.symtable(source, filename, "exec")
    module_globals = {
        symbol.get_name()
        for symbol in table.get_symbols()
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
    }
    missing: list[tuple[str, str]] = []

    def visit(scope, scope_path: str) -> None:
        for symbol in scope.get_symbols():
            name = symbol.get_name()
            if (
                symbol.is_global()
                and name not in module_globals
                and not hasattr(builtins, name)
                and not (name.startswith("__") and name.endswith("__"))
                and symbol.is_referenced()
            ):
                missing.append((scope_path, name))
        for child in scope.get_children():
            visit(child, f"{scope_path}/{child.get_name()}")

    visit(table, "module")
    return sorted(set(missing))


def test_no_undefined_global_names_in_estudio_versions_161_to_169():
    problems = {}
    for version in VERSIONS:
        path = _module_path(version)
        source = path.read_text(encoding="utf-8")
        missing = _undefined_globals(source, str(path))
        if missing:
            problems[path.name] = missing
    assert not problems, f"Referências globais não definidas: {problems}"


def test_apply_skin_resolves_palette_roles_before_any_conditional_branch():
    source = _module_path(161).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_skin"
    )
    first_if = next(
        index for index, node in enumerate(function.body)
        if isinstance(node, ast.If)
    )
    assigned_before_branch = set()
    assignments = {}
    for node in function.body[:first_if]:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_before_branch.add(target.id)
                    assignments[target.id] = node.value
    required = {"border", "accent", "accent_text", "panel"}
    assert required <= assigned_before_branch

    expected = {
        "dark": {
            "border": "#29475D", "accent": "#D6B66D",
            "accent_text": "#12283A", "panel": "#12283A",
        },
        "light": {
            "border": "#CDD9E3", "accent": "#B18B3E",
            "accent_text": "#FFFFFF", "panel": "#FFFFFF",
        },
    }
    for is_dark, mode in ((True, "dark"), (False, "light")):
        evaluated = {
            name: eval(compile(ast.Expression(assignments[name]), str(_module_path(161)), "eval"), {"dark": is_dark})
            for name in required
        }
        assert evaluated == expected[mode]


def test_v161_uses_standard_library_weakref_and_imports_header_layout():
    source = _module_path(161).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_weakref_from_stdlib = any(
        isinstance(node, ast.Import) and any(
            alias.name == "weakref" for alias in node.names
        )
        for node in tree.body
    )
    qtwidgets = next(
        node for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "PySide6.QtWidgets"
    )
    imported_widgets = {alias.name for alias in qtwidgets.names}
    assert imported_weakref_from_stdlib
    assert "QHBoxLayout" in imported_widgets


def test_apply_skin_runtime_smoke_for_light_dark_and_optional_toolbars():
    from types import SimpleNamespace

    source = _module_path(161).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_skin"
    )
    isolated = ast.Module(body=[function], type_ignores=[])

    class Widget:
        def __init__(self):
            self.stylesheet = ""

        def setStyleSheet(self, value):
            self.stylesheet = value

    namespace = {
        "_theme_id": lambda page: page.theme,
        "_skin_stylesheet": lambda theme: f"base:{theme}",
    }
    exec(compile(isolated, str(_module_path(161)), "exec"), namespace)
    apply_skin = namespace["_apply_skin"]

    for theme, accent, accent_text, border in (
        ("escuro", "#D6B66D", "#12283A", "#29475D"),
        ("claro", "#B18B3E", "#FFFFFF", "#CDD9E3"),
    ):
        # Também cobre a situação em que a barra de páginas existe sem a
        # barra de texto — antes disso, `border` ficava sem atribuição local.
        for include_toolbar, include_pages_bar in (
            (True, True), (False, True), (True, False), (False, False)
        ):
            view = Widget()
            toolbar = Widget() if include_toolbar else None
            pages_bar = Widget() if include_pages_bar else None
            page = SimpleNamespace(
                theme=theme,
                _v161_skin_theme=None,
                view=view,
                v147_text_toolbar=toolbar,
                v150_pages_bar=pages_bar,
                setStyleSheet=lambda value: None,
                update=lambda: None,
            )
            apply_skin(page)
            assert page._v161_skin_theme == theme
            if toolbar is not None:
                assert accent in toolbar.stylesheet
                assert border in toolbar.stylesheet
            if pages_bar is not None:
                assert accent in pages_bar.stylesheet
                assert accent_text in pages_bar.stylesheet
                assert border in pages_bar.stylesheet
