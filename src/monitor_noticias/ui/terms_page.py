from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


class TermsPage(BasePage):
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(12)
        self.root.addLayout(row, 1)

        self.news_list = QListWidget()
        self.video_list = QListWidget()

        self.news_count = QLabel()
        self.video_count = QLabel()

        row.addWidget(
            self._card(
                "▣",
                "Termos de Notícias",
                "Usados na varredura de matérias",
                self.news_list,
                self.news_count,
                self._add_news,
                self._remove_news,
                "blue",
            ),
            1,
        )

        row.addWidget(
            self._card(
                "▶",
                "Termos de Vídeos",
                "Lista independente para vídeos",
                self.video_list,
                self.video_count,
                self._add_video,
                self._remove_video,
                "purple",
            ),
            1,
        )

        self.setStyleSheet(self._stylesheet())

    def _video_terms(self) -> list[str]:
        default = set(self.controller.state.terms)
        values = self.controller.prefs.get_string_set(
            "desktop_video_terms",
            default,
        )
        return sorted(values or set(), key=str.casefold)

    def _add_news(self, value: str) -> None:
        self.controller.add_term(value)

    def _remove_news(self, value: str) -> None:
        self.controller.remove_term(value)

    def _add_video(self, value: str) -> None:
        terms = set(self._video_terms())
        terms.add(value.strip())
        self.controller.prefs.update(
            desktop_video_terms=terms
        )
        self.controller.refresh()

    def _remove_video(self, value: str) -> None:
        terms = set(self._video_terms())
        terms.discard(value)
        self.controller.prefs.update(
            desktop_video_terms=terms
        )
        self.controller.refresh()

    def _card(
        self,
        icon_text,
        title_text,
        subtitle_text,
        listw,
        count_label,
        add_cb,
        remove_cb,
        tone,
    ):
        frame = QFrame()
        frame.setObjectName("termCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()

        icon = QLabel(icon_text)
        icon.setObjectName("termIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        header.addWidget(icon)

        text = QVBoxLayout()

        title = QLabel(title_text)
        title.setObjectName("termTitle")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("termSubtitle")

        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text, 1)

        count_label.setObjectName("termCount")
        header.addWidget(count_label)

        layout.addLayout(header)

        add_row = QHBoxLayout()

        edit = QLineEdit()
        edit.setObjectName("termInput")
        edit.setPlaceholderText("⌕  Novo termo")
        add_row.addWidget(edit, 1)

        add = QPushButton("+  Adicionar")
        add.setObjectName("termAdd")
        add_row.addWidget(add)

        layout.addLayout(add_row)

        listw.setObjectName("termList")
        listw.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )
        layout.addWidget(listw, 1)

        delete = QPushButton("▣  Excluir selecionado")
        delete.setObjectName("termDelete")
        layout.addWidget(
            delete,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        def add_value():
            value = edit.text().strip()
            if value:
                add_cb(value)
                edit.clear()

        add.clicked.connect(add_value)
        edit.returnPressed.connect(add_value)

        delete.clicked.connect(
            lambda: remove_cb(
                listw.currentItem().text()
            )
            if listw.currentItem()
            else None
        )

        return frame

    def _stylesheet(self) -> str:
        return """
        QFrame#termCard {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QLabel#termIcon {
            border-radius:12px;
            font-size:22px;
            font-weight:900;
        }
        QLabel#termIcon[tone='blue'] {
            background:#E5F1FF;
            color:#087AF7;
        }
        QLabel#termIcon[tone='purple'] {
            background:#F0E4FF;
            color:#8244F5;
        }
        QLabel#termTitle {
            color:#08245F;
            font-size:18px;
            font-weight:900;
        }
        QLabel#termSubtitle {
            color:#6079A5;
            font-size:10px;
        }
        QLabel#termCount {
            background:#EAF4FF;
            color:#087AF7;
            border-radius:8px;
            padding:10px 14px;
            font-size:10px;
            font-weight:800;
        }
        QLineEdit#termInput {
            min-height:34px;
            padding:0 10px;
        }
        QPushButton#termAdd {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:8px 14px;
            font-weight:800;
        }
        QListWidget#termList {
            background:transparent;
            border:0;
            outline:0;
        }
        QListWidget#termList::item {
            background:#F8FBFF;
            color:#183E72;
            border:1px solid #D8E7F6;
            border-radius:7px;
            padding:7px 10px;
            margin-bottom:4px;
        }
        QListWidget#termList::item:selected {
            background:#EAF4FF;
            color:#087AF7;
            border-color:#8ABDF0;
        }
        QPushButton#termDelete {
            background:#FFF1F4;
            color:#E03155;
            border:1px solid #FFB8C8;
            border-radius:8px;
            padding:8px 13px;
            font-weight:800;
        }
        """

    def refresh(self, state: UiState) -> None:
        self.news_list.clear()
        self.news_list.addItems(state.terms)

        video_terms = self._video_terms()

        self.video_list.clear()
        self.video_list.addItems(video_terms)

        self.news_count.setText(
            f"{len(state.terms)} termo(s)"
        )
        self.video_count.setText(
            f"{len(video_terms)} termo(s)"
        )
