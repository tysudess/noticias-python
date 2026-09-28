from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui import home_page as home_module


_INSTALLED = False


def _build_schedule_only(self) -> None:
    """V76: Agendamento automático ocupa sozinho toda a largura da linha."""

    row = QWidget()
    row.setObjectName("homeScheduleWideRow")

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    schedule, sl = home_module._card("homeCard")
    schedule.setObjectName("homeScheduleWide")
    schedule.setMinimumHeight(176)

    title = QLabel("◴   Agendamento automático")
    title.setObjectName("sectionTitle")

    sub = QLabel(
        "O sistema executa buscas automaticamente nos horários definidos."
    )
    sub.setObjectName("sectionSubtitle")
    sub.setWordWrap(True)

    sl.addWidget(title)
    sl.addWidget(sub)

    cells = QHBoxLayout()
    cells.setContentsMargins(0, 5, 0, 0)
    cells.setSpacing(12)

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

    for cell in (
        self.news_schedule,
        self.demand_schedule,
        self.video_schedule,
    ):
        cell.setMinimumHeight(76)
        cells.addWidget(cell, 1)

    sl.addLayout(cells)

    layout.addWidget(schedule, 1)
    self.root.addWidget(row)


def _build_bottom_without_tips(self) -> None:
    """V76: remove o terceiro card inferior e equilibra os dois restantes."""

    row = QWidget()
    row.setObjectName("homeBottomWideRow")

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)

    sources, sl = home_module._card("homeCard")
    activities, al = home_module._card("homeCard")

    for card in (sources, activities):
        card.setMinimumHeight(220)

    # TOP 10 veículos.
    head = QHBoxLayout()

    title = QLabel("●   Top 10 veículos")
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

    sub = QLabel(
        "Veículos com mais matérias encontradas."
    )
    sub.setObjectName("sectionSubtitle")
    sl.addWidget(sub)

    self.rank_grid = QGridLayout()
    self.rank_grid.setHorizontalSpacing(8)
    self.rank_grid.setVerticalSpacing(5)

    self.rank_rows: list[
        tuple[QLabel, QLabel, QLabel]
    ] = []

    for idx in range(10):
        frame = QFrame()
        frame.setObjectName("rankRow")

        fl = QHBoxLayout(frame)
        fl.setContentsMargins(7, 5, 8, 5)
        fl.setSpacing(7)

        rank = QLabel(str(idx + 1))
        rank.setObjectName("rankNumber")
        rank.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        vehicle = QLabel("—")
        vehicle.setObjectName("rankVehicle")

        count = QLabel("0")
        count.setObjectName("rankCount")

        fl.addWidget(rank)
        fl.addWidget(vehicle, 1)
        fl.addWidget(count)

        grid_row = idx % 5
        grid_col = idx // 5

        self.rank_grid.addWidget(
            frame,
            grid_row,
            grid_col,
        )

        self.rank_rows.append(
            (
                rank,
                vehicle,
                count,
            )
        )

    sl.addLayout(self.rank_grid)
    sl.addStretch(1)

    # Últimas atividades.
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

    sub = QLabel(
        "Histórico recente de ações no sistema."
    )
    sub.setObjectName("sectionSubtitle")
    al.addWidget(sub)

    self.activities_text = QLabel()
    self.activities_text.setObjectName(
        "listText"
    )
    self.activities_text.setWordWrap(
        True
    )

    al.addWidget(
        self.activities_text
    )
    al.addStretch(1)

    layout.addWidget(
        sources,
        1,
    )
    layout.addWidget(
        activities,
        1,
    )

    self.root.addWidget(
        row
    )


def install_home_layout_v76_patch() -> None:
    """Substitui os builders da Home ANTES de a MainWindow ser construída."""

    global _INSTALLED

    if _INSTALLED:
        return

    home_module.HomePage._build_schedule_and_summary = (
        _build_schedule_only
    )

    home_module.HomePage._build_bottom_cards = (
        _build_bottom_without_tips
    )

    _INSTALLED = True
