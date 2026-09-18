from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.extractor import EXTRACTOR_QUALITIES
from monitor_noticias.ui.extractor_page import ExtractorPage


class ReferenceExtractorPage(ExtractorPage):
    """Mesmo motor do Extrator de Vídeos, com organização visual final."""

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 2, 4, 4)
        root.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("extractorHero")

        hl = QHBoxLayout(hero)
        hl.setContentsMargins(16, 12, 16, 12)

        text = QVBoxLayout()
        text.setSpacing(2)

        title = QLabel("Extrator de Vídeos")
        title.setObjectName("extractorTitle")

        subtitle = QLabel(
            "Download direto com seleção de qualidade, "
            "histórico local e sessão Globoplay protegida."
        )
        subtitle.setObjectName("extractorMuted")

        text.addWidget(title)
        text.addWidget(subtitle)

        hl.addLayout(text, 1)

        badge = QLabel("Windows Portable v3.0.1")
        badge.setObjectName("extractorBadge")
        hl.addWidget(badge)

        root.addWidget(hero)

        self.tabs = QTabBar()
        self.tabs.setObjectName("extractorTabs")

        for label in (
            "Download",
            "Histórico",
            "Configurações",
        ):
            self.tabs.addTab(label)

        self.tabs.currentChanged.connect(
            self._switch_tab
        )
        root.addWidget(self.tabs)

        self.stack = QStackedWidget()
        self.stack.setObjectName("extractorStack")

        self.stack.addWidget(
            self._build_download_tab()
        )
        self.stack.addWidget(
            self._build_history_tab()
        )
        self.stack.addWidget(
            self._build_settings_tab()
        )

        root.addWidget(self.stack, 1)

        self.setStyleSheet(
            """
            QFrame#extractorHero,
            QFrame#extractorCard,
            QFrame#extractorStatusCard {
                background:#FFFFFF;
                border:1px solid #D4E4F5;
                border-radius:12px;
            }

            QLabel#extractorTitle {
                color:#08245F;
                font-size:21px;
                font-weight:900;
            }

            QLabel#extractorSection {
                color:#08245F;
                font-size:15px;
                font-weight:900;
            }

            QLabel#extractorMuted {
                color:#6079A5;
                font-size:10px;
            }

            QLabel#extractorBadge {
                background:#EAF9F2;
                color:#078B5F;
                border:1px solid #C3EAD8;
                border-radius:9px;
                padding:8px 12px;
                font-size:10px;
                font-weight:900;
            }

            QTabBar#extractorTabs::tab {
                background:#FFFFFF;
                color:#315A8C;
                border:1px solid #D4E4F5;
                border-radius:8px;
                padding:9px 22px;
                margin-right:5px;
                min-width:110px;
            }

            QTabBar#extractorTabs::tab:selected {
                background:#087AF7;
                color:#FFFFFF;
                border-color:#087AF7;
                font-weight:900;
            }

            QLineEdit {
                min-height:38px;
                background:#FFFFFF;
                color:#08245F;
                border:1px solid #C9DDF2;
                border-radius:8px;
                padding:5px 11px;
            }

            QLineEdit:focus {
                border:1px solid #087AF7;
            }

            QPushButton {
                min-height:34px;
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
                border-radius:8px;
                padding:7px 13px;
                font-weight:800;
            }

            QPushButton:hover {
                background:#EEF6FF;
            }

            QPushButton#extractorPrimary {
                background:#087AF7;
                color:#FFFFFF;
                border:0;
                min-height:42px;
            }

            QPushButton#extractorDanger {
                background:#FFF1F4;
                color:#D72B52;
                border:1px solid #FFB4C6;
            }

            QRadioButton {
                color:#244B7B;
                background:#F8FBFF;
                border:1px solid #D8E7F6;
                border-radius:8px;
                padding:9px 12px;
                spacing:8px;
                min-height:30px;
            }

            QRadioButton:checked {
                background:#EAF4FF;
                border:1px solid #8EC5FF;
                color:#075DB8;
                font-weight:900;
            }

            QProgressBar {
                min-height:12px;
                max-height:12px;
                background:#E9F1FA;
                border:0;
                border-radius:6px;
                text-align:center;
            }

            QProgressBar::chunk {
                background:#087AF7;
                border-radius:6px;
            }

            QListWidget {
                background:#FFFFFF;
                color:#173E75;
                border:1px solid #D4E4F5;
                border-radius:9px;
                alternate-background-color:#F8FBFF;
            }
            """
        )

    def _build_download_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        link_card = QFrame()
        link_card.setObjectName("extractorCard")

        lc = QVBoxLayout(link_card)
        lc.setContentsMargins(16, 14, 16, 14)
        lc.setSpacing(8)

        title = QLabel("Baixar vídeo")
        title.setObjectName("extractorSection")
        lc.addWidget(title)

        hint = QLabel(
            "Cole o link do vídeo. O download é salvo na pasta Videos do portable."
        )
        hint.setObjectName("extractorMuted")
        lc.addWidget(hint)

        link_row = QHBoxLayout()
        link_row.setSpacing(8)

        self.url = QLineEdit()
        self.url.setPlaceholderText(
            "https://..."
        )
        self.url.returnPressed.connect(
            self.start_download
        )

        self.download_button = QPushButton(
            "⇩  BAIXAR VÍDEO"
        )
        self.download_button.setObjectName(
            "extractorPrimary"
        )
        self.download_button.clicked.connect(
            self.start_download
        )

        link_row.addWidget(self.url, 1)
        link_row.addWidget(self.download_button)

        lc.addLayout(link_row)
        layout.addWidget(link_card)

        options = QFrame()
        options.setObjectName("extractorCard")

        ol = QVBoxLayout(options)
        ol.setContentsMargins(16, 14, 16, 14)
        ol.setSpacing(8)

        options_title = QLabel(
            "Qualidade e formato"
        )
        options_title.setObjectName(
            "extractorSection"
        )
        ol.addWidget(options_title)

        self.quality_group = QButtonGroup(self)
        self.quality_buttons = []

        qualities = QHBoxLayout()
        qualities.setSpacing(8)

        selected = self.state_store.load_quality_index(
            1
        )

        for index, quality in enumerate(
            EXTRACTOR_QUALITIES
        ):
            radio = QRadioButton(
                quality.label
            )
            self.quality_group.addButton(
                radio,
                index,
            )
            self.quality_buttons.append(
                radio
            )
            radio.toggled.connect(
                lambda checked, i=index:
                self._quality_changed(i)
                if checked
                else None
            )
            qualities.addWidget(radio, 1)

        if self.quality_buttons:
            selected = max(
                0,
                min(
                    selected,
                    len(self.quality_buttons) - 1,
                ),
            )
            self.quality_buttons[
                selected
            ].setChecked(True)

        ol.addLayout(qualities)

        format_line = QLabel(
            "Formato de saída: MP4"
        )
        format_line.setObjectName(
            "extractorMuted"
        )
        ol.addWidget(format_line)

        layout.addWidget(options)

        status_card = QFrame()
        status_card.setObjectName(
            "extractorStatusCard"
        )

        sl = QVBoxLayout(status_card)
        sl.setContentsMargins(16, 14, 16, 14)
        sl.setSpacing(8)

        row = QHBoxLayout()

        status_title = QLabel(
            "Progresso do download"
        )
        status_title.setObjectName(
            "extractorSection"
        )

        self.percent = QLabel("0%")
        self.percent.setStyleSheet(
            "color:#087AF7;"
            "font-size:16px;"
            "font-weight:900;"
        )

        row.addWidget(status_title)
        row.addStretch(1)
        row.addWidget(self.percent)

        sl.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        sl.addWidget(self.progress)

        self.status = QLabel(
            "Cole o link, escolha a qualidade e clique em BAIXAR VÍDEO."
        )
        self.status.setObjectName(
            "extractorMuted"
        )
        self.status.setWordWrap(True)
        sl.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.open_videos_button = QPushButton(
            "▣  Abrir pasta Vídeos"
        )
        self.open_videos_button.clicked.connect(
            self.open_videos
        )

        self.cancel_button = QPushButton(
            "×  CANCELAR"
        )
        self.cancel_button.setObjectName(
            "extractorDanger"
        )
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(
            self.cancel_download
        )

        actions.addWidget(
            self.open_videos_button
        )
        actions.addWidget(
            self.cancel_button
        )
        actions.addStretch(1)

        sl.addLayout(actions)

        self.binary_status = QLabel()
        self.binary_status.setObjectName(
            "extractorMuted"
        )
        self.binary_status.setWordWrap(True)
        sl.addWidget(self.binary_status)

        layout.addWidget(status_card)
        layout.addStretch(1)

        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("extractorCard")

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(8)

        head = QHBoxLayout()

        title = QLabel("Histórico")
        title.setObjectName(
            "extractorSection"
        )

        self.clear_history_button = QPushButton(
            "Limpar histórico"
        )
        self.clear_history_button.setObjectName(
            "extractorDanger"
        )
        self.clear_history_button.clicked.connect(
            self.clear_history
        )

        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(
            self.clear_history_button
        )

        cl.addLayout(head)

        hint = QLabel(
            "Arquivos baixados recentemente neste portable."
        )
        hint.setObjectName("extractorMuted")
        cl.addWidget(hint)

        self.history = QListWidget()
        cl.addWidget(self.history, 1)

        layout.addWidget(card, 1)
        return page

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        globoplay = QFrame()
        globoplay.setObjectName(
            "extractorCard"
        )

        gl = QVBoxLayout(globoplay)
        gl.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        gl.setSpacing(8)

        title = QLabel(
            "Sessão Globoplay"
        )
        title.setObjectName(
            "extractorSection"
        )
        gl.addWidget(title)

        self.session_status = QLabel()
        self.session_status.setObjectName(
            "extractorMuted"
        )
        gl.addWidget(self.session_status)

        buttons = QHBoxLayout()

        self.login_button = QPushButton(
            "LOGIN GLOBOPLAY"
        )
        self.login_button.setObjectName(
            "extractorPrimary"
        )
        self.login_button.clicked.connect(
            self.open_globoplay_login
        )

        self.delete_session_button = QPushButton(
            "APAGAR SESSÃO"
        )
        self.delete_session_button.setObjectName(
            "extractorDanger"
        )
        self.delete_session_button.clicked.connect(
            self.delete_session
        )

        buttons.addWidget(
            self.login_button
        )
        buttons.addWidget(
            self.delete_session_button
        )
        buttons.addStretch(1)

        gl.addLayout(buttons)

        help_text = QLabel(
            "A senha não é armazenada. Apenas os cookies da sessão "
            "são protegidos pelo Windows."
        )
        help_text.setObjectName(
            "extractorMuted"
        )
        help_text.setWordWrap(True)
        gl.addWidget(help_text)

        layout.addWidget(globoplay)

        ytdlp = QFrame()
        ytdlp.setObjectName(
            "extractorCard"
        )

        yl = QVBoxLayout(ytdlp)
        yl.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        yl.setSpacing(8)

        ytitle = QLabel(
            "Motor yt-dlp"
        )
        ytitle.setObjectName(
            "extractorSection"
        )
        yl.addWidget(ytitle)

        self.update_button = QPushButton(
            "ATUALIZAR YT-DLP"
        )
        self.update_button.clicked.connect(
            self.update_ytdlp
        )
        yl.addWidget(
            self.update_button
        )

        self.settings_status = QLabel()
        self.settings_status.setObjectName(
            "extractorMuted"
        )
        self.settings_status.setWordWrap(True)
        yl.addWidget(
            self.settings_status
        )

        layout.addWidget(ytdlp)
        layout.addStretch(1)

        return page
