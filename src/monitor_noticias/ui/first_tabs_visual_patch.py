from __future__ import annotations

from typing import Any
import re


_PATCHED = False
_STYLE_MARKER = "/* CENTRAL FIRST TABS VISUAL V117 */"


COMMON_FIRST_TABS_QSS = _STYLE_MARKER + r"""
/* Form controls: common height, focus state and contrast. */
QLineEdit,
QComboBox,
QDateEdit,
QTimeEdit,
QSpinBox,
QDoubleSpinBox,
QAbstractSpinBox {
    min-height: 32px;
    padding: 4px 10px;
    border: 1px solid #CFDFF0;
    border-radius: 8px;
    background: #FFFFFF;
    color: #153766;
    selection-background-color: #2D8CFF;
    selection-color: #FFFFFF;
}
QLineEdit:focus,
QComboBox:focus,
QDateEdit:focus,
QTimeEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QAbstractSpinBox:focus {
    border: 1px solid #2584F4;
    background: #FFFFFF;
}
QLineEdit:disabled,
QComboBox:disabled,
QDateEdit:disabled,
QTimeEdit:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled,
QAbstractSpinBox:disabled {
    color: #879AB5;
    background: #F0F4F9;
    border-color: #E0E8F2;
}

/* Consistent button rhythm without overriding semantic colors. */
QPushButton {
    min-height: 32px;
    padding: 5px 12px;
    border-radius: 8px;
    font-weight: 750;
}
QPushButton:disabled {
    color: #8B9DB5;
    background: #EEF3F9;
    border-color: #DCE6F1;
}
QPushButton#newsPrimary,
QPushButton#videoPrimary,
QPushButton#demandPrimary,
QPushButton#demandAdd,
QPushButton#quickTilePrimary {
    color: #FFFFFF;
    background: #0A7DF8;
    border: 1px solid #0872E3;
    border-radius: 8px;
    min-height: 34px;
    padding: 6px 14px;
    font-weight: 800;
}
QPushButton#newsPrimary:hover,
QPushButton#videoPrimary:hover,
QPushButton#demandPrimary:hover,
QPushButton#demandAdd:hover,
QPushButton#quickTilePrimary:hover {
    background: #238BFC;
    border-color: #147CEB;
}
QPushButton#newsPrimary:disabled,
QPushButton#videoPrimary:disabled,
QPushButton#demandPrimary:disabled,
QPushButton#demandAdd:disabled,
QPushButton#quickTilePrimary:disabled {
    color: #879AB5;
    background: #E7EFF8;
    border-color: #D7E3F1;
}
QPushButton#stopButton,
QPushButton#videoStop,
QPushButton#demandDelete {
    color: #C32845;
    background: #FFF4F6;
    border: 1px solid #F5C4CE;
}
QPushButton#stopButton:hover,
QPushButton#videoStop:hover,
QPushButton#demandDelete:hover {
    background: #FFE9EE;
    border-color: #EBAAB8;
}
QPushButton#periodButton,
QPushButton#videoPeriod,
QPushButton#customPeriod,
QPushButton#demandSearch {
    color: #16477F;
    background: #FFFFFF;
    border: 1px solid #CFDFF0;
}
QPushButton#periodButton:checked,
QPushButton#videoPeriod:checked,
QPushButton#customPeriod:checked {
    color: #FFFFFF;
    background: #0A7DF8;
    border-color: #0A7DF8;
}

/* Unified card geometry across Home, News, Videos and Demands. */
QFrame#metricCard,
QFrame#readyCard,
QFrame#heroCard,
QFrame#homeScheduleWide,
QFrame#newsBanner,
QFrame#newsCard,
QFrame#videoTop,
QFrame#videoProgressCard,
QFrame#demandHero,
QFrame#demandCard {
    border-radius: 12px;
    border-color: #D7E4F2;
}
QFrame#newsCard,
QFrame#videoItem,
QFrame#demandItem,
QFrame#rankRow {
    border-radius: 10px;
    border-color: #DCE7F3;
}

/* Predictable typographic hierarchy. */
QLabel#sectionTitle,
QLabel#newsTitle,
QLabel#newsListTitle,
QLabel#videoListTitle,
QLabel#demandListTitle,
QLabel#demandHeroTitle {
    color: #08285F;
    font-size: 16px;
    font-weight: 850;
}
QLabel#sectionSubtitle,
QLabel#newsSubtitle,
QLabel#newsMuted,
QLabel#videoMuted,
QLabel#demandMuted {
    color: #657D9E;
}
QLabel#metricTitle,
QLabel#videoMetricCaption,
QLabel#demandLabel {
    color: #355780;
    font-weight: 750;
}

/* Progress bars share a restrained, high-contrast treatment. */
QProgressBar#newsProgress,
QProgressBar#videoProgress,
QProgressBar#homeSearchProgress {
    min-height: 8px;
    max-height: 8px;
    border: 0;
    border-radius: 4px;
    background: #E8F0FA;
    text-align: center;
}
QProgressBar#newsProgress::chunk,
QProgressBar#videoProgress::chunk,
QProgressBar#homeSearchProgress::chunk {
    border-radius: 4px;
    background: #0A7DF8;
}

/* Consistent, quiet scrollbars. */
QScrollBar:vertical {
    width: 9px;
    margin: 0;
    border: 0;
    border-radius: 4px;
    background: #F0F5FB;
}
QScrollBar::handle:vertical {
    min-height: 30px;
    border-radius: 4px;
    background: #B7CDE6;
}
QScrollBar::handle:vertical:hover {
    background: #8FB1D9;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 9px;
    margin: 0;
    border: 0;
    border-radius: 4px;
    background: #F0F5FB;
}
QScrollBar::handle:horizontal {
    min-width: 30px;
    border-radius: 4px;
    background: #B7CDE6;
}

/* Execution status is semantic: blue=running, green=complete, amber=partial,
   red=failure, gray=cancelled or idle. */
QLabel[executionState="running"] { color: #126DCA; }
QLabel[executionState="completed"] { color: #087B52; }
QLabel[executionState="partial"] { color: #A96B00; }
QLabel[executionState="failure"] { color: #BE2946; }
QLabel[executionState="cancelled"] { color: #687B94; }
QLabel[executionState="idle"] { color: #264A78; }
"""


def responsive_news_button_width(
    card_width: int,
    *,
    preferred: int = 112,
    minimum: int = 78,
    gap: int = 6,
) -> int:
    """Choose a button width that preserves title space on narrower windows."""
    width = max(1, int(card_width))
    left_content_reserve = max(210, int(width * 0.37))
    available = width - left_content_reserve - 20
    fitted = (available - gap * 3) // 4
    return max(minimum, min(preferred, fitted))


def _execution_state(status: str, busy: bool, progress: Any = None, unstable=()) -> str:
    if busy:
        return "running"
    text = str(status or "").strip().casefold()
    if any(token in text for token in ("interrompid", "cancelad", "cancelamento")):
        return "cancelled"
    if text.startswith(("falha", "erro")) or "falha na busca" in text or "timeout" in text or "timed out" in text:
        return "failure"
    if int(getattr(progress, "errors", 0) or 0) > 0 or tuple(unstable or ()):
        return "partial"
    if re.search(r"\b([1-9]\d*)\s+(?:falha|falhas|erro|erros)\b", text):
        return "partial"
    if any(token in text for token in ("concluída com falhas", "concluida com falhas")):
        return "partial"
    if text and ("✓" in text or "conclu" in text):
        return "completed"
    return "idle"


def _refresh_style(widget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _set_execution_property(widget, value: str) -> None:
    if widget is None:
        return
    if widget.property("executionState") == value:
        return
    widget.setProperty("executionState", value)
    _refresh_style(widget)


def _append_stylesheet(page) -> None:
    current = str(page.styleSheet() or "")
    if _STYLE_MARKER not in current:
        page.setStyleSheet(current + "\n" + COMMON_FIRST_TABS_QSS)


def _normalize_layout(page, kind: str) -> None:
    root = getattr(page, "root", None)
    if root is not None:
        root.setSpacing(10)
        # The same outer padding gives all four tabs the same card alignment.
        if kind == "home":
            root.setContentsMargins(12, 10, 12, 10)
        else:
            root.setContentsMargins(10, 10, 10, 10)

    try:
        from PySide6.QtWidgets import QListView, QScrollArea, QFrame
        for view in page.findChildren(QListView):
            view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        for scroll in page.findChildren(QScrollArea):
            scroll.setFrameShape(QFrame.Shape.NoFrame)
    except (ImportError, AttributeError):
        pass

    # Keep action groups readable on smaller desktop resolutions.
    try:
        from PySide6.QtWidgets import QPushButton, QSizePolicy
        for button in page.findChildren(QPushButton):
            if button.objectName() in {"videoAction", "videoWhats"}:
                button.setMinimumWidth(78)
                button.setMaximumWidth(110)
                button.setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed,
                )
    except (ImportError, AttributeError):
        pass


def install_first_tabs_visual_patch() -> None:
    """Apply a shared visual system to the first four tabs, preserving actions."""
    global _PATCHED
    if _PATCHED:
        return

    from PySide6.QtCore import QRect
    from monitor_noticias.ui.home_page import HomePage
    from monitor_noticias.ui.news_page import NewsPage, NewsDelegate
    from monitor_noticias.ui.videos_page import VideosPage
    from monitor_noticias.ui.demands_page import DemandsPage

    def wrap_init(cls, kind: str) -> None:
        original = cls.__init__

        def styled_init(self, *args, **kwargs):
            original(self, *args, **kwargs)
            if getattr(self, "_v117_visual_installed", False):
                return
            _normalize_layout(self, kind)
            _append_stylesheet(self)
            self._v117_visual_installed = True

        cls.__init__ = styled_init

    wrap_init(HomePage, "home")
    wrap_init(NewsPage, "news")
    wrap_init(VideosPage, "videos")
    wrap_init(DemandsPage, "demands")

    # The News delegate paints its action buttons manually, so the regular
    # stylesheet cannot make them responsive. Reuse its four existing actions
    # but calculate their widths from the card width to prevent clipping.
    original_buttons = NewsDelegate._buttons

    def responsive_buttons(self, rect):
        width = responsive_news_button_width(rect.width(), preferred=self.BTN_W, minimum=78, gap=self.GAP)
        total = width * 4 + self.GAP * 3
        x = rect.right() - total - 10
        y = rect.top() + (rect.height() - self.BTN_H) // 2
        return [
            QRect(x + index * (width + self.GAP), y, width, self.BTN_H)
            for index in range(4)
        ]

    responsive_buttons._v117_responsive_buttons = True
    NewsDelegate._buttons = responsive_buttons

    # Wrap refresh methods AFTER V115/V116 so status tint follows the final
    # state produced by the functional and performance corrections.
    original_home_refresh = HomePage.refresh
    original_news_refresh = NewsPage.refresh
    original_video_refresh = VideosPage.refresh
    original_demands_refresh = DemandsPage.refresh

    def home_refresh(self, state):
        original_home_refresh(self, state)
        news_state = _execution_state(
            state.status,
            bool(state.news_busy),
            getattr(state, "news_progress", None),
        )
        video_state = _execution_state(
            state.video_status,
            bool(state.video_busy),
            getattr(state, "video_progress", None),
            getattr(state, "unstable_video_sources", ()),
        )
        if "failure" in (news_state, video_state):
            aggregate = "failure"
        elif "partial" in (news_state, video_state):
            aggregate = "partial"
        elif "running" in (news_state, video_state):
            aggregate = "running"
        elif "cancelled" in (news_state, video_state):
            aggregate = "cancelled"
        elif "completed" in (news_state, video_state):
            aggregate = "completed"
        else:
            aggregate = "idle"
        _set_execution_property(getattr(self, "ready_title", None), aggregate)
        _set_execution_property(getattr(self, "search_progress_title", None), aggregate)

    def news_refresh(self, state):
        original_news_refresh(self, state)
        current = _execution_state(
            state.status,
            bool(state.news_busy),
            getattr(state, "news_progress", None),
        )
        _set_execution_property(getattr(self, "exec_title", None), current)
        _set_execution_property(getattr(self, "exec_pct", None), current)

    def video_refresh(self, state):
        original_video_refresh(self, state)
        current = _execution_state(
            state.video_status,
            bool(state.video_busy),
            getattr(state, "video_progress", None),
            getattr(state, "unstable_video_sources", ()),
        )
        _set_execution_property(getattr(self, "exec_title", None), current)

    def demands_refresh(self, state):
        original_demands_refresh(self, state)
        current = _execution_state(
            state.status,
            bool(state.news_busy),
            getattr(state, "news_progress", None),
        )
        _set_execution_property(getattr(self, "status_title", None), current)

    HomePage.refresh = home_refresh
    NewsPage.refresh = news_refresh
    VideosPage.refresh = video_refresh
    DemandsPage.refresh = demands_refresh
    _PATCHED = True
