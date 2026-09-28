from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_v82_spec_does_not_mutate_exe_resources_after_collect():
    path = ROOT / "MonitorDeNoticias.spec"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden = {
        "BeginUpdateResourceW",
        "UpdateResourceW",
        "EndUpdateResourceW",
    }

    used_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }
    used_attrs = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }

    assert not (forbidden & used_names)
    assert not (forbidden & used_attrs)
    assert 'icon=str(APP_ASSETS / "app_icon.ico")' in source


def test_v82_spec_validates_pyinstaller_archive_read_only():
    spec = (ROOT / "MonitorDeNoticias.spec").read_text(encoding="utf-8")

    assert "CArchiveReader" in spec
    assert "_exe_size < 2_000_000" in spec
    assert "PKG/CArchive PyInstaller" in spec
