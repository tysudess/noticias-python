from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QLabel, QScrollArea

from monitor_noticias.ui.sections import SECTION_ORDER, Section
from monitor_noticias.ui.sidebar_widgets import (
    SIDEBAR_WIDTH,
    SidebarNavItem,
    rebuild_sidebar_layout,
)


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _make_sidebar():
    _app()
    sidebar = QFrame()
    sidebar.setObjectName("sidebar")
    outer = QVBoxLayout(sidebar)

    brand = QFrame(sidebar)
    brand.setObjectName("sidebarBrandWrap")
    outer.addWidget(brand)

    nav_buttons = {}
    for section in SECTION_ORDER:
        item = SidebarNavItem(
            icon_text=section.value.icon,
            label_text=section.value.label,
            icon_color="#FFFFFF",
            parent=sidebar,
        )
        outer.addWidget(item)
        nav_buttons[section] = item

    status = QFrame(sidebar)
    status.setObjectName("sidebarStatusCard")
    outer.addWidget(status)
    return sidebar, nav_buttons


def test_sidebar_rebuild_preserves_all_navigation_items_and_groups():
    sidebar, nav_buttons = _make_sidebar()

    assert rebuild_sidebar_layout(sidebar, nav_buttons) is True
    assert sidebar.width() == SIDEBAR_WIDTH
    assert sidebar.property("sidebarLayoutV133") is True

    scroll = sidebar.findChild(QScrollArea, "sidebarNavigationScroll")
    assert scroll is not None
    assert scroll.widgetResizable() is True

    labels = [
        label.text()
        for label in scroll.findChildren(QLabel, "sidebarGroupLabel")
    ]
    assert labels == ["PAINEL", "MONITORAMENTO", "FERRAMENTAS", "SISTEMA"]

    for section in SECTION_ORDER:
        assert nav_buttons[section].parentWidget() is scroll.widget()


def test_linux_navigation_grouping_omits_only_the_covers_section():
    sidebar, nav_buttons = _make_sidebar()
    assert rebuild_sidebar_layout(sidebar, nav_buttons)

    scroll = sidebar.findChild(QScrollArea, "sidebarNavigationScroll")
    visible_names = {
        item.accessibleName()
        for item in scroll.findChildren(SidebarNavItem)
    }
    expected_names = {section.value.label for section in SECTION_ORDER}
    assert visible_names == expected_names
    if sys.platform.startswith("linux"):
        assert Section.COVERS not in SECTION_ORDER


def test_navigation_item_active_state_updates_accessible_property():
    _app()
    item = SidebarNavItem("⌂", "Início", "#FFFFFF")
    item.set_active(True)
    assert item.property("active") is True
    assert item.indicator.property("active") is True
    item.set_active(False)
    assert item.property("active") is False
