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
/* V136 — navegação escura, limpa e funcional; dourado somente como acento. */
QFrame#sidebar {
    background:#071D31;
    border:0;
    border-right:1px solid #173750;
}

QFrame#sidebarBrandWrap {
    background:transparent;
    border:0;
}

QLabel#sidebarLogo {
    background:#D6B66D;
    color:#09243B;
    border:0;
    border-radius:10px;
    font-family:"Segoe UI";
    font-size:13px;
    font-weight:900;
}

QLabel#sidebarBrandTitle {
    color:#F4F7FA;
    background:transparent;
    border:0;
    font-size:14px;
    font-weight:800;
}

QLabel#sidebarBrandSub {
    color:#8FA9BD;
    background:transparent;
    border:0;
    font-size:8px;
    font-weight:700;
    letter-spacing:1px;
}

QLabel#sidebarGroupLabel {
    color:#7794AA;
    background:transparent;
    border:0;
    border-bottom:1px solid rgba(125,158,184,0.17);
    padding:8px 4px 6px 4px;
    font-size:8px;
    font-weight:800;
    letter-spacing:1.15px;
}

QFrame#sidebarNavItem {
    background:transparent;
    border:1px solid transparent;
    border-radius:9px;
}

QFrame#sidebarNavItem:hover {
    background:#0E2D46;
    border:1px solid rgba(120,160,190,0.12);
}

QFrame#sidebarNavItem:focus {
    border:1px solid #5F91B4;
}

QFrame#sidebarNavItem[active="true"] {
    background:#123B58;
    border:1px solid rgba(104,159,194,0.22);
}

QFrame#sidebarNavIndicator {
    background:transparent;
    border:0;
    border-radius:2px;
}

QFrame#sidebarNavIndicator[active="true"] {
    background:#D8B96F;
}

QFrame#sidebarNavIconWrap {
    background:rgba(135,169,194,0.09);
    border:0;
    border-radius:8px;
}

QFrame#sidebarNavItem:hover QFrame#sidebarNavIconWrap {
    background:rgba(123,171,205,0.15);
}

QFrame#sidebarNavItem[active="true"] QFrame#sidebarNavIconWrap {
    background:#D6B66D;
    border:0;
}

QLabel#sidebarNavIcon {
    color:#AFC3D2;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:15px;
    font-weight:700;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavIcon {
    color:#09243B;
}

QLabel#sidebarNavText {
    color:#D1DDE7;
    background:transparent;
    border:0;
    font-size:10px;
    font-weight:600;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavText {
    color:#FFFFFF;
    font-weight:800;
}

QLabel#sidebarNavCurrentMark {
    color:transparent;
    background:transparent;
    border:0;
    font-size:7px;
}

QFrame#sidebarNavItem[active="true"] QLabel#sidebarNavCurrentMark {
    color:#E2C477;
}

QFrame#sidebarStatusCard {
    background:#0A2941;
    border:1px solid #1D4058;
    border-radius:10px;
}

QLabel#sidebarStatusIcon {
    color:#56D6A5;
    background:transparent;
    border:0;
    font-family:"Segoe UI Symbol";
    font-size:13px;
    font-weight:900;
}

QLabel#sidebarStatusTitle {
    color:#8CA6BA;
    background:transparent;
    border:0;
    font-size:8px;
    font-weight:600;
}

QLabel#sidebarStatusText {
    color:#E6EEF4;
    background:transparent;
    border:0;
    font-size:9px;
    font-weight:700;
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
    width:4px;
    margin:2px 0 2px 0;
}

QScrollBar::handle:vertical {
    background:rgba(149,177,198,0.34);
    min-height:26px;
    border-radius:2px;
}

QScrollBar::handle:vertical:hover {
    background:rgba(214,182,109,0.75);
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

        status.setMinimumHeight(58)

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

        brand.setMinimumHeight(62)
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
        content_layout.setSpacing(4)

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
            heading.setMinimumHeight(23)
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
        self.setFixedHeight(42)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 10, 0)
        row.setSpacing(8)

        self.indicator = QFrame()
        self.indicator.setObjectName("sidebarNavIndicator")
        self.indicator.setProperty("active", False)
        self.indicator.setFixedWidth(3)
        row.addWidget(self.indicator)

        self.icon_wrap = QFrame()
        self.icon_wrap.setObjectName("sidebarNavIconWrap")
        self.icon_wrap.setFixedSize(28, 28)
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
