from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import (
    QAbstractListModel, QDate, QEvent, QModelIndex, QRect, QSize, Qt, QTime, Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView,
    QProgressBar, QPushButton, QStyledItemDelegate, QStyleOptionViewItem,
    QTimeEdit, QVBoxLayout, QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.url_tools import (
    copy_article_url, open_article_url, open_whatsapp,
)


def _format_time(ms: int) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


def _duration(ms: int) -> str:
    sec = max(0, int(ms // 1000))
    return f"{sec // 60:02d}:{sec % 60:02d}"


class NewsModel(QAbstractListModel):
    NewsRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.rows = []

    def set_rows(self, rows) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None
        news = self.rows[index.row()]
        if role == self.NewsRole:
            return news
        if role == Qt.ItemDataRole.DisplayRole:
            return news.title
        return None


class NewsDelegate(QStyledItemDelegate):
    extract_requested = Signal(str)

    ROW_H = 78
    BTN_W = 112
    BTN_H = 34
    GAP = 6

    def sizeHint(self, option, index) -> QSize:
        return QSize(1000, self.ROW_H)

    def _buttons(self, rect: QRect) -> list[QRect]:
        total = self.BTN_W * 4 + self.GAP * 3
        x = rect.right() - total - 10
        y = rect.top() + (rect.height() - self.BTN_H) // 2
        return [
            QRect(
                x + i * (self.BTN_W + self.GAP),
                y,
                self.BTN_W,
                self.BTN_H,
            )
            for i in range(4)
        ]

    @staticmethod
    def _rounded(painter, rect, fill, border, radius=9):
        painter.setBrush(QColor(fill))
        painter.setPen(QPen(QColor(border), 1))
        painter.drawRoundedRect(rect, radius, radius)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        news = index.data(NewsModel.NewsRole)
        if news is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        card = option.rect.adjusted(2, 3, -4, -3)
        self._rounded(painter, card, "#FFFFFF", "#DCE9F6", 10)

        painter.fillRect(
            QRect(card.left(), card.top() + 7, 4, card.height() - 14),
            QColor("#1689F8"),
        )

        avatar = QRect(card.left() + 14, card.top() + 16, 40, 40)
        self._rounded(painter, avatar, "#1284F7", "#1284F7", 8)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(
            avatar,
            Qt.AlignmentFlag.AlignCenter,
            (news.source or "N")[:2].upper(),
        )

        buttons = self._buttons(card)
        text_left = avatar.right() + 11
        text_right = buttons[0].left() - 12

        tag_text = (news.matchedDemand or news.matchedTerm or "").strip()
        tag_rect = None

        if tag_text:
            tag_w = min(145, max(72, len(tag_text) * 6 + 20))
            tag_rect = QRect(
                text_right - tag_w,
                card.top() + 21,
                tag_w,
                32,
            )
            text_right = tag_rect.left() - 10

        meta_rect = QRect(
            text_left,
            card.top() + 10,
            max(20, text_right - text_left),
            18,
        )
        title_rect = QRect(
            text_left,
            card.top() + 29,
            max(20, text_right - text_left),
            38,
        )

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#5272A1"))
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{news.source}  •  {_format_time(news.date)}",
        )

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.setPen(QColor("#08245F"))
        fm = QFontMetrics(painter.font())
        title = fm.elidedText(
            news.title,
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

        if tag_rect:
            self._rounded(painter, tag_rect, "#EAF4FF", "#EAF4FF", 6)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#087AF7"))
            painter.drawText(
                tag_rect.adjusted(6, 0, -6, 0),
                Qt.AlignmentFlag.AlignCenter,
                QFontMetrics(painter.font()).elidedText(
                    tag_text.upper(),
                    Qt.TextElideMode.ElideRight,
                    tag_rect.width() - 12,
                ),
            )

        specs = [
            ("↗ Abrir matéria", "#FFFFFF", "#C9DDF2", "#0C3974"),
            ("◉ WhatsApp", "#EAF9F2", "#BFE8D5", "#078B5F"),
            ("▣ Copiar link", "#FFFFFF", "#C9DDF2", "#0C3974"),
            ("⇩ Extrair matéria", "#F4ECFF", "#DFC6FF", "#8B3CF6"),
        ]

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for rect, (label, fill, border, color) in zip(buttons, specs):
            self._rounded(painter, rect, fill, border, 7)
            painter.setPen(QColor(color))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.restore()

    def editorEvent(self, event, model, option, index) -> bool:
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False

        news = index.data(NewsModel.NewsRole)
        if news is None:
            return False

        point = (
            event.position().toPoint()
            if hasattr(event, "position")
            else event.pos()
        )
        buttons = self._buttons(option.rect.adjusted(2, 3, -4, -3))

        for idx, rect in enumerate(buttons):
            if not rect.contains(point):
                continue

            if idx == 0:
                open_article_url(news.link)
            elif idx == 1:
                open_whatsapp(news.title, news.link)
            elif idx == 2:
                copy_article_url(news.link)
            elif idx == 3:
                self.extract_requested.emit(news.link)

            return True

        return False


class NewsPage(QWidget):
    extract_requested = Signal(str)

    def __init__(self, controller: MainUiController) -> None:
        super().__init__()
        self.controller = controller

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(7)

        banner = QFrame()
        banner.setObjectName("newsBanner")
        banner.setMaximumHeight(108)

        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 9, 18, 9)

        left = QVBoxLayout()
        left.setSpacing(1)

        kicker = QLabel("CENTRAL DE INTELIGÊNCIA DE MÍDIA")
        kicker.setObjectName("newsKicker")

        title = QLabel("Notícias")
        title.setObjectName("newsTitle")

        subtitle = QLabel(
            "Acompanhe matérias em tempo real e transforme informação em decisões estratégicas."
        )
        subtitle.setObjectName("newsSubtitle")

        left.addWidget(kicker)
        left.addWidget(title)
        left.addWidget(subtitle)

        bl.addLayout(left, 2)
        bl.addStretch(2)

        art = QLabel("◯      ◌      ▤")
        art.setObjectName("newsBannerArt")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setMaximumWidth(290)
        bl.addWidget(art, 1)

        root.addWidget(banner)

        filters = QFrame()
        filters.setObjectName("newsCard")

        fl = QVBoxLayout(filters)
        fl.setContentsMargins(10, 8, 10, 8)
        fl.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.query = QLineEdit()
        self.query.setPlaceholderText(
            "⌕  Buscar nas notícias (título, fonte, termo...)"
        )
        self.query.setObjectName("newsSearch")
        top.addWidget(self.query, 1)

        self.search24 = QPushButton("↻  Buscar últimas 24h")
        self.search24.setObjectName("newsPrimary")
        self.search24.clicked.connect(
            lambda: self.controller.search_news(
                *self.controller.period_last_hours(24)
            )
        )
        top.addWidget(self.search24)

        self.only_demands = QCheckBox("Só demandas")
        top.addWidget(self.only_demands)

        fl.addLayout(top)

        periods = QHBoxLayout()
        periods.setSpacing(6)

        self.period_buttons = []

        for label, hours in (
            ("Hoje", None),
            ("24 horas", 24),
            ("7 dias", 168),
            ("30 dias", 720),
        ):
            btn = QPushButton(label)
            btn.setObjectName("periodButton")
            btn.setCheckable(True)

            if label == "Hoje":
                btn.setChecked(True)

            btn.clicked.connect(
                lambda _checked=False, h=hours: self._run_period(h)
            )

            periods.addWidget(btn)
            self.period_buttons.append(btn)

        self.custom = QPushButton("▣  Período personalizado")
        self.custom.setObjectName("periodButton")
        self.custom.setCheckable(True)

        periods.addWidget(self.custom)
        periods.addStretch()
        fl.addLayout(periods)

        self.period_box = QFrame()
        self.period_box.setObjectName("customPeriod")

        pl = QHBoxLayout(self.period_box)
        pl.setContentsMargins(8, 5, 8, 5)
        pl.setSpacing(6)

        today = QDate.currentDate()

        self.start_date = QDateEdit(today.addDays(-1))
        self.start_time = QTimeEdit(QTime(0, 0))
        self.end_date = QDateEdit(today)
        self.end_time = QTimeEdit(QTime(23, 59))
        self.period_go = QPushButton("Buscar período")
        self.period_go.setObjectName("newsPrimary")

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

        fl.addWidget(self.period_box)
        root.addWidget(filters)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        progress_card = QFrame()
        progress_card.setObjectName("newsCard")

        pcl = QVBoxLayout(progress_card)
        pcl.setContentsMargins(12, 8, 12, 8)
        pcl.setSpacing(4)

        head = QHBoxLayout()

        self.exec_title = QLabel("Busca concluída com sucesso")
        self.exec_title.setObjectName("execTitle")

        self.exec_pct = QLabel("100%")
        self.exec_pct.setObjectName("execPct")

        head.addWidget(self.exec_title)
        head.addStretch()
        head.addWidget(self.exec_pct)

        pcl.addLayout(head)

        self.exec_sub = QLabel("0 demanda(s) • 0 resultado(s) • 0 novo(s)")
        self.exec_sub.setObjectName("newsMuted")
        pcl.addWidget(self.exec_sub)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setObjectName("newsProgress")
        pcl.addWidget(self.progress)

        self.exec_detail = QLabel("A busca foi concluída.")
        self.exec_detail.setObjectName("successStrip")
        pcl.addWidget(self.exec_detail)

        status_row.addWidget(progress_card, 3)

        metrics = QFrame()
        metrics.setObjectName("newsCard")

        ml = QHBoxLayout(metrics)
        ml.setContentsMargins(5, 5, 5, 5)
        ml.setSpacing(0)

        self.metric_labels = {}

        for key, label, tone in (
            ("pct", "Conclusão", "green"),
            ("found", "Encontradas", "orange"),
            ("new", "Novas", "purple"),
            ("errors", "Falhas", "red"),
            ("steps", "Etapas", "blue"),
            ("time", "Tempo", "blue"),
        ):
            box = QFrame()
            box.setObjectName("metricMini")

            lay = QVBoxLayout(box)
            lay.setContentsMargins(8, 5, 8, 5)
            lay.setSpacing(1)

            value = QLabel("0")
            value.setObjectName("metricMiniValue")
            value.setProperty("tone", tone)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cap = QLabel(label)
            cap.setObjectName("metricMiniCaption")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lay.addWidget(value)
            lay.addWidget(cap)

            ml.addWidget(box, 1)
            self.metric_labels[key] = value

        status_row.addWidget(metrics, 2)
        root.addLayout(status_row)

        self.stop = QPushButton("■  Parar busca")
        self.stop.setObjectName("stopButton")
        self.stop.clicked.connect(self.controller.stop_news_search)
        self.stop.hide()

        root.addWidget(self.stop, 0, Qt.AlignmentFlag.AlignLeft)

        list_head = QHBoxLayout()

        self.count = QLabel("▣  Notícias encontradas")
        self.count.setObjectName("newsListTitle")

        list_head.addWidget(self.count)
        list_head.addStretch()

        sort_label = QLabel("Mais recentes ⌄")
        sort_label.setObjectName("sortPill")

        list_head.addWidget(sort_label)
        root.addLayout(list_head)

        self.model = NewsModel(self)
        self.delegate = NewsDelegate(self)
        self.delegate.extract_requested.connect(
            self.extract_requested.emit
        )

        self.list_view = QListView()
        self.list_view.setObjectName("newsListView")
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
        self.list_view.setMouseTracking(True)
        self.list_view.setSpacing(0)

        root.addWidget(self.list_view, 1)

        self.query.textChanged.connect(self._filters_changed)
        self.only_demands.toggled.connect(self._filters_changed)

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#newsBanner {
            background:#F2F8FF;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QLabel#newsKicker { color:#087AF7; font-size:10px; font-weight:800; }
        QLabel#newsTitle { color:#08245F; font-size:24px; font-weight:900; }
        QLabel#newsSubtitle { color:#5C73A4; font-size:11px; }
        QLabel#newsBannerArt { color:#A9CFF8; font-size:31px; }

        QFrame#newsCard {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:10px;
        }

        QLineEdit#newsSearch {
            min-height:33px;
            padding:0 10px;
            font-size:11px;
        }

        QPushButton#newsPrimary {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:7px 13px;
            min-height:29px;
            font-weight:800;
            font-size:11px;
        }

        QPushButton#periodButton {
            background:white;
            color:#153E75;
            border:1px solid #C9DCF2;
            border-radius:7px;
            padding:5px 12px;
            min-height:27px;
            font-weight:700;
            font-size:10px;
        }
        QPushButton#periodButton:checked {
            background:#EAF4FF;
            color:#087AF7;
            border:1px solid #087AF7;
        }

        QFrame#customPeriod {
            background:#F8FBFF;
            border:1px solid #DDE9F6;
            border-radius:8px;
        }

        QLabel#execTitle {
            color:#08245F;
            font-size:14px;
            font-weight:900;
        }
        QLabel#execPct {
            color:#08A66B;
            font-size:19px;
            font-weight:900;
        }
        QLabel#newsMuted {
            color:#6079A5;
            font-size:10px;
        }

        QProgressBar#newsProgress {
            background:#E6F0FA;
            border:0;
            border-radius:4px;
            max-height:8px;
        }
        QProgressBar#newsProgress::chunk {
            background:#16B97E;
            border-radius:4px;
        }

        QLabel#successStrip {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:6px;
            padding:4px 8px;
            font-size:10px;
        }

        QFrame#metricMini {
            border-right:1px solid #E2ECF6;
        }

        QLabel#metricMiniValue {
            font-size:17px;
            font-weight:900;
        }
        QLabel#metricMiniValue[tone='green'] { color:#08A66B; }
        QLabel#metricMiniValue[tone='orange'] { color:#F0A000; }
        QLabel#metricMiniValue[tone='purple'] { color:#8B3CF6; }
        QLabel#metricMiniValue[tone='red'] { color:#EA3158; }
        QLabel#metricMiniValue[tone='blue'] { color:#087AF7; }

        QLabel#metricMiniCaption {
            color:#5C73A4;
            font-size:9px;
        }

        QPushButton#stopButton {
            background:#FFF1F4;
            color:#E03155;
            border:1px solid #FFB8C8;
            border-radius:7px;
            padding:6px 12px;
        }

        QLabel#newsListTitle {
            color:#08245F;
            font-size:16px;
            font-weight:900;
        }

        QLabel#sortPill {
            background:white;
            color:#375B88;
            border:1px solid #D5E4F4;
            border-radius:8px;
            padding:6px 11px;
            font-size:10px;
        }

        QListView#newsListView {
            background:transparent;
            border:0;
            outline:0;
        }

        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            margin:0;
            border-radius:5px;
        }
        QScrollBar::handle:vertical {
            background:#9FC3EA;
            min-height:42px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical:hover {
            background:#74AAE0;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height:0;
        }
        """

    def _run_period(self, hours: int | None) -> None:
        for button in self.period_buttons:
            button.setChecked(False)

        sender = self.sender()

        if isinstance(sender, QPushButton):
            sender.setChecked(True)

        if hours is None:
            self.controller.search_news(
                *self.controller.period_today()
            )
        else:
            self.controller.search_news(
                *self.controller.period_last_hours(hours)
            )

    def _period(self) -> None:
        parsed = self.controller.parse_period(
            self.start_date.date().toString("yyyy-MM-dd"),
            self.start_time.time().toString("HH:mm"),
            self.end_date.date().toString("yyyy-MM-dd"),
            self.end_time.time().toString("HH:mm"),
        )

        if parsed:
            self.controller.search_news(*parsed)

    def _filters_changed(self, *_args) -> None:
        self.refresh(self.controller.state)

    def _rows(self, state: UiState):
        query = self.query.text().strip().lower()

        rows = [
            news
            for news in state.news
            if (
                not self.only_demands.isChecked()
                or news.demand
            )
            and (
                not query
                or query
                in (
                    f"{news.title} "
                    f"{news.source} "
                    f"{news.matchedTerm} "
                    f"{news.matchedDemand}"
                ).lower()
            )
        ]

        return sorted(
            rows,
            key=lambda news: getattr(news, "date", 0),
            reverse=True,
        )

    def refresh(self, state: UiState) -> None:
        rows = self._rows(state)
        self.model.set_rows(rows)

        self.count.setText(
            f"▣  Notícias encontradas   "
            f"{len(rows)} resultado(s) para o período selecionado"
        )

        self.search24.setEnabled(
            not state.news_busy
            and self.controller.search_available
        )
        self.period_go.setEnabled(
            not state.news_busy
            and self.controller.search_available
        )
        self.stop.setVisible(state.news_busy)

        progress = state.news_progress

        fraction = (
            max(
                0.0,
                min(
                    1.0,
                    float(getattr(progress, "fraction", 0.0)),
                ),
            )
            if state.news_busy
            else 1.0
        )

        pct = round(fraction * 100)
        found = int(getattr(progress, "found", 0))
        errors = int(getattr(progress, "errors", 0))
        completed = int(getattr(progress, "completed", 0))
        total = int(getattr(progress, "total", 0))
        fresh = len(state.new_news_links)

        self.progress.setValue(pct)
        self.exec_pct.setText(f"{pct}%")

        self.exec_title.setText(
            "Busca em andamento"
            if state.news_busy
            else "Busca concluída com sucesso"
        )

        demand_count = sum(
            1
            for news in rows
            if getattr(news, "demand", False)
        )

        self.exec_sub.setText(
            f"{demand_count} demanda(s)  •  "
            f"{found} resultado(s)  •  "
            f"{fresh} novo(s)"
        )

        if state.news_busy:
            source = (
                getattr(progress, "currentSource", "")
                or "Preparando"
            )
            query = (
                getattr(progress, "currentQuery", "")
                or "consultas"
            )
            self.exec_detail.setText(
                f"{source} • {query}"
            )
        else:
            self.exec_detail.setText(
                f"A busca foi concluída. "
                f"{found} notícia(s) encontrada(s) nesta execução."
            )

        self.metric_labels["pct"].setText(f"{pct}%")
        self.metric_labels["found"].setText(str(found))
        self.metric_labels["new"].setText(str(fresh))
        self.metric_labels["errors"].setText(str(errors))
        self.metric_labels["steps"].setText(
            f"{completed}/{total}"
        )
        self.metric_labels["time"].setText(
            _duration(state.last_news_duration_ms)
        )
