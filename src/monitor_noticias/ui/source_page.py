from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from monitor_noticias.ui.catalog import REGIONS, STATES
from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


class SourcesPage(BasePage):
    """Página Fontes refinada, preservando toda a lógica de seleção existente."""

    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)
        self._guard = False

        filters = QFrame()
        filters.setObjectName("sourcesTop")
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        first = QHBoxLayout()
        first.setSpacing(8)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_buttons: list[QPushButton] = []

        for index, text in enumerate(("Notícias", "Vídeos", "Mídia especializada")):
            button = QPushButton(text)
            button.setObjectName("sourceTabButton")
            button.setCheckable(True)
            button.setProperty("tabIndex", index)
            if index == 0:
                button.setChecked(True)
            self.tab_group.addButton(button, index)
            self.tab_buttons.append(button)
            first.addWidget(button)

        first.addStretch()

        self.query = QLineEdit()
        self.query.setObjectName("sourceSearch")
        self.query.setPlaceholderText("⌕  Pesquisar por nome, região, estado ou grupo...")
        self.query.setMinimumWidth(390)
        first.addWidget(self.query, 1)

        fl.addLayout(first)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(8)

        filters_row.addWidget(self._label("Região"))
        self.region = QComboBox()
        self.region.setMinimumWidth(180)
        self.region.addItems(REGIONS)
        filters_row.addWidget(self.region)

        filters_row.addWidget(self._label("Estado"))
        self.state = QComboBox()
        self.state.setMinimumWidth(180)
        self.state.addItem("Todos")
        self._reload_states()
        filters_row.addWidget(self.state)

        hint = QLabel("Use os filtros para reduzir a lista sem alterar sua seleção.")
        hint.setObjectName("sourceMuted")
        filters_row.addWidget(hint)
        filters_row.addStretch()

        fl.addLayout(filters_row)
        self.root.addWidget(filters)

        state_card = QFrame()
        state_card.setObjectName("sourceStateCard")
        sl = QHBoxLayout(state_card)
        sl.setContentsMargins(16, 12, 16, 12)

        dot = QLabel("●")
        dot.setObjectName("sourceStateDot")
        sl.addWidget(dot)

        state_text = QVBoxLayout()
        self.state_title = QLabel("Fontes de notícias")
        self.state_title.setObjectName("sourceStateTitle")
        self.state_subtitle = QLabel("Selecione quais fontes participam da varredura.")
        self.state_subtitle.setObjectName("sourceStateSubtitle")
        state_text.addWidget(self.state_title)
        state_text.addWidget(self.state_subtitle)
        sl.addLayout(state_text, 1)

        self.all_news_label = QLabel("")
        self.all_news_label.setObjectName("sourceStateValue")
        sl.addWidget(self.all_news_label)

        self.all_news = QCheckBox()
        self.all_news.setObjectName("sourceSwitch")
        self.all_news.setToolTip(
            "Ligado: aceita qualquer veículo encontrado, inclusive fora do catálogo padrão."
        )
        sl.addWidget(self.all_news)

        self.root.addWidget(state_card)

        control = QFrame()
        control.setObjectName("sourcesControl")
        cl = QHBoxLayout(control)
        cl.setContentsMargins(14, 9, 14, 9)
        cl.setSpacing(8)

        self.info = QLabel()
        self.info.setObjectName("sourceCount")
        cl.addWidget(self.info)

        cl.addStretch()

        self.select_visible = QPushButton("✓  Selecionar visíveis")
        self.select_visible.setObjectName("sourcePrimary")
        self.clear_visible = QPushButton("Limpar visíveis")
        self.clear_visible.setObjectName("sourceSecondary")
        self.select_all = QPushButton("Selecionar todas")
        self.select_all.setObjectName("sourceSecondary")
        self.clear_all = QPushButton("Limpar todas")
        self.clear_all.setObjectName("sourceSecondary")

        for button in (
            self.select_visible,
            self.clear_visible,
            self.select_all,
            self.clear_all,
        ):
            cl.addWidget(button)

        self.root.addWidget(control)

        self.news_list = QListWidget()
        self.video_list = QListWidget()
        self.special_list = QListWidget()

        # O QTabWidget é mantido apenas para a barra de tabs.
        self.list_container = QFrame()
        self.list_container.setObjectName("sourceListContainer")
        ll = QVBoxLayout(self.list_container)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        for listw in (self.news_list, self.video_list, self.special_list):
            listw.setObjectName("sourceList")
            listw.setSpacing(5)
            listw.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
            listw.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            ll.addWidget(listw)
            listw.hide()

        self.news_list.show()
        self.root.addWidget(self.list_container, 1)

        self.query.textChanged.connect(lambda _: self.refresh(controller.state))
        self.region.currentTextChanged.connect(self._region_changed)
        self.state.currentTextChanged.connect(lambda _: self.refresh(controller.state))
        self.tab_group.idClicked.connect(self._tab_changed)
        self.all_news.toggled.connect(self._all_news_changed)

        self.select_visible.clicked.connect(lambda: self._set_visible(True))
        self.clear_visible.clicked.connect(lambda: self._set_visible(False))
        self.select_all.clicked.connect(lambda: self._set_all(True))
        self.clear_all.clicked.connect(lambda: self._set_all(False))

        self.setStyleSheet(self._stylesheet())

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sourceFilterLabel")
        return label

    def _stylesheet(self) -> str:
        return """
        QFrame#sourcesTop, QFrame#sourcesControl, QFrame#sourceListContainer {
            background:#FFFFFF;
            border:1px solid #D5E5F5;
            border-radius:12px;
        }
        QPushButton#sourceTabButton {
            background:#F8FBFF;
            color:#183E72;
            border:1px solid #D2E2F4;
            border-radius:8px;
            padding:10px 18px;
            min-width:115px;
            font-weight:800;
        }
        QPushButton#sourceTabButton:checked {
            background:#0A7DF8;
            color:white;
            border-color:#0A7DF8;
        }
        QLineEdit#sourceSearch {
            min-height:34px;
            padding:0 11px;
            font-size:11px;
        }
        QLabel#sourceFilterLabel {
            color:#173E75;
            font-size:11px;
            font-weight:800;
        }
        QLabel#sourceMuted {
            color:#6A80A5;
            font-size:10px;
        }
        QFrame#sourceStateCard {
            background:#ECFBF4;
            border:1px solid #BDEAD7;
            border-radius:12px;
        }
        QLabel#sourceStateDot {
            color:#08A66B;
            font-size:20px;
        }
        QLabel#sourceStateTitle {
            color:#08795A;
            font-size:12px;
            font-weight:900;
        }
        QLabel#sourceStateSubtitle {
            color:#527A6E;
            font-size:10px;
        }
        QLabel#sourceStateValue {
            color:#08A66B;
            font-size:11px;
            font-weight:900;
        }
        QCheckBox#sourceSwitch::indicator {
            width:38px;
            height:22px;
        }
        QFrame#sourcesControl {
            min-height:52px;
        }
        QLabel#sourceCount {
            color:#08245F;
            font-size:17px;
            font-weight:900;
        }
        QPushButton#sourcePrimary {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:8px 15px;
            font-weight:800;
        }
        QPushButton#sourceSecondary {
            background:white;
            color:#123B73;
            border:1px solid #C8DCF2;
            border-radius:8px;
            padding:8px 14px;
            font-weight:700;
        }
        QListWidget#sourceList {
            background:transparent;
            border:0;
            outline:0;
            padding:4px;
        }
        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical {
            background:#9FC3EA;
            min-height:42px;
            border-radius:5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """

    def _tab_index(self) -> int:
        checked = self.tab_group.checkedId()
        return 0 if checked < 0 else checked

    def _tab_changed(self, index: int) -> None:
        for i, listw in enumerate((self.news_list, self.video_list, self.special_list)):
            listw.setVisible(i == index)
        self.refresh(self.controller.state)

    def _region_changed(self, _text: str) -> None:
        self._reload_states()
        self.refresh(self.controller.state)

    def _reload_states(self) -> None:
        current = self.state.currentText() if hasattr(self, "state") else "Todos"
        region = self.region.currentText() if hasattr(self, "region") else "Todas"

        self.state.blockSignals(True)
        self.state.clear()
        self.state.addItem("Todos")

        for code, _name, reg in STATES:
            if region in {"Todas", "Nacional"} or reg == region:
                self.state.addItem(code)

        idx = self.state.findText(current)
        self.state.setCurrentIndex(max(0, idx))
        self.state.blockSignals(False)

    def _all_news_changed(self, value: bool) -> None:
        self.controller.news_all_sources = value
        self.refresh(self.controller.state)

    def _selected_sources(self):
        tab = self._tab_index()
        region = self.region.currentText()
        state = self.state.currentText()
        query = self.query.text().strip().lower()

        base = (
            self.controller.news_sources
            if tab == 0
            else self.controller.video_sources
            if tab == 1
            else self.controller.specialized_sources
        )

        result = []
        for source in base:
            src_region = getattr(source, "region", "Nacional") or "Nacional"
            src_state = getattr(source, "state", "") or "BR"

            if region != "Todas" and src_region != region:
                continue
            if state != "Todos" and src_state != state:
                continue

            haystack = (
                f"{source.name} {src_region} {src_state} "
                f"{source.group} {' '.join(source.aliases)}"
            ).lower()

            if query and query not in haystack:
                continue

            result.append(source)

        return result

    def _make_row(self, listw: QListWidget, source, checked: bool, enabled: bool) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, source.id)
        item.setSizeHint(QSize(0, 58))

        row = QFrame()
        row.setStyleSheet(
            "QFrame{background:white;border:1px solid #DCE9F6;border-radius:9px;}"
            "QLabel{border:0;background:transparent;}"
        )
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(10)

        check = QCheckBox()
        check.setChecked(checked)
        check.setEnabled(enabled)
        lay.addWidget(check)

        badge = QLabel((source.name or "F")[:2].upper())
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(52, 34)
        badge.setStyleSheet(
            "background:#EAF4FF;color:#087AF7;border-radius:8px;"
            "font-size:11px;font-weight:900;"
        )
        lay.addWidget(badge)

        texts = QVBoxLayout()
        texts.setSpacing(1)
        title = QLabel(source.name)
        title.setStyleSheet("color:#08245F;font-size:12px;font-weight:900;")
        meta = QLabel(
            f"{source.group}  •  {getattr(source,'region','Nacional')}  •  "
            f"{getattr(source,'state','') or 'BR'}"
        )
        meta.setStyleSheet("color:#6079A5;font-size:10px;")
        texts.addWidget(title)
        texts.addWidget(meta)
        lay.addLayout(texts, 1)

        status = QLabel("Disponível")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setFixedWidth(112)
        status.setStyleSheet(
            "background:#EAF9F2;color:#078B5F;border:1px solid #C3EBD9;"
            "border-radius:7px;padding:7px;font-size:10px;font-weight:800;"
        )
        lay.addWidget(status)

        listw.addItem(item)
        listw.setItemWidget(item, row)

        def changed(value: bool, source_id=source.id):
            if self._guard:
                return
            if self._tab_index() == 1:
                self.controller.set_video_source(source_id, value)
            else:
                self.controller.set_news_source(source_id, value)

        check.toggled.connect(changed)

    def _fill(self, listw: QListWidget, sources, selected, enabled=True) -> None:
        listw.clear()
        for source in sources:
            checked = (not enabled) or source.id in selected
            self._make_row(listw, source, checked, enabled)

    def refresh(self, state: UiState) -> None:
        self._guard = True

        self.all_news.blockSignals(True)
        self.all_news.setChecked(self.controller.news_all_sources)
        self.all_news.blockSignals(False)

        tab = self._tab_index()
        visible = self._selected_sources()

        if tab == 0:
            self.state_title.setText("Fontes de notícias")
            self.state_subtitle.setText("Escolha quais veículos participam da varredura.")
            self.all_news.show()
            self.all_news_label.setText(
                "TODOS" if self.controller.news_all_sources else "Seleção manual"
            )
            self._fill(
                self.news_list,
                visible,
                self.controller.selected_news_source_ids,
                not self.controller.news_all_sources,
            )
        elif tab == 1:
            self.state_title.setText("Fontes de vídeo")
            self.state_subtitle.setText(
                "Vídeos usam seleção própria; escolha abaixo quais fontes participam da varredura."
            )
            self.all_news.hide()
            self.all_news_label.setText("N/A")
            self._fill(
                self.video_list,
                visible,
                self.controller.selected_video_source_ids,
                True,
            )
        else:
            self.state_title.setText("Mídia especializada")
            self.state_subtitle.setText(
                "Veículos especializados em Defesa, Forças Armadas e assuntos navais."
            )
            self.all_news.show()
            self.all_news_label.setText(
                "TODOS" if self.controller.news_all_sources else "Seleção manual"
            )
            self._fill(
                self.special_list,
                visible,
                self.controller.selected_news_source_ids,
                not self.controller.news_all_sources,
            )

        selected_count = sum(
            1
            for source in visible
            if (
                source.id in self.controller.selected_video_source_ids
                if tab == 1
                else self.controller.news_all_sources
                or source.id in self.controller.selected_news_source_ids
            )
        )

        self.info.setText(
            f"▦   {len(visible)} fonte(s) visível(is)   "
            f"{selected_count} selecionada(s) neste filtro"
        )

        self._guard = False

    def _set_visible(self, checked: bool) -> None:
        tab = self._tab_index()
        for source in self._selected_sources():
            if tab == 1:
                self.controller.set_video_source(source.id, checked)
            else:
                self.controller.set_news_source(source.id, checked)
        self.refresh(self.controller.state)

    def _set_all(self, checked: bool) -> None:
        tab = self._tab_index()
        base = (
            self.controller.video_sources
            if tab == 1
            else self.controller.specialized_sources
            if tab == 2
            else self.controller.news_sources
        )

        if tab == 1:
            self.controller.selected_video_source_ids = (
                {source.id for source in base} if checked else set()
            )
        else:
            if tab == 0:
                self.controller.news_all_sources = checked
                if not checked:
                    self.controller.selected_news_source_ids = set()
            else:
                ids = self.controller.selected_news_source_ids
                spec = {source.id for source in base}
                self.controller.selected_news_source_ids = (
                    ids | spec if checked else ids - spec
                )

        self.refresh(self.controller.state)
