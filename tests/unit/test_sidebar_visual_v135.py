from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QFrame, QLabel

from monitor_noticias.ui.sidebar_widgets import (
    SIDEBAR_STYLE,
    SidebarNavItem,
)

_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_navigation_item_uses_icon_tile_and_active_marker():
    _app()
    item = SidebarNavItem("▤", "Notícias", "#FFFFFF")

    assert item.height() == 44
    assert item.icon_wrap.objectName() == "sidebarNavIconWrap"
    assert item.icon_wrap.size().width() == 31
    assert item.icon_wrap.size().height() == 31
    assert item.current_mark.objectName() == "sidebarNavCurrentMark"
    assert item.text.text() == "Notícias"

    item.set_active(True)
    assert item.property("active") is True
    assert item.indicator.property("active") is True
    item.set_active(False)
    assert item.property("active") is False


def test_sidebar_stylesheet_has_distinct_brand_groups_hover_and_active_states():
    required_rules = (
        "QFrame#sidebarBrandWrap",
        "QLabel#sidebarLogo",
        "QLabel#sidebarGroupLabel",
        "QFrame#sidebarNavIconWrap",
        "QFrame#sidebarNavItem:hover",
        'QFrame#sidebarNavItem[active="true"]',
        "QLabel#sidebarNavCurrentMark",
        "QFrame#sidebarStatusCard",
    )
    for rule in required_rules:
        assert rule in SIDEBAR_STYLE


def test_icon_tile_is_a_child_of_the_navigation_item():
    _app()
    item = SidebarNavItem("▶", "Vídeos", "#FFFFFF")
    assert item.icon_wrap.parentWidget() is item
    assert item.icon.parentWidget() is item.icon_wrap
    assert item.findChild(QFrame, "sidebarNavIconWrap") is item.icon_wrap
    assert item.findChild(QLabel, "sidebarNavCurrentMark") is item.current_mark
