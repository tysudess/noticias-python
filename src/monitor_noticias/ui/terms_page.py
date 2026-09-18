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

        row.addWidget(
            self._card(
                "▣", "Termos de Notícias", "Usados na varredura de matérias",
                self.news_list, controller.add_term, controller.remove_term, "blue"
            ),
            1,
        )

        add_video = getattr(controller, "add_video_term", lambda _value: None)
        remove_video = getattr(controller, "remove_video_term", lambda _value: None)

        row.addWidget(
            self._card(
                "▶", "Termos de Vídeos", "Lista independente para vídeos",
                self.video_list, add_video, remove_video, "purple"
            ),
            1,
        )

        self.setStyleSheet(self._stylesheet())

    def _card(self, icon_text, title, subtitle, listw, add_cb, remove_cb, tone):
        frame = QFrame()
        frame.setObjectName("termCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()

        icon = QLabel(icon_text)
        icon.setObjectName("termIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        head.addWidget(icon)

        text = QVBoxLayout()
        title_l = QLabel(title)
        title_l.setObjectName("termTitle")
        sub_l = QLabel(subtitle)
        sub_l.setObjectName("termSubtitle")
        text.addWidget(title_l)
        text.addWidget(sub_l)
        head.addLayout(text, 1)

        count = QLabel("0 termo(s)")
        count.setObjectName("termCount")
        head.addWidget(count)
        layout.addLayout(head)

        add_row = QHBoxLayout()
        edit = QLineEdit()
        edit.setObjectName("termInput")
        edit.setPlaceholderText("⌕  Novo termo")
        add_row.addWidget(edit, 1)

        add_button = QPushButton("+  Adicionar")
        add_button.setObjectName("termAdd")
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        listw.setObjectName("termList")
        listw.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        layout.addWidget(listw, 1)

        delete = QPushButton("▣  Excluir selecionado")
        delete.setObjectName("termDelete")
        layout.addWidget(delete, 0, Qt.AlignmentFlag.AlignRight)

        def add_term():
            value = edit.text().strip()
            if not value:
                return
            add_cb(value)
            edit.clear()

        add_button.clicked.connect(add_term)
        edit.returnPressed.connect(add_term)
        delete.clicked.connect(
            lambda: remove_cb(listw.currentItem().text())
            if listw.currentItem() else None
        )

        listw._count_label = count
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
        QScrollBar:vertical {
            background:#EDF4FB;
            width:9px;
            border-radius:4px;
        }
        QScrollBar::handle:vertical {
            background:#8EBBE8;
            min-height:42px;
            border-radius:4px;
        }
        """

    def refresh(self, state: UiState) -> None:
        self.news_list.clear()
        self.news_list.addItems(state.terms)

        videos = list(getattr(self.controller, "video_terms", []))
        self.video_list.clear()
        self.video_list.addItems(videos)

        self.news_list._count_label.setText(f"{len(state.terms)} termo(s)")
        self.video_list._count_label.setText(f"{len(videos)} termo(s)")
