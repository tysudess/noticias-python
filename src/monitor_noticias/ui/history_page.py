from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QEvent, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QListView, QPushButton,
    QStyledItemDelegate, QStyleOptionViewItem,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage
from monitor_noticias.ui.url_tools import (
    copy_article_url, open_article_url, open_whatsapp,
)


def _time(ms: int) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


class HistoryModel(QAbstractListModel):
    EntryRole = Qt.ItemDataRole.UserRole + 1
    KindRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.rows = []
        self.kind = "news"
        self._signature = None

    def set_rows(self, rows, kind: str) -> None:
        rows = list(rows)

        signature = (
            kind,
            tuple(
                (
                    getattr(row, "id", 0),
                    getattr(row, "link", ""),
                    getattr(row, "date", getattr(row, "publishedAt", 0)),
                    getattr(row, "title", ""),
                )
                for row in rows
            ),
        )

        if signature == self._signature:
            return

        self.beginResetModel()
        self.rows = rows
        self.kind = kind
        self._signature = signature
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None

        row = self.rows[index.row()]

        if role == self.EntryRole:
            return row

        if role == self.KindRole:
            return self.kind

        if role == Qt.ItemDataRole.DisplayRole:
            return getattr(row, "title", "")

        return None


class HistoryDelegate(QStyledItemDelegate):
    ROW_H = 112
    BTN_W = 112
    BTN_H = 34
    GAP = 7

    @staticmethod
    def _rounded(painter, rect, fill, border, radius=9):
        painter.setBrush(QColor(fill))
        painter.setPen(QPen(QColor(border), 1))
        painter.drawRoundedRect(rect, radius, radius)

    def sizeHint(self, option, index) -> QSize:
        return QSize(1000, self.ROW_H)

    def _buttons(self, rect: QRect, kind: str) -> list[QRect]:
        count = 3 if kind == "news" else 2
        total = self.BTN_W * count + self.GAP * (count - 1)
        x = rect.right() - total - 14
        y = rect.top() + (rect.height() - self.BTN_H) // 2

        return [
            QRect(
                x + i * (self.BTN_W + self.GAP),
                y,
                self.BTN_W,
                self.BTN_H,
            )
            for i in range(count)
        ]

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        entry = index.data(HistoryModel.EntryRole)
        kind = index.data(HistoryModel.KindRole)

        if entry is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        card = option.rect.adjusted(2, 4, -4, -4)
        self._rounded(painter, card, "#FFFFFF", "#DCE9F6", 10)

        icon = QRect(card.left() + 14, card.top() + 20, 50, 50)

        if kind == "news":
            self._rounded(painter, icon, "#E7F3FF", "#E7F3FF", 10)
            painter.setPen(QColor("#087AF7"))
            icon_text = "▤"
        else:
            self._rounded(painter, icon, "#F0E8FF", "#F0E8FF", 10)
            painter.setPen(QColor("#7749F5"))
            icon_text = "▶"

        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(icon, Qt.AlignmentFlag.AlignCenter, icon_text)

        buttons = self._buttons(card, kind)
        text_left = icon.right() + 14
        text_right = buttons[0].left() - 16

        if kind == "news":
            source = getattr(entry, "source", "")
            stamp = getattr(entry, "date", 0)
        else:
            source = getattr(entry, "sourceName", "")
            stamp = getattr(entry, "publishedAt", 0)

        meta_rect = QRect(
            text_left,
            card.top() + 12,
            max(50, text_right - text_left),
            18,
        )

        title_rect = QRect(
            text_left,
            card.top() + 32,
            max(50, text_right - text_left),
            32,
        )

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#5272A1"))
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{source}  •  {_time(stamp)}",
        )

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.setPen(QColor("#08245F"))
        fm = QFontMetrics(painter.font())

        title = fm.elidedText(
            getattr(entry, "title", ""),
            Qt.TextElideMode.ElideRight,
            title_rect.width() * 2,
        )

        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
            | Qt.TextFlag.TextWordWrap,
            title,
        )

        if kind == "news":
            snippet_rect = QRect(
                text_left,
                card.top() + 65,
                max(50, text_right - text_left),
                20,
            )

            snippet = getattr(entry, "snippet", "") or ""

            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#6079A5"))
            painter.drawText(
                snippet_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                QFontMetrics(painter.font()).elidedText(
                    snippet,
                    Qt.TextElideMode.ElideRight,
                    snippet_rect.width(),
                ),
            )

            term = (
                getattr(entry, "matchedDemand", "")
                or getattr(entry, "matchedTerm", "")
                or ""
            ).strip()

            if term:
                tag = QRect(
                    text_left,
                    card.top() + 86,
                    min(170, max(90, len(term) * 7 + 24)),
                    18,
                )
                self._rounded(
                    painter,
                    tag,
                    "#EAF4FF",
                    "#EAF4FF",
                    5,
                )
                painter.setPen(QColor("#087AF7"))
                painter.setFont(
                    QFont("Segoe UI", 7, QFont.Weight.Bold)
                )
                painter.drawText(
                    tag.adjusted(6, 0, -6, 0),
                    Qt.AlignmentFlag.AlignCenter,
                    QFontMetrics(painter.font()).elidedText(
                        f"Termo: {term}",
                        Qt.TextElideMode.ElideRight,
                        tag.width() - 12,
                    ),
                )

        if kind == "news":
            specs = [
                ("↗ Abrir matéria", "#FFFFFF", "#C9DDF2", "#0C3974"),
                ("◉ WhatsApp", "#EAF9F2", "#BFE8D5", "#078B5F"),
                ("▣ Copiar link", "#FFFFFF", "#C9DDF2", "#0C3974"),
            ]
        else:
            specs = [
                ("↗ Abrir vídeo", "#FFFFFF", "#C9DDF2", "#0C3974"),
                ("▣ Copiar link", "#FFFFFF", "#C9DDF2", "#0C3974"),
            ]

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        for rect, (label, fill, border, color) in zip(buttons, specs):
            self._rounded(painter, rect, fill, border, 7)
            painter.setPen(QColor(color))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        painter.restore()

    def editorEvent(self, event, model, option, index) -> bool:
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False

        entry = index.data(HistoryModel.EntryRole)
        kind = index.data(HistoryModel.KindRole)

        if entry is None:
            return False

        point = (
            event.position().toPoint()
            if hasattr(event, "position")
            else event.pos()
        )

        card = option.rect.adjusted(2, 4, -4, -4)
        buttons = self._buttons(card, kind)

        for idx, rect in enumerate(buttons):
            if not rect.contains(point):
                continue

            if kind == "news":
                if idx == 0:
                    open_article_url(entry.link)
                elif idx == 1:
                    open_whatsapp(entry.title, entry.link)
                elif idx == 2:
                    copy_article_url(entry.link)
            else:
                if idx == 0:
                    open_article_url(entry.link)
                elif idx == 1:
                    copy_article_url(entry.link)

            return True

        return False


class HistoryPage(BasePage):
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)

        top = QFrame()
        top.setObjectName("historyTop")

        tl = QHBoxLayout(top)
        tl.setContentsMargins(10, 9, 10, 9)

        self.tabs = QButtonGroup(self)
        self.tabs.setExclusive(True)

        news = QPushButton("Notícias")
        news.setObjectName("historyTab")
        news.setCheckable(True)
        news.setChecked(True)

        videos = QPushButton("Vídeos")
        videos.setObjectName("historyTab")
        videos.setCheckable(True)

        self.tabs.addButton(news, 0)
        self.tabs.addButton(videos, 1)

        tl.addWidget(news)
        tl.addWidget(videos)
        tl.addStretch()

        self.clear = QPushButton("▣  Limpar histórico")
        self.clear.setObjectName("historyClear")
        tl.addWidget(self.clear)

        self.root.addWidget(top)

        self.model = HistoryModel(self)
        self.delegate = HistoryDelegate(self)

        self.list_view = QListView()
        self.list_view.setObjectName("historyListView")
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
        self.list_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.list_view.setSelectionMode(
            QListView.SelectionMode.NoSelection
        )
        self.list_view.setSpacing(0)

        self.root.addWidget(self.list_view, 1)

        self.tabs.idClicked.connect(
            lambda _: self.refresh(self.controller.state)
        )
        self.clear.clicked.connect(self._clear)

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#historyTop {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QPushButton#historyTab {
            background:#F8FBFF;
            color:#183E72;
            border:1px solid #D2E2F4;
            border-radius:8px;
            padding:9px 18px;
            min-width:120px;
            font-weight:800;
        }
        QPushButton#historyTab:checked {
            background:#0A7DF8;
            color:white;
            border-color:#0A7DF8;
        }
        QPushButton#historyClear {
            background:#FFF1F4;
            color:#E03155;
            border:1px solid #FFB8C8;
            border-radius:8px;
            padding:9px 14px;
            font-weight:800;
        }
        QListView#historyListView {
            background:transparent;
            border:0;
            outline:0;
        }
        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical {
            background:#82B5E8;
            min-height:48px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical:hover {
            background:#5F9EDB;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height:0;
        }
        """

    def _tab(self) -> int:
        value = self.tabs.checkedId()
        return 0 if value < 0 else value

    def _clear(self) -> None:
        if self._tab() == 0:
            self.controller.clear_news_history()
        else:
            self.controller.clear_video_history()

    def refresh(self, _state: UiState) -> None:
        if self._tab() == 0:
            self.model.set_rows(
                self.controller.news_db.listNews(1000),
                "news",
            )
        else:
            self.model.set_rows(
                self.controller.video_db.listAll(1000),
                "video",
            )
