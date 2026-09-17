from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from PySide6.QtCore import QDate, Qt, QTime, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDateEdit, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QProgressBar, QPushButton, QScrollArea, QTimeEdit,
    QVBoxLayout, QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState


def _format_time(ms: int) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


def _duration(ms: int) -> str:
    sec = max(0, int(ms // 1000))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _open_url(url: str) -> None:
    if url:
        QDesktopServices.openUrl(QUrl(url))


def _copy(text: str) -> None:
    QApplication.clipboard().setText(text)


def _whatsapp(title: str, url: str) -> None:
    QDesktopServices.openUrl(QUrl("https://wa.me/?text=" + quote(f"{title}\n{url}")))


class NewsPage(QWidget):
    """Aba Notícias com layout compacto e lista contínua em um único scroll."""

    extract_requested = Signal(str)

    def __init__(self, controller: MainUiController) -> None:
        super().__init__()
        self.controller = controller

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(7)

        # Banner compacto.
        banner = QFrame()
        banner.setObjectName("newsBanner")
        banner.setMaximumHeight(108)

        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 9, 18, 9)
        bl.setSpacing(12)

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
        subtitle.setWordWrap(True)

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

        # Busca + filtros em bloco compacto.
        filters = QFrame()
        filters.setObjectName("newsCard")

        fl = QVBoxLayout(filters)
        fl.setContentsMargins(10, 8, 10, 8)
        fl.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.query = QLineEdit()
        self.query.setPlaceholderText("⌕  Buscar nas notícias (título, fonte, termo...)")
        self.query.setObjectName("newsSearch")
        top.addWidget(self.query, 1)

        self.search24 = QPushButton("↻  Buscar últimas 24h")
        self.search24.setObjectName("newsPrimary")
        self.search24.clicked.connect(
            lambda: self.controller.search_news(*self.controller.period_last_hours(24))
        )
        top.addWidget(self.search24)

        self.only_demands = QCheckBox("Só demandas")
        top.addWidget(self.only_demands)

        fl.addLayout(top)

        periods = QHBoxLayout()
        periods.setSpacing(6)

        self.period_buttons: list[QPushButton] = []

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

        # Andamento + métricas.
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

        self.metric_labels: dict[str, QLabel] = {}

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

        # Cabeçalho da lista: sem paginação.
        list_head = QHBoxLayout()
        list_head.setContentsMargins(2, 0, 2, 0)

        self.count = QLabel("▣  Notícias encontradas")
        self.count.setObjectName("newsListTitle")
        list_head.addWidget(self.count)

        list_head.addStretch()

        self.sort_label = QLabel("Mais recentes ⌄")
        self.sort_label.setObjectName("sortPill")
        list_head.addWidget(self.sort_label)

        root.addLayout(list_head)

        # Um único scroll com TODAS as matérias filtradas.
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("newsScroll")
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.list_widget = QWidget()

        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 3, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.list_widget)
        root.addWidget(self.scroll, 1)

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
        QLabel#newsKicker {
            color:#087AF7;
            font-size:10px;
            font-weight:800;
        }
        QLabel#newsTitle {
            color:#08245F;
            font-size:24px;
            font-weight:900;
        }
        QLabel#newsSubtitle {
            color:#5C73A4;
            font-size:11px;
        }
        QLabel#newsBannerArt {
            color:#A9CFF8;
            font-size:31px;
        }

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

        QScrollArea#newsScroll {
            border:0;
            background:transparent;
        }

        QScrollArea#newsScroll QWidget#qt_scrollarea_viewport {
            background:transparent;
        }

        QFrame#newsItem {
            background:white;
            border:1px solid #DCE9F6;
            border-radius:9px;
        }

        QLabel#sourceAvatar {
            background:#087AF7;
            color:white;
            border-radius:8px;
            font-size:14px;
            font-weight:900;
            min-width:36px;
            max-width:36px;
            min-height:36px;
            max-height:36px;
        }

        QLabel#itemMeta {
            color:#5272A1;
            font-size:10px;
        }

        QLabel#itemTitle {
            color:#08245F;
            font-size:12px;
            font-weight:800;
        }

        QLabel#itemSummary {
            color:#6079A5;
            font-size:10px;
        }

        QLabel#termTag {
            background:#EAF4FF;
            color:#087AF7;
            border-radius:6px;
            padding:5px 8px;
            font-size:9px;
            font-weight:800;
        }

        QPushButton#itemAction {
            background:white;
            color:#0C3974;
            border:1px solid #C9DDF2;
            border-radius:7px;
            padding:6px 9px;
            font-size:10px;
            font-weight:700;
        }

        QPushButton#itemWhats {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #BFE8D5;
            border-radius:7px;
            padding:6px 9px;
            font-size:10px;
            font-weight:700;
        }

        QPushButton#itemExtract {
            background:#F4ECFF;
            color:#8B3CF6;
            border:1px solid #DFC6FF;
            border-radius:7px;
            padding:6px 9px;
            font-size:10px;
            font-weight:700;
        }
        """

    def _run_period(self, hours: int | None) -> None:
        for button in self.period_buttons:
            button.setChecked(False)

        sender = self.sender()
        if isinstance(sender, QPushButton):
            sender.setChecked(True)

        if hours is None:
            self.controller.search_news(*self.controller.period_today())
        else:
            self.controller.search_news(*self.controller.period_last_hours(hours))

    def _period(self) -> None:
        start = self.start_date.date().toString("yyyy-MM-dd")
        st = self.start_time.time().toString("HH:mm")
        end = self.end_date.date().toString("yyyy-MM-dd")
        et = self.end_time.time().toString("HH:mm")

        parsed = self.controller.parse_period(start, st, end, et)

        if parsed:
            self.controller.search_news(*parsed)

    def _filters_changed(self, *_args) -> None:
        self.refresh(self.controller.state)

    def _rows(self, state: UiState):
        q = self.query.text().strip().lower()

        rows = [
            news
            for news in state.news
            if (
                not self.only_demands.isChecked()
                or news.demand
            )
            and (
                not q
                or q
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

    def _clear_items(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

    def _news_item(self, news) -> QFrame:
        card = QFrame()
        card.setObjectName("newsItem")

        row = QHBoxLayout(card)
        row.setContentsMargins(11, 7, 11, 7)
        row.setSpacing(9)

        avatar = QLabel((news.source or "N")[:2].upper())
        avatar.setObjectName("sourceAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(1)

        meta = QLabel(f"{news.source}  •  {_format_time(news.date)}")
        meta.setObjectName("itemMeta")

        title = QLabel(news.title)
        title.setObjectName("itemTitle")
        title.setWordWrap(True)

        summary_text = (
            getattr(news, "summary", "")
            or getattr(news, "description", "")
            or ""
        )

        summary = QLabel(summary_text)
        summary.setObjectName("itemSummary")
        summary.setWordWrap(True)

        info.addWidget(meta)
        info.addWidget(title)

        if summary.text().strip():
            info.addWidget(summary)

        row.addLayout(info, 1)

        tag_text = news.matchedDemand or news.matchedTerm or ""

        if tag_text:
            tag = QLabel(tag_text.upper())
            tag.setObjectName("termTag")
            tag.setMaximumWidth(150)
            row.addWidget(tag)

        actions = QHBoxLayout()
        actions.setSpacing(5)

        for text, object_name, fn in (
            ("↗  Abrir matéria", "itemAction", lambda: _open_url(news.link)),
            ("◉  WhatsApp", "itemWhats", lambda: _whatsapp(news.title, news.link)),
            ("▣  Copiar link", "itemAction", lambda: _copy(news.link)),
            ("⇩  Extrair matéria", "itemExtract", lambda: self.extract_requested.emit(news.link)),
        ):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.clicked.connect(fn)
            actions.addWidget(button)

        row.addLayout(actions)
        return card

    def refresh(self, state: UiState) -> None:
        rows = self._rows(state)

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
            if getattr(news, "demand", "")
        )

        self.exec_sub.setText(
            f"{demand_count} demanda(s)  •  "
            f"{found} resultado(s)  •  "
            f"{fresh} novo(s)"
        )

        if state.news_busy:
            source = getattr(progress, "currentSource", "") or "Preparando"
            query = getattr(progress, "currentQuery", "") or "consultas"
            self.exec_detail.setText(f"{source} • {query}")
        else:
            self.exec_detail.setText(
                f"A busca foi concluída. "
                f"{found} notícia(s) encontrada(s) nesta execução."
            )

        self.metric_labels["pct"].setText(f"{pct}%")
        self.metric_labels["found"].setText(str(found))
        self.metric_labels["new"].setText(str(fresh))
        self.metric_labels["errors"].setText(str(errors))
        self.metric_labels["steps"].setText(f"{completed}/{total}")
        self.metric_labels["time"].setText(
            _duration(state.last_news_duration_ms)
        )

        # Sem paginação: todas as matérias entram no mesmo scroll.
        self._clear_items()

        for news in rows:
            self.list_layout.insertWidget(
                self.list_layout.count() - 1,
                self._news_item(news),
            )
