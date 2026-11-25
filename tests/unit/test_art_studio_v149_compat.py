from enum import Enum
from pathlib import Path

from monitor_noticias.ui.art_studio_v149_compat import _enum_to_int

ROOT = Path(__file__).resolve().parents[2]


class FakeQtEnum(Enum):
    SHIFT = 0x02000000
    LEFT = 0x01000012


def test_qt_enum_values_are_converted_without_calling_int_on_enum():
    assert _enum_to_int(FakeQtEnum.SHIFT) == 0x02000000
    assert _enum_to_int(FakeQtEnum.LEFT) == 0x01000012
    assert _enum_to_int(0x02000000) == 0x02000000


def test_run_applies_v149_compatibility_before_installing_v149():
    source = (ROOT / "run.py").read_text(encoding="utf-8")
    patch = source.index("install_art_studio_v149_shortcut_compatibility()")
    install = source.index("install_art_studio_v149()")
    startup = source.index("from monitor_noticias.app.application import main")
    assert patch < install < startup


def test_compatibility_uses_enum_value_for_modifier_and_key():
    source = (
        ROOT / "src/monitor_noticias/ui/art_studio_v149_compat.py"
    ).read_text(encoding="utf-8")
    assert 'getattr(value, "value", value)' in source
    assert "_enum_to_int(modifiers[0])" in source
    assert "_enum_to_int(key)" in source
