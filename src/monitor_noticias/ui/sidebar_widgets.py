from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


SIDEBAR_WIDTH = 236

SIDEBAR_STYLE = """
QFrame#sidebar {
    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #092E53,
        stop:0.55 #082745,
        stop:1 #061C34
    );
    border:0;
    border-right:1px solid #9E824B;
}

QFrame#sidebarBrandWrap {
    background:rgba(255,255,255,0.045);
    border:1px solid rgba(198,161,91,0.42);
    border-radius:13px;
}

QLabel#sidebarLogo {
    background:#D8B765;
    color:#082746;
    border:1px solid #F0D99D;
    border-radius:11px;
    font-family:"Segoe UI";
    font-size:14px;
    font-weight:900;
}

QLabel#sidebarBrandTitle {
    color:#FFFFFF;
    background:transparent;
    border:0;
    font-size:14px;
    font-weight:800;
}

QLabel#sidebarBrandSub {
    color:#B6C9DC;
    background:transparent;
    border:0;
    font-size:9px;
    font-weight:600;
}

QLabel#sidebarGroupLabel {
    color:#8FAAC4;
    background:transparent;
    border:0;
    padding:7px 4px 3px 5px;
    font-size:9px;
    font-weight:800;
    letter-spacing:1px;
}

QFrame#sidebarNavItem {
    background:transparent;
    border:1px solid rgba(198,161,91,0.13);
    border-radius:10px;
}

QFrame#sidebarNavItem:hover {
    background:rgba(42,104,157,0.28);
    border:1px solid rgba(198,161,91,0.52);
}

QFrame#sidebarNavItem[active="true"] {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #174C78,
        stop:1 #123D65
    );
    border:1px solid #C6A15B;
}

QFrame#sidebarNavIndicator {
    background:transparent;
    border:0;
    border-radius:2px;
}

QFrame#sidebarNavIndicator[active="true"] {
    background:#E6C579;
}

QLabel#sidebarNavIcon {
    color:#BBD0E3;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:16px;
    font-weight:700;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavIcon {
    color:#F1D99F;
}

QLabel#sidebarNavText {
    color:#E5EDF5;
    background:transparent;
    border:0;
    font-size:11px;
    font-weight:600;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavText {
    color:#FFFFFF;
    font-weight:800;
}

QFrame#sidebarStatusCard {
    background:rgba(255,255,255,0.055);
    border:1px solid rgba(198,161,91,0.38);
    border-radius:12px;
}

QLabel#sidebarStatusIcon {
    color:#E2C477;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:17px;
    font-weight:700;
}

QLabel#sidebarStatusTitle {
    color:#A9BED2;
    background:transparent;
    border:0;
    font-size:9px;
    font-weight:700;
}

QLabel#sidebarStatusText {
    color:#F0F5FA;
    background:transparent;
    border:0;
    font-size:10px;
    font-weight:600;
}

QScrollArea#sidebarNavigationScroll {
    background:transparent;
    border:0;
}

QScrollArea#sidebarNavigationScroll QWidget#sidebarNavigationContent {
    background:transparent;
}

QScrollBar:vertical {
    background:transparent;
    width:6px;
    margin:2px 0 2px 0;
}

QScrollBar::handle:vertical {
    background:rgba(173,195,217,0.42);
    min-height:28px;
    border-radius:3px;
}

QScrollBar::handle:vertical:hover {
    background:rgba(224,198,133,0.82);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background:transparent;
    border:0;
    height:0;
}
"""


_GROUPS = (
    ("PAINEL", ("HOME",)),
    (
        "MONITORAMENTO",
        ("NEWS", "VIDEOS", "DEMANDS", "SOURCES", "HISTORY", "TERMS", "STOP"),
    ),
    (
        "FERRAMENTAS",
        ("NEWS_EXTRACTOR", "COVERS", "PDF_EDITOR", "EXTRACTOR", "VIDEO_EDITOR"),
    ),
    ("SISTEMA", ("SETTINGS",)),
)


def rebuild_sidebar_layout(
    sidebar: QFrame,
    nav_buttons: Mapping[object, "SidebarNavItem"],
) -> bool:
    """Reorganiza a barra criada pela MainWindow sem alterar suas ações."""
    if sidebar.property("sidebarLayoutV133"):
        return True
    if not nav_buttons:
        return False

    outer = sidebar.layout()
    if not isinstance(outer, QVBoxLayout):
        return False

    brand = sidebar.findChild(QFrame, "sidebarBrandWrap")
    status = sidebar.findChild(QFrame, "sidebarStatusCard")
    if brand is None or status is None:
        return False

    sidebar.setUpdatesEnabled(False)
    try:
        logo = sidebar.findChild(QLabel, "sidebarLogo")
        if logo is not None:
            logo.setText("CM")
            logo.setFixedSize(40, 40)
            logo.setToolTip("Central Inteligente de Mídia")

        status_icon = sidebar.findChild(QLabel, "sidebarStatusIcon")
        if status_icon is not None:
            status_icon.setText("●")

        while outer.count():
            item = outer.takeAt(0)
            if item is not None:
                del item

        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)
        sidebar.setFixedWidth(SIDEBAR_WIDTH)

        brand.setMinimumHeight(66)
        outer.addWidget(brand, 0)

        scroll = QScrollArea(sidebar)
        scroll.setObjectName("sidebarNavigationScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        content = QWidget()
        content.setObjectName("sidebarNavigationContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 1, 2, 4)
        content_layout.setSpacing(5)

        by_name = {
            getattr(section, "name", ""): (section, button)
            for section, button in nav_buttons.items()
        }

        for group_label, section_names in _GROUPS:
            group_items = [by_name[name] for name in section_names if name in by_name]
            if not group_items:
                continue

            heading = QLabel(group_label)
            heading.setObjectName("sidebarGroupLabel")
            heading.setMinimumHeight(20)
            content_layout.addWidget(heading)

            for section, button in group_items:
                button.setToolTip(section.value.subtitle)
                button.setAccessibleName(section.value.label)
                button.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )
                content_layout.addWidget(button)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(status, 0)

        sidebar.setProperty("sidebarLayoutV133", True)
        sidebar.updateGeometry()
        sidebar.update()
        return True
    finally:
        sidebar.setUpdatesEnabled(True)


class SidebarNavItem(QFrame):
    clicked = Signal()

    def __init__(
        self,
        icon_text: str,
        label_text: str,
        icon_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._active = False
        self._refine_queued = False

        self.setObjectName("sidebarNavItem")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(label_text)
        self.setFixedHeight(40)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(10)

        self.indicator = QFrame()
        self.indicator.setObjectName("sidebarNavIndicator")
        self.indicator.setProperty("active", False)
        self.indicator.setFixedWidth(3)
        row.addWidget(self.indicator)

        self.icon = QLabel(icon_text)
        self.icon.setObjectName("sidebarNavIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedWidth(22)
        row.addWidget(self.icon)

        self.text = QLabel(label_text)
        self.text.setObjectName("sidebarNavText")
        self.text.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )
        row.addWidget(self.text, 1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._refine_queued:
            return
        self._refine_queued = True
        QTimer.singleShot(0, self._refine_sidebar)

    def _refine_sidebar(self) -> None:
        parent = self.parentWidget()
        sidebar = parent
        while sidebar is not None and sidebar.objectName() != "sidebar":
            sidebar = sidebar.parentWidget()
        if sidebar is None:
            return

        window = sidebar.window()
        nav_buttons = getattr(window, "nav_buttons", {})
        rebuild_sidebar_layout(sidebar, nav_buttons)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_active(self, value: bool) -> None:
        value = bool(value)
        if value == self._active:
            return

        self._active = value
        self.setProperty("active", value)
        self.indicator.setProperty("active", value)
        self._repolish(self)
        self._repolish(self.indicator)
        self._repolish(self.icon)
        self._repolish(self.text)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
