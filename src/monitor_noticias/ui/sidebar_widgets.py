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
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0A355C,
        stop:0.48 #082A4A,
        stop:1 #041B31
    );
    border:0;
    border-right:1px solid #B0904F;
}

QFrame#sidebarBrandWrap {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(25,76,112,0.92),
        stop:1 rgba(8,39,67,0.96)
    );
    border:1px solid rgba(218,187,112,0.62);
    border-left:3px solid #D8B765;
    border-radius:14px;
}

QLabel#sidebarLogo {
    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #F0D891,
        stop:1 #C49A4E
    );
    color:#082746;
    border:1px solid #F7E7B8;
    border-radius:12px;
    font-family:"Segoe UI";
    font-size:14px;
    font-weight:900;
}

QLabel#sidebarBrandTitle {
    color:#FFFFFF;
    background:transparent;
    border:0;
    font-size:14px;
    font-weight:900;
}

QLabel#sidebarBrandSub {
    color:#E4C77F;
    background:transparent;
    border:0;
    font-size:9px;
    font-weight:700;
}

QLabel#sidebarGroupLabel {
    color:#D6B86E;
    background:transparent;
    border:0;
    border-left:2px solid #B9944D;
    border-bottom:1px solid rgba(198,161,91,0.26);
    padding:8px 5px 5px 8px;
    font-size:9px;
    font-weight:900;
    letter-spacing:1.25px;
}

QFrame#sidebarNavItem {
    background:rgba(255,255,255,0.035);
    border:1px solid rgba(150,183,210,0.20);
    border-radius:12px;
}

QFrame#sidebarNavItem:hover {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(45,112,164,0.42),
        stop:1 rgba(24,75,119,0.40)
    );
    border:1px solid rgba(218,187,112,0.76);
}

QFrame#sidebarNavItem:focus {
    border:1px solid #F0D891;
}

QFrame#sidebarNavItem[active="true"] {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #1D5A86,
        stop:0.58 #164A73,
        stop:1 #103B61
    );
    border:1px solid #D8B765;
}

QFrame#sidebarNavIndicator {
    background:transparent;
    border:0;
    border-radius:2px;
}

QFrame#sidebarNavIndicator[active="true"] {
    background:#F0D891;
}

QFrame#sidebarNavIconWrap {
    background:rgba(105,151,186,0.15);
    border:1px solid rgba(158,190,216,0.18);
    border-radius:9px;
}

QFrame#sidebarNavItem:hover QFrame#sidebarNavIconWrap {
    background:rgba(108,162,204,0.22);
    border:1px solid rgba(211,185,120,0.35);
}

QFrame#sidebarNavItem[active="true"] QFrame#sidebarNavIconWrap {
    background:qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #F0D891,
        stop:1 #C9A45B
    );
    border:1px solid #F4E2AC;
}

QLabel#sidebarNavIcon {
    color:#D3E0EC;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:15px;
    font-weight:800;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavIcon {
    color:#082B4B;
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
    font-weight:900;
}

QLabel#sidebarNavCurrentMark {
    color:transparent;
    background:transparent;
    border:0;
    font-size:10px;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavCurrentMark {
    color:#F0D891;
}

QFrame#sidebarStatusCard {
    background:qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(26,75,111,0.82),
        stop:1 rgba(8,39,66,0.92)
    );
    border:1px solid rgba(211,180,105,0.58);
    border-left:3px solid #C6A15B;
    border-radius:12px;
}

QLabel#sidebarStatusIcon {
    color:#F0D891;
    background:rgba(5,31,53,0.72);
    border:1px solid rgba(218,187,112,0.72);
    border-radius:12px;
    font-family:"Segoe UI Symbol";
    font-size:11px;
    font-weight:900;
}

QLabel#sidebarStatusTitle {
    color:#B8CADD;
    background:transparent;
    border:0;
    font-size:9px;
    font-weight:700;
}

QLabel#sidebarStatusText {
    color:#F5E5BC;
    background:transparent;
    border:0;
    font-size:10px;
    font-weight:800;
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
        (
            "NEWS_EXTRACTOR",
            "COVERS",
            "PDF_EDITOR",
            "EXTRACTOR",
            "VIDEO_EDITOR",
            "SCREEN_RECORDER",
        ),
    ),
    ("SISTEMA", ("ADMINISTRATION", "SETTINGS")),
)

_EXTRA_NAV_ITEMS = (
    (
        "SCREEN_RECORDER",
        "screen_recorder_nav",
        "Gravador de Tela",
        "Grave a tela inteira ou uma área personalizada em MP4.",
    ),
    (
        "ADMINISTRATION",
        "_admin_users_button",
        "Administração",
        "Cadastro de usuários e redefinição segura de senhas.",
    ),
)


def rebuild_sidebar_layout(
    sidebar: QFrame,
    nav_buttons: Mapping[object, "SidebarNavItem"],
    extra_items: Mapping[str, "SidebarNavItem"] | None = None,
) -> bool:
    """Reorganiza a barra sem descartar itens adicionados por integrações.

    Além das seções principais, a janela pode adicionar o Gravador de Tela e
    Administração dinamicamente. Esses itens precisam entrar no novo layout;
    deixá-los como filhos soltos da sidebar faz o Qt manter suas geometrias
    antigas, causando sobreposição com os botões reorganizados.
    """
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
            status_icon.setFixedSize(26, 26)
            status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status.setMinimumHeight(62)

        window = sidebar.window()
        discovered_extras = {
            key: getattr(window, attribute, None)
            for key, attribute, _label, _tooltip in _EXTRA_NAV_ITEMS
        }
        discovered_extras = {
            key: item
            for key, item in discovered_extras.items()
            if isinstance(item, SidebarNavItem)
        }
        if extra_items:
            discovered_extras.update(
                {
                    key: item
                    for key, item in extra_items.items()
                    if isinstance(item, SidebarNavItem)
                }
            )

        # Constrói um registro uniforme para seções comuns e navegação extra.
        by_name = {
            section.name: (
                section.value.label,
                section.value.subtitle,
                button,
            )
            for section, button in nav_buttons.items()
        }
        for key, _attribute, label, tooltip in _EXTRA_NAV_ITEMS:
            button = discovered_extras.get(key)
            if button is not None:
                by_name[key] = (label, tooltip, button)

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

        for group_label, section_names in _GROUPS:
            group_items = [
                (name, *by_name[name])
                for name in section_names
                if name in by_name
            ]
            if not group_items:
                continue

            heading = QLabel(group_label)
            heading.setObjectName("sidebarGroupLabel")
            heading.setMinimumHeight(25)
            content_layout.addWidget(heading)

            for _name, label, tooltip, button in group_items:
                button.setToolTip(tooltip)
                button.setAccessibleName(label)
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
        self.setFixedHeight(44)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(9, 0, 10, 0)
        row.setSpacing(9)

        self.indicator = QFrame()
        self.indicator.setObjectName("sidebarNavIndicator")
        self.indicator.setProperty("active", False)
        self.indicator.setFixedWidth(3)
        row.addWidget(self.indicator)

        self.icon_wrap = QFrame()
        self.icon_wrap.setObjectName("sidebarNavIconWrap")
        self.icon_wrap.setFixedSize(31, 31)
        icon_layout = QHBoxLayout(self.icon_wrap)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        self.icon = QLabel(icon_text)
        self.icon.setObjectName("sidebarNavIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon)
        row.addWidget(self.icon_wrap)

        self.text = QLabel(label_text)
        self.text.setObjectName("sidebarNavText")
        self.text.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )
        row.addWidget(self.text, 1)

        self.current_mark = QLabel("●")
        self.current_mark.setObjectName("sidebarNavCurrentMark")
        self.current_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_mark.setFixedWidth(10)
        row.addWidget(self.current_mark)

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
        self._repolish(self.icon_wrap)
        self._repolish(self.icon)
        self._repolish(self.text)
        self._repolish(self.current_mark)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
