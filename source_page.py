from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from monitor_noticias.ui.catalog import REGIONS, STATES
from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


class SourcesPage(BasePage):
    """Fonte com seleção nativa e scroll leve.

    Usa QTreeWidget em vez de centenas de widgets por linha. O checkbox continua
    funcional e, ao desmarcar uma fonte quando 'todas' está ativo, a página muda
    automaticamente para seleção manual sem perder as demais.
    """

    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)
        self._guard = False

        filters = QFrame()
        filters.setObjectName("sourcesTop")
        fl = QVBoxLayout(filters)
        fl.setContentsMargins(14, 11, 14, 11)
        fl.setSpacing(9)

        first = QHBoxLayout()
        first.setSpacing(8)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        for index, text in enumerate(
            ("Notícias", "Vídeos", "Mídia especializada")
        ):
            button = QPushButton(text)
            button.setObjectName("sourceTabButton")
            button.setCheckable(True)
            if index == 0:
                button.setChecked(True)
            self.tab_group.addButton(button, index)
            first.addWidget(button)

        first.addSpacing(6)

        self.query = QLineEdit()
        self.query.setObjectName("sourceSearch")
        self.query.setPlaceholderText(
            "⌕  Pesquisar por nome, região, estado ou grupo..."
        )
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
        filters_row.addWidget(self.state)

        self._reload_states()

        hint = QLabel(
            "Use os filtros para reduzir a lista sem alterar sua seleção."
        )
        hint.setObjectName("sourceMuted")
        filters_row.addWidget(hint)
        filters_row.addStretch()

        fl.addLayout(filters_row)
        self.root.addWidget(filters)

        mode = QFrame()
        mode.setObjectName("sourceStateCard")

        ml = QHBoxLayout(mode)
        ml.setContentsMargins(16, 11, 16, 11)

        dot = QLabel("●")
        dot.setObjectName("sourceStateDot")
        ml.addWidget(dot)

        text = QVBoxLayout()
        text.setSpacing(1)

        self.state_title = QLabel("Fontes de notícias")
        self.state_title.setObjectName("sourceStateTitle")

        self.state_subtitle = QLabel(
            "Escolha quais veículos participam da varredura."
        )
        self.state_subtitle.setObjectName("sourceStateSubtitle")

        text.addWidget(self.state_title)
        text.addWidget(self.state_subtitle)
        ml.addLayout(text, 1)

        self.mode_label = QLabel("TODOS")
        self.mode_label.setObjectName("sourceStateValue")
        ml.addWidget(self.mode_label)

        self.all_news = QPushButton("✓")
        self.all_news.setObjectName("sourceModeButton")
        self.all_news.setCheckable(True)
        self.all_news.setFixedSize(44, 30)
        ml.addWidget(self.all_news)

        self.root.addWidget(mode)

        controls = QFrame()
        controls.setObjectName("sourcesControl")

        cl = QHBoxLayout(controls)
        cl.setContentsMargins(14, 8, 14, 8)
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

        self.root.addWidget(controls)

        self.tree = QTreeWidget()
        self.tree.setObjectName("sourceTree")
        self.tree.setColumnCount(4)
        self.tree.header().hide()
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.setVerticalScrollMode(
            QTreeWidget.ScrollMode.ScrollPerPixel
        )
        self.tree.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tree.setColumnWidth(0, 52)
        self.tree.setColumnWidth(1, 72)
        self.tree.setColumnWidth(3, 130)

        self.root.addWidget(self.tree, 1)

        self.query.textChanged.connect(
            lambda _: self.refresh(self.controller.state)
        )
        self.region.currentTextChanged.connect(self._region_changed)
        self.state.currentTextChanged.connect(
            lambda _: self.refresh(self.controller.state)
        )
        self.tab_group.idClicked.connect(
            lambda _: self.refresh(self.controller.state)
        )
        self.all_news.toggled.connect(self._all_news_changed)
        self.tree.itemChanged.connect(self._item_changed)

        self.select_visible.clicked.connect(
            lambda: self._set_visible(True)
        )
        self.clear_visible.clicked.connect(
            lambda: self._set_visible(False)
        )
        self.select_all.clicked.connect(
            lambda: self._set_all(True)
        )
        self.clear_all.clicked.connect(
            lambda: self._set_all(False)
        )

        self.setStyleSheet(self._stylesheet())

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sourceFilterLabel")
        return label

    def _stylesheet(self) -> str:
        return """
        QFrame#sourcesTop, QFrame#sourcesControl {
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
            min-height:35px;
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
            font-size:18px;
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
            color:#078B5F;
            font-size:11px;
            font-weight:900;
        }

        QPushButton#sourceModeButton {
            background:white;
            color:#0B6872;
            border:1px solid #8EBDBD;
            border-radius:8px;
            font-weight:900;
        }
        QPushButton#sourceModeButton:checked {
            background:#0B6872;
            color:white;
            border-color:#0B6872;
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

        QTreeWidget#sourceTree {
            background:white;
            border:1px solid #D5E5F5;
            border-radius:12px;
            outline:0;
        }
        QTreeWidget#sourceTree::item {
            border-bottom:1px solid #E3EDF7;
            padding:8px 8px;
            min-height:40px;
            color:#173E75;
        }
        QTreeWidget#sourceTree::indicator {
            width:18px;
            height:18px;
        }

        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical {
            background:#82B5E8;
            min-height:48px;
            border-radius:5px;
        }
        QScrollBar::handle:vertical:hover {
            background:#5F9EDB;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height:0;
        }
        """

    def _tab(self) -> int:
        value = self.tab_group.checkedId()
        return 0 if value < 0 else value

    def _region_changed(self, _text: str) -> None:
        self._reload_states()
        self.refresh(self.controller.state)

    def _reload_states(self) -> None:
        current = self.state.currentText()
        region = self.region.currentText()

        self.state.blockSignals(True)
        self.state.clear()
        self.state.addItem("Todos")

        for code, _name, reg in STATES:
            if region in {"Todas", "Nacional"} or reg == region:
                self.state.addItem(code)

        index = self.state.findText(current)
        self.state.setCurrentIndex(max(0, index))
        self.state.blockSignals(False)

    def _sources(self):
        if self._tab() == 0:
            return self.controller.news_sources
        if self._tab() == 1:
            return self.controller.video_sources
        return self.controller.specialized_sources

    def _visible_sources(self):
        query = self.query.text().strip().lower()
        region = self.region.currentText()
        state = self.state.currentText()
        result = []

        for source in self._sources():
            src_region = getattr(source, "region", "Nacional") or "Nacional"
            src_state = getattr(source, "state", "") or "BR"

            if region != "Todas" and src_region != region:
                continue
            if state != "Todos" and src_state != state:
                continue

            haystack = (
                f"{source.name} {source.group} {src_region} {src_state} "
                f"{' '.join(getattr(source, 'aliases', ()) or ())}"
            ).lower()

            if query and query not in haystack:
                continue

            result.append(source)

        return result

    def _selected_ids(self) -> set[str]:
        if self._tab() == 1:
            return set(self.controller.selected_video_source_ids)

        if self.controller.news_all_sources:
            return {source.id for source in self._sources()}

        return set(self.controller.selected_news_source_ids)

    def _all_news_changed(self, checked: bool) -> None:
        if self._guard or self._tab() == 1:
            return

        self.controller.news_all_sources = checked

        if checked:
            self.controller.selected_news_source_ids = set()

        self.refresh(self.controller.state)

    def _item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._guard or column != 0:
            return

        source_id = item.data(0, Qt.ItemDataRole.UserRole)

        if not source_id:
            return

        checked = item.checkState(0) == Qt.CheckState.Checked

        if self._tab() == 1:
            self.controller.set_video_source(source_id, checked)
            return

        # Se "TODOS" estiver ativo e o usuário desmarcar uma fonte, muda para
        # seleção manual preservando todas as demais.
        if self.controller.news_all_sources:
            all_ids = {
                source.id
                for source in (
                    tuple(self.controller.news_sources)
                    + tuple(self.controller.specialized_sources)
                )
            }
            self.controller.news_all_sources = False
            self.controller.selected_news_source_ids = all_ids

            self._guard = True
            self.all_news.setChecked(False)
            self._guard = False

        self.controller.set_news_source(source_id, checked)

    def refresh(self, _state: UiState) -> None:
        self._guard = True

        tab = self._tab()
        visible = self._visible_sources()

        self.all_news.blockSignals(True)
        self.all_news.setChecked(
            self.controller.news_all_sources
            if tab != 1
            else False
        )
        self.all_news.blockSignals(False)

        if tab == 0:
            self.state_title.setText("Fontes de notícias")
            self.state_subtitle.setText(
                "Escolha quais veículos participam da varredura."
            )
            self.mode_label.setText(
                "TODOS"
                if self.controller.news_all_sources
                else "Seleção manual"
            )
            self.all_news.show()

        elif tab == 1:
            self.state_title.setText("Fontes de vídeo")
            self.state_subtitle.setText(
                "Escolha quais fontes participam da busca de vídeos."
            )
            self.mode_label.setText("Seleção própria")
            self.all_news.hide()

        else:
            self.state_title.setText("Mídia especializada")
            self.state_subtitle.setText(
                "Veículos especializados em Defesa e Forças Armadas."
            )
            self.mode_label.setText(
                "TODOS"
                if self.controller.news_all_sources
                else "Seleção manual"
            )
            self.all_news.show()

        selected = self._selected_ids()

        self.tree.clear()

        selected_count = 0

        for source in visible:
            item = QTreeWidgetItem(self.tree)
            item.setData(0, Qt.ItemDataRole.UserRole, source.id)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            checked = source.id in selected
            selected_count += int(checked)

            item.setCheckState(
                0,
                Qt.CheckState.Checked
                if checked
                else Qt.CheckState.Unchecked,
            )

            item.setText(1, (source.name or "F")[:2].upper())

            src_region = getattr(source, "region", "Nacional") or "Nacional"
            src_state = getattr(source, "state", "") or "BR"

            item.setText(
                2,
                f"{source.name}\n"
                f"{source.group}  •  {src_region}  •  {src_state}",
            )

            item.setText(3, "Disponível")
            item.setTextAlignment(
                3,
                Qt.AlignmentFlag.AlignCenter,
            )
            item.setSizeHint(0, QSize(0, 56))

        self.info.setText(
            f"▦   {len(visible)} fonte(s) visível(is)   "
            f"{selected_count} selecionada(s) neste filtro"
        )

        self._guard = False

    def _set_visible(self, checked: bool) -> None:
        if self._tab() != 1 and self.controller.news_all_sources and not checked:
            all_ids = {
                source.id
                for source in (
                    tuple(self.controller.news_sources)
                    + tuple(self.controller.specialized_sources)
                )
            }
            self.controller.news_all_sources = False
            self.controller.selected_news_source_ids = all_ids

        for source in self._visible_sources():
            if self._tab() == 1:
                self.controller.set_video_source(source.id, checked)
            else:
                self.controller.set_news_source(source.id, checked)

        self.refresh(self.controller.state)

    def _set_all(self, checked: bool) -> None:
        if self._tab() == 1:
            self.controller.selected_video_source_ids = (
                {source.id for source in self.controller.video_sources}
                if checked
                else set()
            )

        elif self._tab() == 0:
            self.controller.news_all_sources = checked
            self.controller.selected_news_source_ids = (
                set()
                if checked
                else set()
            )

        else:
            ids = set(self.controller.selected_news_source_ids)
            spec_ids = {
                source.id
                for source in self.controller.specialized_sources
            }

            if self.controller.news_all_sources and not checked:
                ids = {
                    source.id
                    for source in (
                        tuple(self.controller.news_sources)
                        + tuple(self.controller.specialized_sources)
                    )
                }
                self.controller.news_all_sources = False

            self.controller.selected_news_source_ids = (
                ids | spec_ids
                if checked
                else ids - spec_ids
            )

        self.refresh(self.controller.state)
