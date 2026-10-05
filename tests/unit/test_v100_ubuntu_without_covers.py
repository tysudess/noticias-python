from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ROOT / "src" / "monitor_noticias" / "ui" / "sections.py"


def _load_sections(platform: str):
    original = sys.platform
    try:
        sys.platform = platform
        spec = importlib.util.spec_from_file_location(
            f"sections_v100_{platform.replace('-', '_')}",
            SECTIONS,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.platform = original


def test_ubuntu_removes_covers_from_navigation_and_tools():
    sections = _load_sections("linux")

    assert sections.Section.COVERS not in sections.SECTION_ORDER
    assert sections.Section.COVERS not in sections.TOOL_SECTIONS
    assert sections.Section.NEWS in sections.SECTION_ORDER
    assert sections.Section.PDF_EDITOR in sections.SECTION_ORDER


def test_windows_keeps_covers_unchanged():
    sections = _load_sections("win32")

    assert sections.Section.COVERS in sections.SECTION_ORDER
    assert sections.Section.COVERS in sections.TOOL_SECTIONS
    assert sections.SECTION_ORDER.index(sections.Section.COVERS) < sections.SECTION_ORDER.index(
        sections.Section.PDF_EDITOR
    )
