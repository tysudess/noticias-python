from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QScrollArea, QVBoxLayout

from monitor_noticias.ui.sections import SECTION_ORDER
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


def test_sidebar_rebuild_keeps_regular_pages_grouped_and_scrollable():
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

    for button in nav_buttons.values():
        assert button.parentWidget() is scroll.widget()


def test_dynamic_recorder_and_admin_items_are_moved_into_the_grouped_layout():
    sidebar, nav_buttons = _make_sidebar()
    recorder = SidebarNavItem("●", "Gravador de Tela", "#FFFFFF", parent=sidebar)
    admin = SidebarNavItem("♚", "Administração", "#FFFFFF", parent=sidebar)

    assert rebuild_sidebar_layout(
        sidebar,
        nav_buttons,
        {
            "SCREEN_RECORDER": recorder,
            "ADMINISTRATION": admin,
        },
    ) is True

    scroll = sidebar.findChild(QScrollArea, "sidebarNavigationScroll")
    assert scroll is not None
    assert recorder.parentWidget() is scroll.widget()
    assert admin.parentWidget() is scroll.widget()

    names = {
        item.accessibleName()
        for item in scroll.findChildren(SidebarNavItem)
    }
    assert "Gravador de Tela" in names
    assert "Administração" in names
    assert len(names) == len(nav_buttons) + 2

    headings = [
        label.text()
        for label in scroll.findChildren(QLabel, "sidebarGroupLabel")
    ]
    assert headings == ["PAINEL", "MONITORAMENTO", "FERRAMENTAS", "SISTEMA"]


def test_navigation_item_active_state_is_preserved():
    _app()
    item = SidebarNavItem("⌂", "Início", "#FFFFFF")
    item.set_active(True)
    assert item.property("active") is True
    assert item.indicator.property("active") is True
    item.set_active(False)
    assert item.property("active") is False
