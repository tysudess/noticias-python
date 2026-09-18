from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage
from monitor_noticias.ui.url_tools import copy_article_url, open_article_url, open_whatsapp


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

        self.news_tab = QPushButton("Notícias")
        self.news_tab.setObjectName("historyTab")
        self.news_tab.setCheckable(True)
        self.news_tab.setChecked(True)

        self.video_tab = QPushButton("Vídeos")
        self.video_tab.setObjectName("historyTab")
        self.video_tab.setCheckable(True)

        self.tabs.addButton(self.news_tab, 0)
        self.tabs.addButton(self.video_tab, 1)

        tl.addWidget(self.news_tab)
        tl.addWidget(self.video_tab)
        tl.addStretch()

        self.clear = QPushButton("▣  Limpar histórico")
        self.clear.setObjectName("historyClear")
        tl.addWidget(self.clear)

        self.root.addWidget(top)

        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.setSpacing(7)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.root.addWidget(self.list, 1)

        self.tabs.idClicked.connect(lambda _: self.refresh(self.controller.state))
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

    def _button(self, text: str, style: str, fn):
        button = QPushButton(text)
        button.setStyleSheet(
            style + "border-radius:7px;padding:8px 11px;font-weight:700;"
        )
        button.clicked.connect(fn)
        return button

    def _add_news(self, news) -> None:
        item = QListWidgetItem()

        card = QFrame()
        card.setMinimumHeight(94)
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
        title.setStyleSheet("color:#08245F;font-size:11px;font-weight:900;")

        snippet = QLabel(getattr(news, "snippet", "") or "")
        snippet.setWordWrap(True)
        snippet.setStyleSheet("color:#6079A5;font-size:9px;")

        text.addWidget(meta)
        text.addWidget(title)

        if snippet.text().strip():
            text.addWidget(snippet)

        term = " • ".join(
            value
            for value in (
                getattr(news, "matchedTerm", ""),
                getattr(news, "matchedDemand", ""),
            )
            if value
        )

        if term:
            tag = QLabel(f"Termo: {term}")
            tag.setStyleSheet(
                "background:#EAF4FF;color:#087AF7;border-radius:6px;"
                "padding:4px 8px;font-size:8px;font-weight:800;"
            )
            text.addWidget(tag, 0, Qt.AlignmentFlag.AlignLeft)

        row.addLayout(text, 1)

        row.addWidget(self._button(
            "↗  Abrir matéria",
            "background:white;color:#0C3974;border:1px solid #C9DDF2;",
            lambda: open_article_url(news.link),
        ))
        row.addWidget(self._button(
            "◉  WhatsApp",
            "background:#EAF9F2;color:#078B5F;border:1px solid #BFE8D5;",
            lambda: open_whatsapp(news.title, news.link),
        ))
        row.addWidget(self._button(
            "▣  Copiar link",
            "background:white;color:#0C3974;border:1px solid #C9DDF2;",
            lambda: copy_article_url(news.link),
        ))

        item.setSizeHint(card.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, card)

    def _add_video(self, video) -> None:
        item = QListWidgetItem()

        card = QFrame()
        card.setMinimumHeight(82)
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
        meta = QLabel(f"{video.sourceName}  •  {_time(video.publishedAt)}")
        meta.setStyleSheet("color:#5D79A7;font-size:9px;")
        title = QLabel(video.title)
        title.setWordWrap(True)
        title.setStyleSheet("color:#08245F;font-size:11px;font-weight:900;")

        text.addWidget(meta)
        text.addWidget(title)
        row.addLayout(text, 1)

        row.addWidget(self._button(
            "↗  Abrir vídeo",
            "background:white;color:#0C3974;border:1px solid #C9DDF2;",
            lambda: open_article_url(video.link),
        ))
        row.addWidget(self._button(
            "▣  Copiar link",
            "background:white;color:#0C3974;border:1px solid #C9DDF2;",
            lambda: copy_article_url(video.link),
        ))

        item.setSizeHint(card.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, card)

    def refresh(self, _state: UiState) -> None:
        self.list.clear()

        if self._tab() == 0:
            for news in self.controller.news_db.listNews(2000):
                self._add_news(news)
        else:
            for video in self.controller.video_db.listAll(2000):
                self._add_video(video)
