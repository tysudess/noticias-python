from __future__ import annotations

from collections import Counter
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState


def _card(object_name: str = "homeCard") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(object_name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 15, 18, 15)
    layout.setSpacing(8)
    return frame, layout


class HomePage(QWidget):
    navigate = Signal(str)

    def __init__(self, controller: MainUiController) -> None:
        super().__init__()
        self.controller = controller

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(12, 8, 12, 10)
        self.root.setSpacing(11)

        self.metric_values: dict[str, QLabel] = {}
        self.metric_subtitles: dict[str, QLabel] = {}

        self._build_metrics()
        self._build_monitor_and_actions()
        self._build_schedule_and_summary()
        self._build_bottom_cards()

        self.root.addStretch(1)
        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#metricCard {
            background:#FFFFFF;
            border:1px solid #D3E4F5;
            border-radius:13px;
        }
        QLabel#metricTitle {
            color:#173E75;
            font-size:12px;
            font-weight:800;
        }
        QLabel#metricValue {
            color:#071D55;
            font-size:29px;
            font-weight:900;
        }
        QLabel#metricSubtitle {
            color:#627CA7;
            font-size:10px;
        }
        QLabel#metricDelta {
            color:#00A96E;
            font-size:11px;
            font-weight:900;
        }
        QLabel#metricIcon, QLabel#scheduleIcon {
            border-radius:12px;
            font-size:23px;
            font-weight:900;
        }
        QLabel#metricIcon[tone='blue'], QLabel#scheduleIcon[tone='blue'] {
            background:#DDEEFF;
            color:#0C77F5;
        }
        QLabel#metricIcon[tone='purple'], QLabel#scheduleIcon[tone='purple'] {
            background:#EFE2FF;
            color:#743AF3;
        }
        QLabel#metricIcon[tone='green'], QLabel#scheduleIcon[tone='green'] {
            background:#DDF8EC;
            color:#049E68;
        }
        QLabel#metricIcon[tone='orange'], QLabel#scheduleIcon[tone='orange'] {
            background:#FFF0C9;
            color:#E69A00;
        }
        QLabel#metricIcon[tone='pink'] {
            background:#FFE1ED;
            color:#C4005C;
        }

        QFrame#heroCard, QFrame#homeCard, QFrame#quickCard, QFrame#tipCard {
            background:#FFFFFF;
            border:1px solid #D3E4F5;
            border-radius:14px;
        }

        QLabel#heroRadioIcon {
            background:#E9F4FF;
            color:#0B79F6;
            border-radius:34px;
            font-size:38px;
            font-weight:900;
        }
        QLabel#heroTitle {
            color:#08245F;
            font-size:23px;
            font-weight:900;
        }
        QLabel#heroSubtitle {
            color:#5873A0;
            font-size:12px;
        }

        QFrame#readyCard {
            background:#EAF9F2;
            border:1px solid #C2ECDB;
            border-radius:10px;
        }
        QLabel#readyTitle {
            color:#078B5F;
            font-size:14px;
            font-weight:900;
        }
        QLabel#readyText {
            color:#3F6B60;
            font-size:11px;
        }

        QLabel#searchProgressTitle {
            color:#173E75;
            font-size:11px;
            font-weight:800;
        }
        QLabel#searchProgressValue {
            color:#087AF7;
            font-size:15px;
            font-weight:900;
        }
        QProgressBar#homeSearchProgress {
            background:#DCEBFA;
            border:0;
            border-radius:5px;
            min-height:10px;
            max-height:10px;
        }
        QProgressBar#homeSearchProgress::chunk {
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:0,
                stop:0 #0A7CF6,
                stop:1 #16B97E
            );
            border-radius:5px;
        }

        QFrame#monitorVisual {
            background:#F4F9FF;
            border:0;
            border-radius:18px;
        }
        QLabel#monitorScreen {
            color:#0B4D9C;
            font-size:70px;
            font-weight:900;
        }
        QLabel#monitorLines {
            color:#72A9E8;
            font-size:14px;
            font-weight:700;
        }

        QLabel#sectionTitle {
            color:#08245F;
            font-size:17px;
            font-weight:900;
        }
        QLabel#sectionSubtitle {
            color:#617BA5;
            font-size:11px;
        }

        QPushButton#quickTile {
            background:#F8FBFF;
            color:#0A3A79;
            border:1px solid #D4E4F5;
            border-radius:12px;
            padding:12px;
            font-size:11px;
            font-weight:800;
            text-align:center;
            min-height:96px;
        }
        QPushButton#quickTile:hover {
            background:#EDF6FF;
            border-color:#91BDEA;
        }
        QPushButton#quickTilePrimary {
            background:qlineargradient(
                x1:0,y1:0,x2:0,y2:1,
                stop:0 #168DFA,
                stop:1 #0878EA
            );
            color:white;
            border:0;
            border-radius:12px;
            padding:12px;
            font-size:11px;
            font-weight:800;
            text-align:center;
            min-height:96px;
        }

        QFrame#scheduleBox {
            background:#F8FBFF;
            border:1px solid #DFEBF7;
            border-radius:10px;
        }
        QLabel#scheduleTitle {
            color:#0A326D;
            font-size:11px;
            font-weight:900;
        }
        QLabel#scheduleDetail {
            color:#526E9B;
            font-size:10px;
        }

        QLabel#smallPill {
            background:#F8FBFF;
            color:#365D8F;
            border:1px solid #D6E5F4;
            border-radius:8px;
            padding:6px 10px;
            font-size:10px;
        }

        QFrame#graphFrame {
            background:white;
            border:0;
        }
        QLabel#graphText {
            color:#7EA8DD;
            font-family:"Consolas";
            font-size:10px;
        }
        QLabel#graphLegend {
            color:#426891;
            font-size:10px;
        }

        QPushButton#linkButton {
            background:transparent;
            color:#087AF7;
            border:0;
            padding:2px 4px;
            min-height:18px;
            font-size:10px;
            font-weight:800;
        }

        QFrame#rankRow {
            background:#F8FBFF;
            border:1px solid #E0EBF6;
            border-radius:7px;
        }
        QLabel#rankNumber {
            background:#E7F2FF;
            color:#087AF7;
            border-radius:8px;
            font-size:9px;
            font-weight:900;
            min-width:17px;
            max-width:17px;
            min-height:17px;
            max-height:17px;
        }
        QLabel#rankVehicle {
            color:#183E72;
            font-size:10px;
            font-weight:700;
        }
        QLabel#rankCount {
            color:#087AF7;
            font-size:10px;
            font-weight:900;
        }

        QLabel#listText {
            color:#244B7B;
            font-size:11px;
        }

        QLabel#tipText {
            background:#EDF7FF;
            color:#355D89;
            border-radius:10px;
            padding:12px;
            font-size:11px;
        }
        QLabel#dots {
            color:#0A7BF7;
            font-size:12px;
        }
        """

    def _build_metrics(self) -> None:
        wrap = QWidget()
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)

        specs = [
            ("news", "▤", "Notícias 24h", "na janela atual", "blue"),
            ("videos", "▶", "Vídeos armazenados", "relevantes na base", "purple"),
            ("today", "▰", "Vídeos hoje", "capturados hoje", "green"),
            ("demands", "▣", "Demandas", "0 ativas", "orange"),
            ("sources", "●", "Fontes", "especializadas", "pink"),
        ]

        for col, (key, icon, title, subtitle, tone) in enumerate(specs):
            card = QFrame()
            card.setObjectName("metricCard")
            card.setMinimumHeight(105)

            row = QHBoxLayout(card)
            row.setContentsMargins(14, 11, 14, 11)
            row.setSpacing(12)

            badge = QLabel(icon)
            badge.setObjectName("metricIcon")
            badge.setProperty("tone", tone)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(52, 52)

            text = QVBoxLayout()
            text.setSpacing(0)

            title_label = QLabel(title)
            title_label.setObjectName("metricTitle")
            value = QLabel("0")
            value.setObjectName("metricValue")
            sub = QLabel(subtitle)
            sub.setObjectName("metricSubtitle")

            text.addWidget(title_label)
            text.addWidget(value)
            text.addWidget(sub)

            row.addWidget(badge)
            row.addLayout(text, 1)

            if key == "sources":
                delta = QLabel("↗ +2%")
                delta.setObjectName("metricDelta")
                row.addWidget(delta, 0, Qt.AlignmentFlag.AlignTop)

            self.metric_values[key] = value
            self.metric_subtitles[key] = sub
            grid.addWidget(card, 0, col)

        self.root.addWidget(wrap)

    def _build_monitor_and_actions(self) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero.setMinimumHeight(260)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 16, 22, 16)
        hero_layout.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(9)

        title_row = QHBoxLayout()
        radio = QLabel("◉")
        radio.setObjectName("heroRadioIcon")
        radio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radio.setFixedSize(68, 68)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Central pronta para monitorar")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            "As buscas e os resultados são atualizados em tempo real."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_row.addWidget(radio)
        title_row.addLayout(title_box, 1)
        left.addLayout(title_row)

        status = QFrame()
        status.setObjectName("readyCard")
        status_l = QVBoxLayout(status)
        status_l.setContentsMargins(17, 12, 17, 12)
        status_l.setSpacing(3)

        self.ready_title = QLabel("●   Status: Pronto")
        self.ready_title.setObjectName("readyTitle")
        self.ready_text = QLabel("Monitoramento ativo e funcionando normalmente.")
        self.ready_text.setObjectName("readyText")
        self.ready_text.setWordWrap(True)

        status_l.addWidget(self.ready_title)
        status_l.addWidget(self.ready_text)
        left.addWidget(status)

        progress_box = QFrame()
        progress_box.setObjectName("monitorVisual")
        progress_l = QVBoxLayout(progress_box)
        progress_l.setContentsMargins(14, 10, 14, 10)
        progress_l.setSpacing(5)

        p_head = QHBoxLayout()
        self.search_progress_title = QLabel("Busca atual")
        self.search_progress_title.setObjectName("searchProgressTitle")
        self.search_progress_value = QLabel("0%")
        self.search_progress_value.setObjectName("searchProgressValue")

        p_head.addWidget(self.search_progress_title)
        p_head.addStretch()
        p_head.addWidget(self.search_progress_value)

        self.search_progress = QProgressBar()
        self.search_progress.setObjectName("homeSearchProgress")
        self.search_progress.setRange(0, 100)
        self.search_progress.setTextVisible(False)
        self.search_progress.setValue(0)

        self.search_progress_detail = QLabel("Nenhuma busca em andamento.")
        self.search_progress_detail.setObjectName("readyText")

        progress_l.addLayout(p_head)
        progress_l.addWidget(self.search_progress)
        progress_l.addWidget(self.search_progress_detail)

        left.addWidget(progress_box)

        visual = QFrame()
        visual.setObjectName("monitorVisual")
        visual.setMinimumWidth(235)

        visual_l = QVBoxLayout(visual)
        visual_l.setContentsMargins(16, 10, 16, 10)
        visual_l.setSpacing(2)

        screen = QLabel("▭")
        screen.setObjectName("monitorScreen")
        screen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        monitor_text = QLabel("▣  ▬▬▬\n▣  ▬▬▬\n▣  ▬▬▬")
        monitor_text.setObjectName("monitorLines")
        monitor_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        visual_l.addStretch()
        visual_l.addWidget(screen)
        visual_l.addWidget(monitor_text)
        visual_l.addStretch()

        hero_layout.addLayout(left, 3)
        hero_layout.addWidget(visual, 2)
        layout.addWidget(hero, 3)

        quick, ql = _card("quickCard")
        quick.setMinimumHeight(260)
        ql.setContentsMargins(18, 15, 18, 15)
        ql.setSpacing(8)

        qtitle = QLabel("⚡   Ações rápidas")
        qtitle.setObjectName("sectionTitle")
        qsub = QLabel("Execute as principais buscas com um clique.")
        qsub.setObjectName("sectionSubtitle")

        ql.addWidget(qtitle)
        ql.addWidget(qsub)

        tiles = QHBoxLayout()
        tiles.setSpacing(8)

        self.news_button = QPushButton(
            "⌕\n\nBuscar notícias\nVarredura agora"
        )
        self.news_button.setObjectName("quickTilePrimary")
        self.news_button.clicked.connect(self.controller.search_news)

        self.video_button = QPushButton(
            "▶\n\nBuscar vídeos\nPesquisar agora"
        )
        self.video_button.setObjectName("quickTile")
        self.video_button.clicked.connect(self.controller.search_videos)

        self.demands_button = QPushButton(
            "▣\n\nBuscar demandas\nConsultar ativas"
        )
        self.demands_button.setObjectName("quickTile")
        self.demands_button.clicked.connect(self.controller.search_all_demands)

        tiles.addWidget(self.news_button, 1)
        tiles.addWidget(self.video_button, 1)
        tiles.addWidget(self.demands_button, 1)

        ql.addLayout(tiles)
        ql.addStretch()

        layout.addWidget(quick, 2)
        self.root.addWidget(row)

    def _build_schedule_and_summary(self) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        schedule, sl = _card("homeCard")
        schedule.setMinimumHeight(178)

        title = QLabel("◴   Agendamento automático")
        title.setObjectName("sectionTitle")
        sub = QLabel("O sistema executa buscas automaticamente nos horários definidos.")
        sub.setObjectName("sectionSubtitle")
        sub.setWordWrap(True)

        sl.addWidget(title)
        sl.addWidget(sub)

        cells = QHBoxLayout()
        cells.setSpacing(8)

        self.news_schedule = self._schedule_box("▤", "Notícias", "a cada 30 min", "blue")
        self.demand_schedule = self._schedule_box("▣", "Demandas", "a cada 60 min", "orange")
        self.video_schedule = self._schedule_box(
            "▶", "Vídeos", "08:00, 12:00, 15:00, 19:00, 21:00", "purple"
        )

        cells.addWidget(self.news_schedule)
        cells.addWidget(self.demand_schedule)
        cells.addWidget(self.video_schedule)
        sl.addLayout(cells)

        summary, dl = _card("homeCard")
        summary.setMinimumHeight(178)

        head = QHBoxLayout()
        title = QLabel("▥   Resumo do dia")
        title.setObjectName("sectionTitle")
        period = QLabel("Últimas 24 horas   ˅")
        period.setObjectName("smallPill")

        head.addWidget(title)
        head.addStretch()
        head.addWidget(period)
        dl.addLayout(head)

        sub = QLabel("Panorama geral das últimas 24 horas.")
        sub.setObjectName("sectionSubtitle")
        dl.addWidget(sub)

        graph = QFrame()
        graph.setObjectName("graphFrame")
        gl = QVBoxLayout(graph)
        gl.setContentsMargins(12, 5, 12, 5)

        self.graph_text = QLabel(
            "40 ┤\n30 ┤\n20 ┤\n10 ┤\n 0 ┼─●──●──●──●──●──●──●──●──●──●──●──●─"
        )
        self.graph_text.setObjectName("graphText")
        self.graph_text.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        legend = QLabel("● Notícias     ● Vídeos     ● Demandas")
        legend.setObjectName("graphLegend")

        gl.addWidget(self.graph_text)
        gl.addWidget(legend)
        dl.addWidget(graph)

        layout.addWidget(schedule, 1)
        layout.addWidget(summary, 1)
        self.root.addWidget(row)

    def _schedule_box(self, icon: str, title: str, detail: str, tone: str) -> QFrame:
        box = QFrame()
        box.setObjectName("scheduleBox")
        box.setProperty("tone", tone)

        row = QHBoxLayout(box)
        row.setContentsMargins(11, 8, 11, 8)
        row.setSpacing(8)

        badge = QLabel(icon)
        badge.setObjectName("scheduleIcon")
        badge.setProperty("tone", tone)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(38, 38)

        text = QVBoxLayout()
        text.setSpacing(0)
        title_l = QLabel(title)
        title_l.setObjectName("scheduleTitle")
        detail_l = QLabel(detail)
        detail_l.setObjectName("scheduleDetail")
        detail_l.setWordWrap(True)

        text.addWidget(title_l)
        text.addWidget(detail_l)
        row.addWidget(badge)
        row.addLayout(text, 1)
        return box

    def _build_bottom_cards(self) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        sources, sl = _card("homeCard")
        activities, al = _card("homeCard")
        tips, tl = _card("tipCard")

        for card in (sources, activities, tips):
            card.setMinimumHeight(198)

        # TOP 10 veículos.
        head = QHBoxLayout()
        title = QLabel("●   Top 10 veículos")
        title.setObjectName("sectionTitle")
        more = QPushButton("Ver todas")
        more.setObjectName("linkButton")
        more.clicked.connect(lambda: self.navigate.emit("SOURCES"))
        head.addWidget(title)
        head.addStretch()
        head.addWidget(more)
        sl.addLayout(head)

        sub = QLabel("Veículos com mais matérias encontradas.")
        sub.setObjectName("sectionSubtitle")
        sl.addWidget(sub)

        self.rank_grid = QGridLayout()
        self.rank_grid.setHorizontalSpacing(7)
        self.rank_grid.setVerticalSpacing(4)
        self.rank_rows: list[tuple[QLabel, QLabel, QLabel]] = []

        for idx in range(10):
            frame = QFrame()
            frame.setObjectName("rankRow")
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(5, 3, 6, 3)
            fl.setSpacing(5)

            rank = QLabel(str(idx + 1))
            rank.setObjectName("rankNumber")
            rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vehicle = QLabel("—")
            vehicle.setObjectName("rankVehicle")
            count = QLabel("0")
            count.setObjectName("rankCount")

            fl.addWidget(rank)
            fl.addWidget(vehicle, 1)
            fl.addWidget(count)

            r = idx % 5
            c = idx // 5
            self.rank_grid.addWidget(frame, r, c)
            self.rank_rows.append((rank, vehicle, count))

        sl.addLayout(self.rank_grid)

        # Atividades.
        head = QHBoxLayout()
        title = QLabel("◷   Últimas atividades")
        title.setObjectName("sectionTitle")
        more = QPushButton("Ver histórico")
        more.setObjectName("linkButton")
        more.clicked.connect(lambda: self.navigate.emit("HISTORY"))
        head.addWidget(title)
        head.addStretch()
        head.addWidget(more)
        al.addLayout(head)

        sub = QLabel("Histórico recente de ações no sistema.")
        sub.setObjectName("sectionSubtitle")
        al.addWidget(sub)

        self.activities_text = QLabel()
        self.activities_text.setObjectName("listText")
        self.activities_text.setWordWrap(True)
        al.addWidget(self.activities_text)
        al.addStretch()

        # Dicas.
        title = QLabel("💡   Dicas")
        title.setObjectName("sectionTitle")
        tl.addWidget(title)

        self.tip_text = QLabel(
            "🎓   Use termos de busca específicos\n\n"
            "Quanto mais específicos os termos, mais relevantes serão os resultados."
        )
        self.tip_text.setObjectName("tipText")
        self.tip_text.setWordWrap(True)
        tl.addWidget(self.tip_text)
        tl.addStretch()

        dots = QLabel("●  ○  ○")
        dots.setObjectName("dots")
        dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.addWidget(dots)

        layout.addWidget(sources, 1)
        layout.addWidget(activities, 1)
        layout.addWidget(tips, 1)
        self.root.addWidget(row)

    def refresh(self, state: UiState) -> None:
        now_ms = int(datetime.now().timestamp() * 1000)
        day_ago = now_ms - 86_400_000

        news_count = len(state.news)
        videos_count = len(state.videos)
        today_videos = sum(1 for video in state.videos if video.capturedAt >= day_ago)
        active_demands = sum(1 for demand in state.demands if demand.active)
        source_count = len(self.controller.news_sources)

        self.metric_values["news"].setText(str(news_count))
        self.metric_values["videos"].setText(str(videos_count))
        self.metric_values["today"].setText(str(today_videos))
        self.metric_values["demands"].setText(str(active_demands))
        self.metric_values["sources"].setText(str(source_count))
        self.metric_subtitles["demands"].setText(
            f"{active_demands} ativa" if active_demands == 1 else f"{active_demands} ativas"
        )
        self.metric_subtitles["sources"].setText(f"{source_count} especializadas")

        # Progresso real da busca.
        progress = None
        progress_name = "Busca atual"

        if state.news_busy:
            progress = state.news_progress
            progress_name = "Busca de notícias"
        elif state.video_busy:
            progress = state.video_progress
            progress_name = "Busca de vídeos"

        if progress is not None:
            fraction = max(0.0, min(1.0, float(getattr(progress, "fraction", 0.0))))
            pct = round(fraction * 100)
            completed = int(getattr(progress, "completed", 0))
            total = int(getattr(progress, "total", 0))
            current = (
                getattr(progress, "currentSource", "")
                or getattr(progress, "currentQuery", "")
                or "Processando..."
            )

            self.ready_title.setText("●   Status: Monitorando")
            self.ready_text.setText("Busca em andamento. Resultados atualizados em tempo real.")
            self.search_progress_title.setText(progress_name)
            self.search_progress_value.setText(f"{pct}%")
            self.search_progress.setValue(pct)
            self.search_progress_detail.setText(
                f"{current}   •   etapa {completed}/{total}" if total else str(current)
            )
        else:
            self.ready_title.setText("●   Status: Pronto")
            self.ready_text.setText("Monitoramento ativo e funcionando normalmente.")
            self.search_progress_title.setText("Busca atual")
            self.search_progress_value.setText("100%")
            self.search_progress.setValue(100)
            self.search_progress_detail.setText("Nenhuma busca em andamento.")

        cfg = self.controller.proxy_config
        auto = self.controller.automation_settings

        news_interval = getattr(auto, "news_interval_minutes", 30)
        demand_interval = getattr(auto, "demand_interval_minutes", 60)
        video_times = sorted(getattr(auto, "video_schedule_times", set()) or [])
        video_detail = ", ".join(video_times) if video_times else "Sem horários definidos"

        self._set_schedule_detail(self.news_schedule, f"a cada {news_interval} min")
        self._set_schedule_detail(self.demand_schedule, f"a cada {demand_interval} min")
        self._set_schedule_detail(self.video_schedule, video_detail)

        # Top 10 veículos com mais matérias encontradas.
        vehicle_counts = Counter(
            (getattr(news, "source", "") or "Sem veículo").strip()
            for news in state.news
        )
        top10 = vehicle_counts.most_common(10)

        for idx, (_rank, vehicle_label, count_label) in enumerate(self.rank_rows):
            if idx < len(top10):
                vehicle, count = top10[idx]
                vehicle_label.setText(vehicle)
                vehicle_label.setToolTip(vehicle)
                count_label.setText(str(count))
            else:
                vehicle_label.setText("—")
                count_label.setText("0")

        unstable = (
            "Nenhuma"
            if not state.unstable_video_sources
            else ", ".join(
                str(getattr(item, "sourceName", item))
                for item in state.unstable_video_sources
            )
        )

        self.activities_text.setText(
            "●  Sistema iniciado\n"
            "   Monitor de Notícias v4.0.2\n\n"
            "⚙  Configuração carregada\n"
            f"   {cfg.status_label}\n\n"
            f"◴  Agendamento {'ativo' if auto.automatic_monitoring else 'pausado'}\n"
            f"   Fontes instáveis: {unstable}"
        )

    @staticmethod
    def _set_schedule_detail(frame: QFrame, value: str) -> None:
        for label in frame.findChildren(QLabel):
            if label.objectName() == "scheduleDetail":
                label.setText(value)
                return
