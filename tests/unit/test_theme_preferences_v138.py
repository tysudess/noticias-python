from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from monitor_noticias.ui.theme_preferences import ThemePreferencesCard
from monitor_noticias.ui.theme_store import THEME_CLARO, THEME_ESCURO

_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_settings_card_offers_light_and_dark_and_marks_dark_by_default(tmp_path):
    _app()

    class FakeWindow:
        pass

    card = ThemePreferencesCard(FakeWindow(), tmp_path / "appearance.json", THEME_ESCURO)
    assert set(card.theme_buttons) == {THEME_ESCURO, THEME_CLARO}
    assert card.theme_buttons[THEME_ESCURO].isChecked()
    assert not card.theme_buttons[THEME_CLARO].isChecked()
    assert "ESCURO" in card.theme_buttons[THEME_ESCURO].text()
    assert "CLARO" in card.theme_buttons[THEME_CLARO].text()
