from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


def _time(ms: int) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y %H:%M")


class DemandsPage(BasePage):
    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("demandHero")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(18, 13, 18, 13)

        icon = QLabel("▣")
        icon.setObjectName("demandHeroIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(60, 60)
        hl.addWidget(icon)

        text = QVBoxLayout()
        title = QLabel("Demandas")
        title.setObjectName("demandHeroTitle")
        sub = QLabel(
            "Consulte e gerencie as demandas ativas, organizando o monitoramento conforme seus temas de interesse."
        )
        sub.setObjectName("demandMuted")
        sub.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(sub)
        hl.addLayout(text, 1)

        self.root.addWidget(hero)

        form = QFrame()
        form.setObjectName("demandCard")
        fl = QHBoxLayout(form)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(12)

        vehicle_box = QVBoxLayout()
        vehicle_label = QLabel("Veículo")
        vehicle_label.setObjectName("demandLabel")
        self.vehicle = QLineEdit()
        self.vehicle.setPlaceholderText("Selecione ou digite o veículo...")
        vehicle_box.addWidget(vehicle_label)
        vehicle_box.addWidget(self.vehicle)
        fl.addLayout(vehicle_box, 2)

        subject_box = QVBoxLayout()
        subject_label = QLabel("Assunto")
        subject_label.setObjectName("demandLabel")
        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Digite o assunto da demanda...")
        subject_box.addWidget(subject_label)
        subject_box.addWidget(self.subject)
        fl.addLayout(subject_box, 2)

        self.add = QPushButton("+   Adicionar")
        self.add.setObjectName("demandAdd")
        self.add.setMinimumHeight(44)
        fl.addWidget(self.add, 0, Qt.AlignmentFlag.AlignBottom)

        self.all = QPushButton("↻   Buscar todas")
        self.all.setObjectName("demandPrimary")
        self.all.setMinimumHeight(44)
        fl.addWidget(self.all, 0, Qt.AlignmentFlag.AlignBottom)

        self.root.addWidget(form)

        status = QFrame()
        status.setObjectName("demandStatus")
        st = QHBoxLayout(status)
        st.setContentsMargins(22, 14, 22, 14)
        dot = QLabel("●")
        dot.setObjectName("demandStatusDot")
        st.addWidget(dot)

        text = QVBoxLayout()
        self.status_title = QLabel("Status: Pronto")
        self.status_title.setObjectName("demandStatusTitle")
        self.status_text = QLabel("Sistema disponível para consultar e gerenciar demandas.")
        self.status_text.setObjectName("demandStatusText")
        text.addWidget(self.status_title)
        text.addWidget(self.status_text)
        st.addLayout(text, 1)

        self.root.addWidget(status)

        container = QFrame()
        container.setObjectName("demandCard")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(10)

        head = QHBoxLayout()
        title = QLabel("▤   Demandas cadastradas")
        title.setObjectName("demandListTitle")
        head.addWidget(title)
        head.addStretch()
        self.count = QLabel("")
        self.count.setObjectName("demandMuted")
        head.addWidget(self.count)
        cl.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setObjectName("demandScroll")
        self.items_widget = QWidget()
        self.items = QVBoxLayout(self.items_widget)
        self.items.setContentsMargins(0, 0, 0, 0)
        self.items.setSpacing(8)
        self.items.addStretch()
        self.scroll.setWidget(self.items_widget)
        cl.addWidget(self.scroll, 1)

        self.root.addWidget(container, 1)

        self.add.clicked.connect(self._add)
        self.all.clicked.connect(controller.search_all_demands)
        self.vehicle.textChanged.connect(self._valid)
        self.subject.textChanged.connect(self._valid)
        self._valid()

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#demandHero, QFrame#demandCard {
            background:white;border:1px solid #D6E6F7;border-radius:12px;
        }
        QLabel#demandHeroIcon {
            background:#E5F1FF;color:#087AF7;border-radius:30px;
            font-size:27px;font-weight:900;
        }
        QLabel#demandHeroTitle {
            color:#08245F;font-size:23px;font-weight:900;
        }
        QLabel#demandMuted { color:#6079A5;font-size:10px; }
        QLabel#demandLabel {
            color:#08245F;font-size:11px;font-weight:900;
        }
        QPushButton#demandAdd {
            background:#FFD44D;color:#5C4300;border:1px solid #F4B719;
            border-radius:8px;padding:9px 15px;font-weight:900;
        }
        QPushButton#demandPrimary {
            background:#0A7DF8;color:white;border:0;border-radius:8px;
            padding:9px 15px;font-weight:900;
        }
        QFrame#demandStatus {
            background:#ECFBF4;border:1px solid #B8EBD4;border-radius:12px;
        }
        QLabel#demandStatusDot { color:#078B5F;font-size:23px; }
        QLabel#demandStatusTitle {
            color:#086C50;font-size:13px;font-weight:900;
        }
        QLabel#demandStatusText { color:#527A6E;font-size:10px; }
        QLabel#demandListTitle {
            color:#08245F;font-size:17px;font-weight:900;
        }
        QScrollArea#demandScroll { border:0;background:transparent; }
        QFrame#demandItem {
            background:#FFFFFF;border:1px solid #DCE9F6;border-radius:10px;
        }
        QLabel#demandIcon {
            background:#FFF3CF;color:#E59A00;border:1px solid #FFE09A;
            border-radius:9px;font-size:19px;font-weight:900;
        }
        QLabel#demandTitle {
            color:#08245F;font-size:12px;font-weight:900;
        }
        QLabel#demandMeta { color:#6079A5;font-size:10px; }
        QPushButton#demandSearch {
            background:white;color:#0C3974;border:1px solid #C9DDF2;
            border-radius:8px;padding:8px 13px;font-weight:800;
        }
        QPushButton#demandDelete {
            background:#FFF1F4;color:#E03155;border:1px solid #FFB8C8;
            border-radius:8px;padding:8px 13px;font-weight:800;
        }
        """

    def _valid(self) -> None:
        self.add.setEnabled(bool(self.vehicle.text().strip() and self.subject.text().strip()))

    def _add(self) -> None:
        self.controller.add_demand(self.vehicle.text(), self.subject.text())
        self.vehicle.clear()
        self.subject.clear()

    def _clear(self) -> None:
        while self.items.count() > 1:
            item = self.items.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _item(self, demand) -> QFrame:
        frame = QFrame()
        frame.setObjectName("demandItem")
        frame.setMinimumHeight(88)

        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        icon = QLabel("▣")
        icon.setObjectName("demandIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)
        row.addWidget(icon)

        text = QVBoxLayout()
        title = QLabel(f"{demand.vehicle} • {demand.subject}")
        title.setObjectName("demandTitle")
        title.setWordWrap(True)
        meta = QLabel(
            f"Última busca: {_time(demand.lastCheckedAt)}  •  "
            f"encontrados {demand.lastFoundCount}  •  novos {demand.lastNewCount}"
        )
        meta.setObjectName("demandMeta")
        text.addWidget(title)
        text.addWidget(meta)
        row.addLayout(text, 1)

        find = QPushButton("⌕  Buscar")
        find.setObjectName("demandSearch")
        find.clicked.connect(lambda: self.controller.search_demand(demand))
        row.addWidget(find)

        delete = QPushButton("▣")
        delete.setObjectName("demandDelete")
        delete.setToolTip("Excluir demanda")
        delete.clicked.connect(lambda: self.controller.remove_demand(demand.id))
        row.addWidget(delete)

        return frame

    def refresh(self, state: UiState) -> None:
        if state.news_busy:
            self.status_title.setText("Status: Buscando")
            self.status_text.setText(state.status)
        else:
            self.status_title.setText("Status: Pronto")
            self.status_text.setText(
                "Sistema disponível para consultar e gerenciar demandas."
            )

        self.all.setEnabled(not state.news_busy and self.controller.search_available)

        total = len(state.demands)
        self.count.setText(
            f"{total} demanda cadastrada" if total == 1 else f"{total} demandas cadastradas"
        )

        self._clear()
        for demand in state.demands:
            self.items.insertWidget(self.items.count() - 1, self._item(demand))

        self.items_widget.setMinimumHeight(max(120, total * 96))
