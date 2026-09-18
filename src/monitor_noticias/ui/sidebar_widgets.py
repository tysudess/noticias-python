from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)


SIDEBAR_STYLE = """
QFrame#sidebar {
    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #082F70,
        stop:0.52 #06285F,
        stop:1 #041D49
    );
    border:0;
    border-right:1px solid #0A397D;
}

QFrame#sidebarBrandWrap {
    background:transparent;
    border:0;
}

QLabel#sidebarLogo {
    background:#F3C84D;
    color:#082B64;
    border:1px solid #FFD864;
    border-radius:9px;
    font-family:"Segoe UI Symbol";
    font-size:20px;
    font-weight:900;
}

QLabel#sidebarBrandTitle {
    color:#FFFFFF;
    background:transparent;
    border:0;
    font-size:13px;
    font-weight:900;
}

QLabel#sidebarBrandSub {
    color:#AFC5E7;
    background:transparent;
    border:0;
    font-size:8px;
}

QFrame#sidebarNavItem {
    background:transparent;
    border:0;
    border-radius:8px;
}

QFrame#sidebarNavItem:hover {
    background:rgba(21, 91, 173, 0.42);
}

QFrame#sidebarNavItem[active="true"] {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #0B74EE,
        stop:0.72 #0758C7,
        stop:1 #07469D
    );
    border:1px solid rgba(68, 161, 255, 0.28);
}

QFrame#sidebarNavIndicator {
    background:transparent;
    border:0;
    border-radius:2px;
}

QFrame#sidebarNavIndicator[active="true"] {
    background:#37BEFF;
}

QLabel#sidebarNavIcon {
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:15px;
    font-weight:900;
}

QLabel#sidebarNavText {
    background:transparent;
    border:0;
    color:#F5F9FF;
    font-size:9px;
    font-weight:700;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavText {
    color:#FFFFFF;
    font-weight:800;
}

QLabel#sidebarNavChevron {
    background:transparent;
    border:0;
    color:#6388BC;
    font-family:"Segoe UI Symbol";
    font-size:13px;
    font-weight:700;
}

QFrame#sidebarNavItem:hover QLabel#sidebarNavChevron,
QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavChevron {
    color:#CDE6FF;
}

QFrame#sidebarStatusCard {
    background:rgba(13, 63, 125, 0.52);
    border:1px solid rgba(71, 127, 196, 0.24);
    border-radius:8px;
}

QLabel#sidebarStatusIcon {
    color:#6E94C9;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:16px;
}

QLabel#sidebarStatusTitle {
    color:#8FA9CE;
    background:transparent;
    border:0;
    font-size:7px;
}

QLabel#sidebarStatusText {
    color:#E7F0FF;
    background:transparent;
    border:0;
    font-size:7px;
}
"""


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
        self._icon_color = icon_color

        self.setObjectName("sidebarNavItem")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 8, 0)
        row.setSpacing(7)

        self.indicator = QFrame()
        self.indicator.setObjectName("sidebarNavIndicator")
        self.indicator.setProperty("active", False)
        self.indicator.setFixedWidth(3)
        row.addWidget(self.indicator)

        self.icon = QLabel(icon_text)
        self.icon.setObjectName("sidebarNavIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedWidth(20)
        self.icon.setStyleSheet(
            f"color:{icon_color};background:transparent;border:0;"
        )
        row.addWidget(self.icon)

        self.text = QLabel(label_text)
        self.text.setObjectName("sidebarNavText")
        self.text.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )
        row.addWidget(self.text, 1)

        self.chevron = QLabel("›")
        self.chevron.setObjectName("sidebarNavChevron")
        self.chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chevron.setFixedWidth(12)
        row.addWidget(self.chevron)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_active(self, value: bool) -> None:
        value = bool(value)

        if value == self._active:
            return

        self._active = value
        self.setProperty("active", value)
        self.indicator.setProperty("active", value)

        self._repolish(self)
        self._repolish(self.indicator)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
