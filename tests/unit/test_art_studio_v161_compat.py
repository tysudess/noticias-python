from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import weakref

ROOT = Path(__file__).resolve().parents[2]
COMPAT_PATH = ROOT / "src/monitor_noticias/ui/art_studio_v161_compat.py"


def test_compatibility_installs_stdlib_weakref_before_v161_import():
    source = (ROOT / "run.py").read_text(encoding="utf-8")
    compat_call = source.index("install_art_studio_v161_weakref_compatibility()")
    v161_import = source.index("from monitor_noticias.ui.art_studio_v161 import")
    assert compat_call < v161_import


def test_compatibility_exposes_the_standard_library_module(monkeypatch):
    fake_package = types.ModuleType("PySide6")
    fake_qtcore = types.ModuleType("PySide6.QtCore")
    fake_package.QtCore = fake_qtcore
    monkeypatch.setitem(sys.modules, "PySide6", fake_package)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", fake_qtcore)

    spec = importlib.util.spec_from_file_location("art_studio_v161_compat_test", COMPAT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.install_art_studio_v161_weakref_compatibility()
    assert fake_qtcore.weakref is weakref
    assert fake_qtcore.weakref.ref is weakref.ref


def test_compatibility_is_idempotent():
    fake_package = types.ModuleType("PySide6")
    fake_qtcore = types.ModuleType("PySide6.QtCore")
    fake_package.QtCore = fake_qtcore
    old_package = sys.modules.get("PySide6")
    old_core = sys.modules.get("PySide6.QtCore")
    sys.modules["PySide6"] = fake_package
    sys.modules["PySide6.QtCore"] = fake_qtcore
    try:
        spec = importlib.util.spec_from_file_location("art_studio_v161_compat_idempotent_test", COMPAT_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.install_art_studio_v161_weakref_compatibility()
        first = fake_qtcore.weakref
        module.install_art_studio_v161_weakref_compatibility()
        assert fake_qtcore.weakref is first is weakref
    finally:
        if old_package is None:
            sys.modules.pop("PySide6", None)
        else:
            sys.modules["PySide6"] = old_package
        if old_core is None:
            sys.modules.pop("PySide6.QtCore", None)
        else:
            sys.modules["PySide6.QtCore"] = old_core
