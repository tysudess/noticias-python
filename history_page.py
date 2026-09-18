from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
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

        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.setSpacing(7)
        self.list.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )
        self.list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.root.addWidget(self.list, 1)

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
        QListWidget#historyList {
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

    def _news_card(self, news):
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:white;border:1px solid #DCE9F6;border-radius:10px;}"
            "QLabel{border:0;background:transparent;}"
        )

        row = QHBoxLayout(card)
        row.setContentsMargins(13, 9, 13, 9)
        row.setSpacing(11)

        icon = QLabel("▤")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(50, 50)
        icon.setStyleSheet(
            "background:#E7F3FF;color:#087AF7;border-radius:10px;"
            "font-size:20px;font-weight:900;"
        )
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)

        meta = QLabel(f"{news.source}  •  {_time(news.date)}")
        meta.setStyleSheet("color:#5D79A7;font-size:9px;")

        title = QLabel(news.title)
        title.setWordWrap(True)
        title.setStyleSheet(
            "color:#08245F;font-size:11px;font-weight:900;"
        )

        snippet = QLabel(getattr(news, "snippet", "") or "")
        snippet.setWordWrap(True)
        snippet.setStyleSheet("color:#6079A5;font-size:9px;")

        term = " • ".join(
            value
            for value in (
                getattr(news, "matchedTerm", ""),
                getattr(news, "matchedDemand", ""),
            )
            if value
        )

        text.addWidget(meta)
        text.addWidget(title)

        if snippet.text().strip():
            text.addWidget(snippet)

        if term:
            tag = QLabel(f"Termo: {term}")
            tag.setStyleSheet(
                "background:#EAF4FF;color:#087AF7;border-radius:6px;"
                "padding:4px 8px;font-size:8px;font-weight:800;"
            )
            text.addWidget(tag, 0, Qt.AlignmentFlag.AlignLeft)

        row.addLayout(text, 1)

        actions = (
            ("↗  Abrir matéria", lambda: open_article_url(news.link)),
            ("◉  WhatsApp", lambda: open_whatsapp(news.title, news.link)),
            ("▣  Copiar link", lambda: copy_article_url(news.link)),
        )

        for label, callback in actions:
            button = QPushButton(label)
            button.setStyleSheet(
                "background:white;color:#0C3974;border:1px solid #C9DDF2;"
                "border-radius:7px;padding:8px 11px;font-weight:700;"
            )
            if "WhatsApp" in label:
                button.setStyleSheet(
                    "background:#EAF9F2;color:#078B5F;border:1px solid #BFE8D5;"
                    "border-radius:7px;padding:8px 11px;font-weight:700;"
                )
            button.clicked.connect(callback)
            row.addWidget(button)

        return card

    def _video_card(self, video):
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:white;border:1px solid #DCE9F6;border-radius:10px;}"
            "QLabel{border:0;background:transparent;}"
        )

        row = QHBoxLayout(card)
        row.setContentsMargins(13, 9, 13, 9)
        row.setSpacing(11)

        icon = QLabel("▶")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(50, 50)
        icon.setStyleSheet(
            "background:#F0E8FF;color:#7749F5;border-radius:10px;"
            "font-size:20px;font-weight:900;"
        )
        row.addWidget(icon)

        text = QVBoxLayout()

        meta = QLabel(
            f"{video.sourceName}  •  {_time(video.publishedAt)}"
        )
        meta.setStyleSheet("color:#5D79A7;font-size:9px;")

        title = QLabel(video.title)
        title.setWordWrap(True)
        title.setStyleSheet(
            "color:#08245F;font-size:11px;font-weight:900;"
        )

        text.addWidget(meta)
        text.addWidget(title)
        row.addLayout(text, 1)

        for label, callback in (
            ("↗  Abrir vídeo", lambda: open_article_url(video.link)),
            ("▣  Copiar link", lambda: copy_article_url(video.link)),
        ):
            button = QPushButton(label)
            button.setStyleSheet(
                "background:white;color:#0C3974;border:1px solid #C9DDF2;"
                "border-radius:7px;padding:8px 11px;font-weight:700;"
            )
            button.clicked.connect(callback)
            row.addWidget(button)

        return card

    def refresh(self, _state: UiState) -> None:
        self.list.clear()

        if self._tab() == 0:
            rows = self.controller.news_db.listNews(500)

            for news in rows:
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 96))
                self.list.addItem(item)
                self.list.setItemWidget(
                    item,
                    self._news_card(news),
                )
        else:
            rows = self.controller.video_db.listAll(500)

            for video in rows:
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 86))
                self.list.addItem(item)
                self.list.setItemWidget(
                    item,
                    self._video_card(video),
                )
