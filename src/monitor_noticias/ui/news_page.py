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
    extract_requested = Signal(str)

    PAGE_SIZE = 5

    def __init__(self, controller: MainUiController) -> None:
        super().__init__()
        self.controller = controller
        self.current_page = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Banner
        banner = QFrame()
        banner.setObjectName("newsBanner")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(18, 12, 22, 12)
        left = QVBoxLayout()
        kicker = QLabel("CENTRAL DE INTELIGÊNCIA DE MÍDIA")
        kicker.setObjectName("newsKicker")
        title = QLabel("Notícias")
        title.setObjectName("newsTitle")
        subtitle = QLabel("Acompanhe matérias em tempo real e transforme\ninformação em decisões estratégicas.")
        subtitle.setObjectName("newsSubtitle")
        left.addWidget(kicker)
        left.addWidget(title)
        left.addWidget(subtitle)
        bl.addLayout(left, 1)
        art = QLabel("◯       ◌       ▤")
        art.setObjectName("newsBannerArt")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(art)
        root.addWidget(banner)

        # Busca e filtros
        filters = QFrame()
        filters.setObjectName("newsCard")
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)
        top = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("⌕  Buscar nas notícias (título, fonte, termo...)")
        self.query.setObjectName("newsSearch")
        top.addWidget(self.query, 1)
        self.search24 = QPushButton("↻  Buscar últimas 24h")
        self.search24.setObjectName("newsPrimary")
        self.search24.clicked.connect(lambda: self.controller.search_news(*self.controller.period_last_hours(24)))
        top.addWidget(self.search24)
        self.only_demands = QCheckBox("Só demandas")
        top.addWidget(self.only_demands)
        fl.addLayout(top)

        periods = QHBoxLayout()
        periods.setSpacing(8)
        self.period_buttons = []
        for label, hours in (("Hoje", None), ("24 horas", 24), ("7 dias", 168), ("30 dias", 720)):
            btn = QPushButton(label)
            btn.setObjectName("periodButton")
            btn.setCheckable(True)
            if label == "Hoje":
                btn.setChecked(True)
            btn.clicked.connect(lambda _=False, h=hours: self._run_period(h))
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
        pl.setContentsMargins(8, 6, 8, 6)
        today = QDate.currentDate()
        self.start_date = QDateEdit(today.addDays(-1))
        self.start_time = QTimeEdit(QTime(0, 0))
        self.end_date = QDateEdit(today)
        self.end_time = QTimeEdit(QTime(23, 59))
        self.period_go = QPushButton("Buscar período")
        self.period_go.setObjectName("newsPrimary")
        for w in (self.start_date, self.start_time, self.end_date, self.end_time, self.period_go):
            pl.addWidget(w)
        self.period_box.hide()
        self.custom.toggled.connect(self.period_box.setVisible)
        self.period_go.clicked.connect(self._period)
        fl.addWidget(self.period_box)
        root.addWidget(filters)

        # Execução + métricas
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        progress_card = QFrame()
        progress_card.setObjectName("newsCard")
        pcl = QVBoxLayout(progress_card)
        pcl.setContentsMargins(14, 10, 14, 10)
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
        ml.setContentsMargins(8, 8, 8, 8)
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
            lay.setContentsMargins(10, 6, 10, 6)
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

        # Título/lista/paginação
        list_head = QHBoxLayout()
        self.count = QLabel("▣  Notícias encontradas")
        self.count.setObjectName("newsListTitle")
        list_head.addWidget(self.count)
        list_head.addStretch()
        self.sort_label = QLabel("Mais recentes ⌄")
        self.sort_label.setObjectName("sortPill")
        list_head.addWidget(self.sort_label)
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setObjectName("pagerButton")
        self.prev_btn.clicked.connect(self._prev_page)
        self.page_label = QLabel("1 de 1")
        self.page_label.setObjectName("newsMuted")
        self.next_btn = QPushButton("›")
        self.next_btn.setObjectName("pagerButton")
        self.next_btn.clicked.connect(self._next_page)
        list_head.addWidget(self.prev_btn)
        list_head.addWidget(self.page_label)
        list_head.addWidget(self.next_btn)
        root.addLayout(list_head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("newsScroll")
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(7)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_widget)
        root.addWidget(self.scroll, 1)

        self.query.textChanged.connect(self._filters_changed)
        self.only_demands.toggled.connect(self._filters_changed)

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#newsBanner { background:#F2F8FF; border:1px solid #D6E6F7; border-radius:14px; }
        QLabel#newsKicker { color:#087AF7; font-size:10px; font-weight:800; }
        QLabel#newsTitle { color:#08245F; font-size:27px; font-weight:900; }
        QLabel#newsSubtitle { color:#5C73A4; font-size:12px; }
        QLabel#newsBannerArt { color:#A9CFF8; font-size:38px; min-width:330px; }
        QFrame#newsCard { background:white; border:1px solid #D6E6F7; border-radius:12px; }
        QLineEdit#newsSearch { min-height:38px; padding:0 12px; }
        QPushButton#newsPrimary { background:#0A7DF8; color:white; border:0; border-radius:8px; padding:9px 15px; font-weight:800; }
        QPushButton#periodButton { background:white; color:#153E75; border:1px solid #C9DCF2; border-radius:8px; padding:7px 14px; font-weight:700; }
        QPushButton#periodButton:checked { background:#EAF4FF; color:#087AF7; border:1px solid #087AF7; }
        QFrame#customPeriod { background:#F8FBFF; border:1px solid #DDE9F6; border-radius:8px; }
        QLabel#execTitle { color:#08245F; font-size:16px; font-weight:900; }
        QLabel#execPct { color:#08A66B; font-size:22px; font-weight:900; }
        QLabel#newsMuted { color:#6079A5; font-size:11px; }
        QProgressBar#newsProgress { background:#E6F0FA; border:0; border-radius:4px; max-height:10px; }
        QProgressBar#newsProgress::chunk { background:#16B97E; border-radius:4px; }
        QLabel#successStrip { background:#EAF9F2; color:#078B5F; border:1px solid #C4ECD9; border-radius:7px; padding:6px 10px; }
        QFrame#metricMini { border-right:1px solid #E2ECF6; }
        QLabel#metricMiniValue { font-size:19px; font-weight:900; }
        QLabel#metricMiniValue[tone='green'] { color:#08A66B; }
        QLabel#metricMiniValue[tone='orange'] { color:#F0A000; }
        QLabel#metricMiniValue[tone='purple'] { color:#8B3CF6; }
        QLabel#metricMiniValue[tone='red'] { color:#EA3158; }
        QLabel#metricMiniValue[tone='blue'] { color:#087AF7; }
        QLabel#metricMiniCaption { color:#5C73A4; font-size:10px; }
        QPushButton#stopButton { background:#FFF1F4; color:#E03155; border:1px solid #FFB8C8; border-radius:8px; padding:8px 14px; }
        QLabel#newsListTitle { color:#08245F; font-size:17px; font-weight:900; }
        QLabel#sortPill { background:white; color:#375B88; border:1px solid #D5E4F4; border-radius:8px; padding:7px 12px; }
        QPushButton#pagerButton { background:white; color:#087AF7; border:1px solid #D5E4F4; border-radius:8px; min-width:34px; padding:5px 8px; }
        QScrollArea#newsScroll { border:0; background:transparent; }
        QFrame#newsItem { background:white; border:1px solid #DCE9F6; border-radius:10px; }
        QLabel#sourceAvatar { background:#087AF7; color:white; border-radius:8px; font-size:15px; font-weight:900; min-width:34px; max-width:34px; min-height:34px; max-height:34px; }
        QLabel#itemMeta { color:#5272A1; font-size:10px; }
        QLabel#itemTitle { color:#08245F; font-size:12px; font-weight:800; }
        QLabel#itemSummary { color:#6079A5; font-size:10px; }
        QLabel#termTag { background:#EAF4FF; color:#087AF7; border-radius:6px; padding:5px 8px; font-size:9px; font-weight:800; }
        QPushButton#itemAction { background:white; color:#0C3974; border:1px solid #C9DDF2; border-radius:7px; padding:7px 10px; font-weight:700; }
        QPushButton#itemWhats { background:#EAF9F2; color:#078B5F; border:1px solid #BFE8D5; border-radius:7px; padding:7px 10px; font-weight:700; }
        QPushButton#itemExtract { background:#F4ECFF; color:#8B3CF6; border:1px solid #DFC6FF; border-radius:7px; padding:7px 10px; font-weight:700; }
        """

    def _run_period(self, hours: int | None) -> None:
        self.current_page = 0
        for b in self.period_buttons:
            b.setChecked(False)
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
            self.current_page = 0
            self.controller.search_news(*parsed)

    def _filters_changed(self, *_args) -> None:
        self.current_page = 0
        self.refresh(self.controller.state)

    def _rows(self, state: UiState):
        q = self.query.text().strip().lower()
        rows = [
            n for n in state.news
            if (not self.only_demands.isChecked() or n.demand)
            and (not q or q in f"{n.title} {n.source} {n.matchedTerm} {n.matchedDemand}".lower())
        ]
        return sorted(rows, key=lambda n: getattr(n, "date", 0), reverse=True)

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh(self.controller.state)

    def _next_page(self) -> None:
        rows = self._rows(self.controller.state)
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        if self.current_page + 1 < pages:
            self.current_page += 1
            self.refresh(self.controller.state)

    def _clear_items(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _news_item(self, news) -> QFrame:
        card = QFrame()
        card.setObjectName("newsItem")
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        avatar = QLabel((news.source or "N")[:2].upper())
        avatar.setObjectName("sourceAvatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(avatar)

        info = QVBoxLayout()
        info.setSpacing(2)
        meta = QLabel(f"{news.source}  •  {_format_time(news.date)}")
        meta.setObjectName("itemMeta")
        title = QLabel(news.title)
        title.setObjectName("itemTitle")
        title.setWordWrap(True)
        summary = QLabel(getattr(news, "summary", "") or getattr(news, "description", "") or "")
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
            tag.setMaximumWidth(140)
            row.addWidget(tag)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        for text, obj, fn in (
            ("↗  Abrir matéria", "itemAction", lambda: _open_url(news.link)),
            ("◉  WhatsApp", "itemWhats", lambda: _whatsapp(news.title, news.link)),
            ("▣  Copiar link", "itemAction", lambda: _copy(news.link)),
            ("⇩  Extrair matéria", "itemExtract", lambda: self.extract_requested.emit(news.link)),
        ):
            b = QPushButton(text)
            b.setObjectName(obj)
            b.clicked.connect(fn)
            actions.addWidget(b)
        row.addLayout(actions)
        return card

    def refresh(self, state: UiState) -> None:
        rows = self._rows(state)
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, pages - 1)
        start = self.current_page * self.PAGE_SIZE
        visible = rows[start:start + self.PAGE_SIZE]

        self.count.setText(f"▣  Notícias encontradas   {len(rows)} resultado(s) para o período selecionado")
        self.page_label.setText(f"{self.current_page + 1} de {pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page + 1 < pages)

        self.search24.setEnabled(not state.news_busy and self.controller.search_available)
        self.period_go.setEnabled(not state.news_busy and self.controller.search_available)
        self.stop.setVisible(state.news_busy)

        progress = state.news_progress
        fraction = max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0)))) if state.news_busy else 1.0
        pct = round(fraction * 100)
        found = int(getattr(progress, "found", 0))
        errors = int(getattr(progress, "errors", 0))
        completed = int(getattr(progress, "completed", 0))
        total = int(getattr(progress, "total", 0))
        fresh = len(state.new_news_links)

        self.progress.setValue(pct)
        self.exec_pct.setText(f"{pct}%")
        self.exec_title.setText("Busca em andamento" if state.news_busy else "Busca concluída com sucesso")
        self.exec_sub.setText(f"{sum(1 for n in rows if getattr(n, 'demand', ''))} demanda(s)  •  {found} resultado(s)  •  {fresh} novo(s)")
        if state.news_busy:
            source = getattr(progress, "currentSource", "") or "Preparando"
            query = getattr(progress, "currentQuery", "") or "consultas"
            self.exec_detail.setText(f"{source} • {query}")
        else:
            self.exec_detail.setText(f"A busca foi concluída. {found} notícia(s) encontrada(s) nesta execução.")

        self.metric_labels["pct"].setText(f"{pct}%")
        self.metric_labels["found"].setText(str(found))
        self.metric_labels["new"].setText(str(fresh))
        self.metric_labels["errors"].setText(str(errors))
        self.metric_labels["steps"].setText(f"{completed}/{total}")
        self.metric_labels["time"].setText(_duration(state.last_news_duration_ms))

        self._clear_items()
        for news in visible:
            self.list_layout.insertWidget(self.list_layout.count() - 1, self._news_item(news))
