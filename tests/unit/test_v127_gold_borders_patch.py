from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from monitor_noticias.ui.gold_borders_patch import (
    GOLD_BORDER,
    GOLD_BORDER_QSS,
    rewrite_inline_border_stylesheet,
)


def test_inline_border_color_is_replaced_without_changing_other_properties():
    original = "background:#FFFFFF;border:1px solid #D6E6F7;border-radius:14px;padding:8px;"
    changed = rewrite_inline_border_stylesheet(original)

    assert f"border:1px solid {GOLD_BORDER};" in changed
    assert "background:#FFFFFF;" in changed
    assert "border-radius:14px;" in changed
    assert "padding:8px;" in changed


def test_inline_border_is_added_if_missing():
    changed = rewrite_inline_border_stylesheet("background:#FFFFFF;border-radius:12px;")
    assert f"border: 1px solid {GOLD_BORDER};" in changed
    assert "background:#FFFFFF;" in changed


def test_qss_contains_card_tabs_and_sidebar_navigation_outlines():
    assert "QFrame#metricCard" in GOLD_BORDER_QSS
    assert "QFrame#demandCard" in GOLD_BORDER_QSS
    assert "QTabBar::tab" in GOLD_BORDER_QSS
    assert "QFrame#sidebarNavItem" in GOLD_BORDER_QSS
    assert GOLD_BORDER in GOLD_BORDER_QSS
