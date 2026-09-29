from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLICATION = ROOT / "src" / "monitor_noticias" / "app" / "application.py"


def test_v87_digital_newspapers_is_not_installed_at_runtime():
    source = APPLICATION.read_text(encoding="utf-8")

    assert "digital_newspapers_integration" not in source
    assert "install_digital_newspapers" not in source


def test_v87_keeps_existing_core_integrations():
    source = APPLICATION.read_text(encoding="utf-8")

    assert "install_settings_proxy_toggle_patch" in source
    assert "install_home_layout_v76_patch" in source
    assert "install_sources_bahia_patch" in source
    assert "install_authenticated_window" in source
    assert "install_pdf_export_quality_fix" in source
