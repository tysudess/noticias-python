from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from monitor_noticias.ui.gold_borders_patch import GOLD_BORDER_QSS
from monitor_noticias.ui.sidebar_widgets import SIDEBAR_STYLE


def test_sidebar_uses_flat_modern_colors_instead_of_decorative_gradients():
    assert "qlineargradient" not in SIDEBAR_STYLE
    assert "background:#071D31" in SIDEBAR_STYLE
    assert "QFrame#sidebarNavItem[active=\"true\"]" in SIDEBAR_STYLE
    assert "QFrame#sidebarNavItem:hover" in SIDEBAR_STYLE


def test_general_gold_outline_system_does_not_override_sidebar_navigation():
    assert "QFrame#sidebarNavItem" not in GOLD_BORDER_QSS
    assert "QFrame#sidebarStatusCard" not in GOLD_BORDER_QSS
    # The wider application keeps its gold outline system for content cards/tabs.
    assert "QFrame#metricCard" in GOLD_BORDER_QSS
    assert "QTabBar::tab" in GOLD_BORDER_QSS
