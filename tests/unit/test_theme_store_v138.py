from __future__ import annotations

import json

import pytest

from monitor_noticias.ui.theme_store import (
    DEFAULT_THEME,
    THEME_CLARO,
    THEME_ESCURO,
    load_saved_theme,
    save_theme,
)


def test_missing_or_invalid_preference_uses_dark_default(tmp_path):
    path = tmp_path / "preferences" / "appearance.json"
    assert load_saved_theme(path) == DEFAULT_THEME

    path.parent.mkdir(parents=True)
    path.write_text("{invalid", encoding="utf-8")
    assert load_saved_theme(path) == THEME_ESCURO


def test_legacy_marinho_preference_migrates_to_dark(tmp_path):
    path = tmp_path / "appearance.json"
    path.write_text(json.dumps({"version": 1, "theme": "marinho"}), encoding="utf-8")
    assert load_saved_theme(path) == THEME_ESCURO


def test_save_and_reload_both_supported_themes(tmp_path):
    path = tmp_path / "preferences" / "appearance.json"
    for theme in (THEME_CLARO, THEME_ESCURO):
        save_theme(path, theme)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["theme"] == theme
        assert load_saved_theme(path) == theme


def test_save_rejects_unknown_theme(tmp_path):
    with pytest.raises(ValueError):
        save_theme(tmp_path / "appearance.json", "azul")
