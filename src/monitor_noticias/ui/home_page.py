from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
    """Tela Início refinada para legibilidade e proporção visual."""

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
        QLabel#metricIcon,
        QLabel#scheduleIcon {
            border-radius:12px;
            font-size:23px;
            font-weight:900;
        }
        QLabel#metricIcon[tone='blue'],
        QLabel#scheduleIcon[tone='blue'] {
            background:#DDEEFF;
            color:#0C77F5;
        }
        QLabel#metricIcon[tone='purple'],
        QLabel#scheduleIcon[tone='purple'] {
            background:#EFE2FF;
            color:#743AF3;
        }
        QLabel#metricIcon[tone='green'],
        QLabel#scheduleIcon[tone='green'] {
            background:#DDF8EC;
            color:#049E68;
        }
        QLabel#metricIcon[tone='orange'],
        QLabel#scheduleIcon[tone='orange'] {
            background:#FFF0C9;
            color:#E69A00;
        }
        QLabel#metricIcon[tone='pink'] {
            background:#FFE1ED;
            color:#C4005C;
        }

        QFrame#heroCard,
        QFrame#homeCard,
        QFrame#quickCard,
        QFrame#tipCard {
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

        QPushButton#quickPrimary,
        QPushButton#quickSecondary {
            text-align:left;
            border-radius:9px;
            padding:8px 16px;
            min-height:44px;
            font-size:11px;
            font-weight:800;
        }
        QPushButton#quickPrimary {
            background:qlineargradient(
                x1:0,y1:0,x2:1,y2:0,
                stop:0 #0A75EA,
                stop:1 #0B8EFF
            );
            color:white;
            border:0;
        }
        QPushButton#quickSecondary {
            background:#F8FBFF;
            color:#0A3A79;
            border:1px solid #D4E4F5;
        }
        QPushButton#quickSecondary:hover {
            background:#EEF6FF;
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
                row.addWidget(
                    delta,
                    0,
                    Qt.AlignmentFlag.AlignTop,
                )

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
        hero.setMinimumHeight(205)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 17, 22, 17)
        hero_layout.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(8)

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
            "As buscas e os resultados agora são atualizados "
            "na própria tela, em tempo real."
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
        status_l.setContentsMargins(17, 11, 17, 11)
        status_l.setSpacing(3)

        self.ready_title = QLabel("●   Status: Pronto")
        self.ready_title.setObjectName("readyTitle")

        self.ready_text = QLabel(
            "Monitoramento ativo e funcionando normalmente."
        )
        self.ready_text.setObjectName("readyText")
        self.ready_text.setWordWrap(True)

        status_l.addWidget(self.ready_title)
        status_l.addWidget(self.ready_text)

        left.addWidget(status)

        visual = QFrame()
        visual.setObjectName("monitorVisual")
        visual.setMinimumWidth(250)

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
        quick.setMinimumHeight(205)

        qtitle = QLabel("⚡   Ações rápidas")
        qtitle.setObjectName("sectionTitle")

        qsub = QLabel(
            "Execute varreduras prioritárias sem interromper o acompanhamento."
        )
        qsub.setObjectName("sectionSubtitle")
        qsub.setWordWrap(True)

        ql.addWidget(qtitle)
        ql.addWidget(qsub)

        self.news_button = QPushButton(
            "⌕   Buscar notícias\n"
            "      Iniciar varredura agora     ›"
        )
        self.news_button.setObjectName("quickPrimary")
        self.news_button.clicked.connect(
            self.controller.search_news
        )

        self.video_button = QPushButton(
            "▶   Buscar vídeos\n"
            "      Pesquisar novos vídeos     ›"
        )
        self.video_button.setObjectName("quickSecondary")
        self.video_button.clicked.connect(
            self.controller.search_videos
        )

        self.demands_button = QPushButton(
            "▣   Buscar demandas\n"
            "      Consultar demandas ativas     ›"
        )
        self.demands_button.setObjectName("quickSecondary")
        self.demands_button.clicked.connect(
            self.controller.search_all_demands
        )

        for button in (
            self.news_button,
            self.video_button,
            self.demands_button,
        ):
            button.setMinimumHeight(47)
            ql.addWidget(button)

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

        sub = QLabel(
            "O sistema executa buscas automaticamente "
            "nos horários definidos."
        )
        sub.setObjectName("sectionSubtitle")
        sub.setWordWrap(True)

        sl.addWidget(title)
        sl.addWidget(sub)

        cells = QHBoxLayout()
        cells.setSpacing(8)

        self.news_schedule = self._schedule_box(
            "▤",
            "Notícias",
            "a cada 30 min",
            "blue",
        )
        self.demand_schedule = self._schedule_box(
            "▣",
            "Demandas",
            "a cada 60 min",
            "orange",
        )
        self.video_schedule = self._schedule_box(
            "▶",
            "Vídeos",
            "08:00, 12:00, 15:00, 19:00, 21:00",
            "purple",
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
            "40 ┤\n"
            "30 ┤\n"
            "20 ┤\n"
            "10 ┤\n"
            " 0 ┼─●──●──●──●──●──●──●──●──●──●──●──●─"
        )
        self.graph_text.setObjectName("graphText")
        self.graph_text.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        legend = QLabel(
            "● Notícias     ● Vídeos     ● Demandas"
        )
        legend.setObjectName("graphLegend")

        gl.addWidget(self.graph_text)
        gl.addWidget(legend)

        dl.addWidget(graph)

        layout.addWidget(schedule, 1)
        layout.addWidget(summary, 1)

        self.root.addWidget(row)

    def _schedule_box(
        self,
        icon: str,
        title: str,
        detail: str,
        tone: str,
    ) -> QFrame:
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
            card.setMinimumHeight(168)

        # Fontes.
        head = QHBoxLayout()

        title = QLabel("●   Fontes mais relevantes")
        title.setObjectName("sectionTitle")

        more = QPushButton("Ver todas")
        more.setObjectName("linkButton")
        more.clicked.connect(
            lambda: self.navigate.emit("SOURCES")
        )

        head.addWidget(title)
        head.addStretch()
        head.addWidget(more)

        sl.addLayout(head)

        sub = QLabel("Suas principais fontes monitoradas.")
        sub.setObjectName("sectionSubtitle")
        sl.addWidget(sub)

        self.sources_text = QLabel()
        self.sources_text.setObjectName("listText")
        self.sources_text.setWordWrap(True)

        sl.addWidget(self.sources_text)
        sl.addStretch()

        # Atividades.
        head = QHBoxLayout()

        title = QLabel("◷   Últimas atividades")
        title.setObjectName("sectionTitle")

        more = QPushButton("Ver histórico")
        more.setObjectName("linkButton")
        more.clicked.connect(
            lambda: self.navigate.emit("HISTORY")
        )

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
            "Quanto mais específicos os termos, mais "
            "relevantes serão os resultados."
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

        today_videos = sum(
            1
            for video in state.videos
            if video.capturedAt >= day_ago
        )

        active_demands = sum(
            1
            for demand in state.demands
            if demand.active
        )

        source_count = len(self.controller.news_sources)

        self.metric_values["news"].setText(str(news_count))
        self.metric_values["videos"].setText(str(videos_count))
        self.metric_values["today"].setText(str(today_videos))
        self.metric_values["demands"].setText(str(active_demands))
        self.metric_values["sources"].setText(str(source_count))

        self.metric_subtitles["demands"].setText(
            f"{active_demands} ativa"
            if active_demands == 1
            else f"{active_demands} ativas"
        )

        self.metric_subtitles["sources"].setText(
            f"{source_count} especializadas"
        )

        cfg = self.controller.proxy_config
        auto = self.controller.automation_settings

        if state.news_busy or state.video_busy:
            self.ready_title.setText(
                "●   Status: Monitorando"
            )
            self.ready_text.setText(
                "Uma busca está em andamento. "
                "Os resultados serão atualizados em tempo real."
            )
        else:
            self.ready_title.setText(
                "●   Status: Pronto"
            )
            self.ready_text.setText(
                "Monitoramento ativo e funcionando normalmente."
            )

        news_interval = getattr(
            auto,
            "news_interval_minutes",
            30,
        )

        demand_interval = getattr(
            auto,
            "demand_interval_minutes",
            60,
        )

        video_times = sorted(
            getattr(
                auto,
                "video_schedule_times",
                set(),
            )
            or []
        )

        video_detail = (
            ", ".join(video_times)
            if video_times
            else "Sem horários definidos"
        )

        self._set_schedule_detail(
            self.news_schedule,
            f"a cada {news_interval} min",
        )

        self._set_schedule_detail(
            self.demand_schedule,
            f"a cada {demand_interval} min",
        )

        self._set_schedule_detail(
            self.video_schedule,
            video_detail,
        )

        top_sources = list(
            self.controller.news_sources[:5]
        )

        if top_sources:
            lines = []

            for index, source in enumerate(
                top_sources,
                start=1,
            ):
                name = getattr(
                    source,
                    "name",
                    str(source),
                )

                lines.append(
                    f"{index}.  ●  {name}        ● Ativa"
                )

            self.sources_text.setText(
                "\n".join(lines)
            )
        else:
            self.sources_text.setText(
                "Nenhuma fonte cadastrada."
            )

        unstable = (
            "Nenhuma"
            if not state.unstable_video_sources
            else ", ".join(
                str(
                    getattr(
                        item,
                        "sourceName",
                        item,
                    )
                )
                for item in state.unstable_video_sources
            )
        )

        self.activities_text.setText(
            "●  Sistema iniciado\n"
            "   Monitor de Notícias v4.0.2\n\n"
            "⚙  Configuração carregada\n"
            f"   {cfg.status_label}\n\n"
            f"◴  Agendamento "
            f"{'ativo' if auto.automatic_monitoring else 'pausado'}\n"
            f"   Fontes instáveis: {unstable}"
        )

    @staticmethod
    def _set_schedule_detail(
        frame: QFrame,
        value: str,
    ) -> None:
        for label in frame.findChildren(QLabel):
            if label.objectName() == "scheduleDetail":
                label.setText(value)
                return
