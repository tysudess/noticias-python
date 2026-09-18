from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from PySide6.QtCore import QDate, Qt, QTime, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDateEdit, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QPushButton, QScrollArea, QTimeEdit, QVBoxLayout, QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


def _time(ms: int) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


def _duration(ms: int) -> str:
    sec = max(0, int(ms // 1000))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _open(url: str) -> None:
    if url:
        QDesktopServices.openUrl(QUrl(url))


def _copy(url: str) -> None:
    QApplication.clipboard().setText(url)


def _whatsapp(title: str, url: str) -> None:
    QDesktopServices.openUrl(QUrl("https://wa.me/?text=" + quote(f"{title}\n{url}")))


class VideosPage(BasePage):
    extract_requested = Signal(str)

    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)

        top = QFrame()
        top.setObjectName("videoTop")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(12, 10, 12, 10)
        tl.setSpacing(8)

        search_row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setObjectName("videoSearch")
        self.query.setPlaceholderText("⌕  Buscar nos vídeos (título, fonte, termo...)")
        search_row.addWidget(self.query, 1)

        self.run = QPushButton("↻  Buscar vídeos agora")
        self.run.setObjectName("videoPrimary")
        self.run.clicked.connect(controller.search_videos)
        search_row.addWidget(self.run)
        tl.addLayout(search_row)

        periods = QHBoxLayout()
        periods.setSpacing(8)
        self.period_buttons = []

        for label, hours in (
            ("24 horas", 24),
            ("7 dias", 168),
            ("30 dias", 720),
        ):
            button = QPushButton(label)
            button.setObjectName("videoPeriod")
            button.setCheckable(True)

            if label == "24 horas":
                button.setChecked(True)

            button.clicked.connect(
                lambda _checked=False, h=hours: controller.search_videos(
                    *controller.period_last_hours(h)
                )
            )

            periods.addWidget(button)
            self.period_buttons.append(button)

        self.custom = QPushButton("Período personalizado")
        self.custom.setObjectName("videoPeriod")
        self.custom.setCheckable(True)
        periods.addWidget(self.custom)
        periods.addStretch()
        tl.addLayout(periods)

        self.period_box = QFrame()
        self.period_box.setObjectName("videoCustom")
        pl = QHBoxLayout(self.period_box)
        pl.setContentsMargins(8, 5, 8, 5)

        today = QDate.currentDate()
        self.start_date = QDateEdit(today.addDays(-1))
        self.start_time = QTimeEdit(QTime(0, 0))
        self.end_date = QDateEdit(today)
        self.end_time = QTimeEdit(QTime(23, 59))
        self.period_go = QPushButton("Buscar período")
        self.period_go.setObjectName("videoPrimary")

        for widget in (
            self.start_date,
            self.start_time,
            self.end_date,
            self.end_time,
            self.period_go,
        ):
            pl.addWidget(widget)

        self.period_box.hide()
        self.custom.toggled.connect(self.period_box.setVisible)
        self.period_go.clicked.connect(self._period)
        tl.addWidget(self.period_box)

        self.root.addWidget(top)

        progress_card = QFrame()
        progress_card.setObjectName("videoProgressCard")
        pcl = QVBoxLayout(progress_card)
        pcl.setContentsMargins(16, 12, 16, 12)
        pcl.setSpacing(7)

        head = QHBoxLayout()

        icon = QLabel("✓")
        icon.setObjectName("videoCheck")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        head.addWidget(icon)

        title_box = QVBoxLayout()

        self.exec_title = QLabel("Vídeos • última execução concluída")
        self.exec_title.setObjectName("videoExecTitle")

        self.exec_sub = QLabel("Pronto")
        self.exec_sub.setObjectName("videoMuted")

        title_box.addWidget(self.exec_title)
        title_box.addWidget(self.exec_sub)

        head.addLayout(title_box, 1)

        self.metrics = {}

        for key, caption in (
            ("pct", "Conclusão"),
            ("found", "Encontrados"),
            ("new", "Novos"),
            ("errors", "Falhas"),
            ("steps", "Etapas"),
            ("time", "Tempo"),
        ):
            box = QVBoxLayout()
            value = QLabel("0")
            value.setObjectName("videoMetric")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cap = QLabel(caption)
            cap.setObjectName("videoMetricCaption")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)

            box.addWidget(value)
            box.addWidget(cap)
            head.addLayout(box)

            self.metrics[key] = value

        pcl.addLayout(head)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setObjectName("videoProgress")
        pcl.addWidget(self.progress)

        self.detail = QLabel("Nenhuma busca em andamento.")
        self.detail.setObjectName("videoSuccess")
        pcl.addWidget(self.detail)

        self.root.addWidget(progress_card)

        self.stop = QPushButton("■  Parar busca")
        self.stop.setObjectName("videoStop")
        self.stop.clicked.connect(controller.stop_video_search)
        self.stop.hide()

        self.root.addWidget(
            self.stop,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        head_list = QHBoxLayout()

        self.count = QLabel("Vídeos encontrados")
        self.count.setObjectName("videoListTitle")
        head_list.addWidget(self.count)

        head_list.addStretch()

        self.shown = QLabel("")
        self.shown.setObjectName("videoMuted")
        head_list.addWidget(self.shown)

        self.root.addLayout(head_list)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setObjectName("videoScroll")

        self.container = QWidget()
        self.items = QVBoxLayout(self.container)
        self.items.setContentsMargins(0, 0, 2, 0)
        self.items.setSpacing(7)
        self.items.addStretch()

        self.scroll.setWidget(self.container)
        self.root.addWidget(self.scroll, 1)

        self.query.textChanged.connect(
            lambda _: self.refresh(controller.state)
        )

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#videoTop, QFrame#videoProgressCard {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QLineEdit#videoSearch {
            min-height:35px;
            padding:0 11px;
        }
        QPushButton#videoPrimary {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:8px 15px;
            font-weight:800;
        }
        QPushButton#videoPeriod {
            background:white;
            color:#153E75;
            border:1px solid #C9DCF2;
            border-radius:8px;
            padding:7px 14px;
            font-weight:700;
        }
        QPushButton#videoPeriod:checked {
            background:#EAF4FF;
            color:#087AF7;
            border-color:#087AF7;
        }
        QFrame#videoCustom {
            background:#F8FBFF;
            border:1px solid #DDE9F6;
            border-radius:8px;
        }
        QLabel#videoCheck {
            background:#DDF8EC;
            color:#078B5F;
            border-radius:27px;
            font-size:29px;
            font-weight:900;
        }
        QLabel#videoExecTitle {
            color:#08245F;
            font-size:18px;
            font-weight:900;
        }
        QLabel#videoMuted {
            color:#6079A5;
            font-size:10px;
        }
        QLabel#videoMetric {
            color:#087AF7;
            font-size:18px;
            font-weight:900;
            min-width:56px;
        }
        QLabel#videoMetricCaption {
            color:#6079A5;
            font-size:9px;
        }
        QProgressBar#videoProgress {
            background:#E3ECF6;
            border:0;
            border-radius:4px;
            max-height:10px;
        }
        QProgressBar#videoProgress::chunk {
            background:#0A7DF8;
            border-radius:4px;
        }
        QLabel#videoSuccess {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:7px;
            padding:7px 10px;
            font-size:10px;
        }
        QPushButton#videoStop {
            background:#FFF1F4;
            color:#E03155;
            border:1px solid #FFB8C8;
            border-radius:8px;
            padding:8px 14px;
        }
        QLabel#videoListTitle {
            color:#08245F;
            font-size:18px;
            font-weight:900;
        }
        QScrollArea#videoScroll {
            border:0;
            background:transparent;
        }
        QFrame#videoItem {
            background:white;
            border:1px solid #DCE9F6;
            border-radius:10px;
        }
        QLabel#videoIcon {
            background:#F0E9FF;
            color:#7145F5;
            border-radius:25px;
            font-size:24px;
            font-weight:900;
        }
        QLabel#videoMeta {
            color:#5272A1;
            font-size:9px;
        }
        QLabel#videoTitle {
            color:#08245F;
            font-size:12px;
            font-weight:900;
        }
        QLabel#videoTag {
            background:#F4ECFF;
            color:#8B3CF6;
            border:1px solid #DFC6FF;
            border-radius:7px;
            padding:6px 10px;
            font-size:9px;
            font-weight:800;
        }
        QLabel#videoNew {
            background:#E6F8F0;
            color:#078B5F;
            border:1px solid #A9E4CB;
            border-radius:6px;
            padding:3px 8px;
            font-size:8px;
            font-weight:900;
        }
        QPushButton#videoAction {
            background:white;
            color:#0C3974;
            border:1px solid #C9DDF2;
            border-radius:7px;
            padding:7px 10px;
            font-weight:700;
        }
        QPushButton#videoWhats {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #BFE8D5;
            border-radius:7px;
            padding:7px 10px;
            font-weight:700;
        }
        """

    def _period(self) -> None:
        parsed = self.controller.parse_period(
            self.start_date.date().toString("yyyy-MM-dd"),
            self.start_time.time().toString("HH:mm"),
            self.end_date.date().toString("yyyy-MM-dd"),
            self.end_time.time().toString("HH:mm"),
        )

        if parsed:
            self.controller.search_videos(*parsed)

    def _clear(self) -> None:
        while self.items.count() > 1:
            item = self.items.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

    def _card(self, video, is_new: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("videoItem")
        card.setMinimumHeight(100)

        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        icon = QLabel("▶")
        icon.setObjectName("videoIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(3)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(7)

        meta = QLabel(
            f"{video.sourceName}  •  {_time(video.publishedAt)}"
        )
        meta.setObjectName("videoMeta")
        meta_row.addWidget(meta)

        if is_new:
            new_badge = QLabel("NOVO")
            new_badge.setObjectName("videoNew")
            new_badge.setFixedHeight(20)
            meta_row.addWidget(
                new_badge,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        meta_row.addStretch()
        text.addLayout(meta_row)

        title = QLabel(video.title)
        title.setObjectName("videoTitle")
        title.setWordWrap(True)
        text.addWidget(title)

        tag_text = video.matchedDemand or video.matchedTerm or ""

        if tag_text:
            tag = QLabel(f"Termo: {tag_text}")
            tag.setObjectName("videoTag")
            tag.setMaximumWidth(210)
            text.addWidget(
                tag,
                0,
                Qt.AlignmentFlag.AlignLeft,
            )

        row.addLayout(text, 1)

        for label, obj, fn in (
            ("↗  Abrir vídeo", "videoAction", lambda: _open(video.link)),
            ("◉  WhatsApp", "videoWhats", lambda: _whatsapp(video.title, video.link)),
            ("▣  Copiar link", "videoAction", lambda: _copy(video.link)),
            ("⇩  Extrair vídeo", "videoAction", lambda: self.extract_requested.emit(video.link)),
        ):
            button = QPushButton(label)
            button.setObjectName(obj)
            button.clicked.connect(fn)
            row.addWidget(button)

        return card

    def refresh(self, state: UiState) -> None:
        query = self.query.text().strip().lower()

        rows = [
            video
            for video in state.videos
            if not query
            or query
            in (
                f"{video.title} "
                f"{video.sourceName} "
                f"{video.matchedTerm} "
                f"{video.matchedDemand}"
            ).lower()
        ]

        self.count.setText("Vídeos encontrados")
        self.shown.setText(f"{len(rows)} exibido(s)")

        self.run.setEnabled(
            not state.video_busy
            and self.controller.search_available
        )
        self.period_go.setEnabled(
            not state.video_busy
            and self.controller.search_available
        )
        self.stop.setVisible(state.video_busy)

        progress = state.video_progress

        fraction = (
            max(
                0.0,
                min(
                    1.0,
                    float(getattr(progress, "fraction", 0.0)),
                ),
            )
            if state.video_busy
            else 1.0
        )

        pct = round(fraction * 100)
        found = int(getattr(progress, "found", 0))
        errors = int(getattr(progress, "errors", 0))
        completed = int(getattr(progress, "completed", 0))
        total = int(getattr(progress, "total", 0))
        fresh = len(state.new_video_links)

        self.exec_title.setText(
            "Vídeos • busca em andamento"
            if state.video_busy
            else "Vídeos • última execução concluída"
        )
        self.exec_sub.setText(state.video_status)

        self.metrics["pct"].setText(f"{pct}%")
        self.metrics["found"].setText(str(found))
        self.metrics["new"].setText(str(fresh))
        self.metrics["errors"].setText(str(errors))
        self.metrics["steps"].setText(f"{completed}/{total}")
        self.metrics["time"].setText(
            _duration(state.last_video_duration_ms)
        )

        self.progress.setValue(pct)

        if state.video_busy:
            source = (
                getattr(progress, "currentSource", "")
                or "Preparando"
            )
            query_text = (
                getattr(progress, "currentQuery", "")
                or "consultas"
            )
            self.detail.setText(
                f"{source} • {query_text}"
            )
        else:
            self.detail.setText(
                f"A busca foi concluída. "
                f"{found} vídeo(s) encontrado(s) nesta execução."
            )

        self._clear()

        # new_video_links contém somente os vídeos inseridos na execução atual.
        # Assim que outra busca inicia, AutomationService limpa o conjunto e os
        # selos NOVO da execução anterior desaparecem automaticamente.
        for video in rows:
            self.items.insertWidget(
                self.items.count() - 1,
                self._card(
                    video,
                    video.link in state.new_video_links,
                ),
            )

        if rows:
            self.container.setMinimumHeight(
                len(rows) * 108
            )
        else:
            self.container.setMinimumHeight(120)
