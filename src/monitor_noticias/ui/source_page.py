from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QEvent, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView,
    QPushButton, QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout,
)

from monitor_noticias.ui.catalog import REGIONS, STATES
from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


class SourceListModel(QAbstractListModel):
    SourceRole = Qt.ItemDataRole.UserRole + 1
    CheckedRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.rows = []
        self.checked: set[str] = set()
        self._signature = None

    def set_rows(self, rows, checked: set[str]) -> None:
        rows = list(rows)
        signature = (
            tuple(
                (
                    getattr(source, "id", ""),
                    getattr(source, "name", ""),
                    getattr(source, "group", ""),
                    getattr(source, "region", ""),
                    getattr(source, "state", ""),
                )
                for source in rows
            ),
            tuple(sorted(checked)),
        )

        if signature == self._signature:
            return

        self.beginResetModel()
        self.rows = rows
        self.checked = set(checked)
        self._signature = signature
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None

        source = self.rows[index.row()]

        if role == self.SourceRole:
            return source

        if role == self.CheckedRole:
            return getattr(source, "id", "") in self.checked

        if role == Qt.ItemDataRole.DisplayRole:
            return getattr(source, "name", "")

        return None


class SourceDelegate(QStyledItemDelegate):
    toggled = Signal(str, bool)

    ROW_H = 62

    def sizeHint(self, option, index) -> QSize:
        return QSize(1000, self.ROW_H)

    @staticmethod
    def _rounded(painter, rect, fill, border, radius=8):
        painter.setBrush(QColor(fill))
        painter.setPen(QPen(QColor(border), 1))
        painter.drawRoundedRect(rect, radius, radius)

    @staticmethod
    def _check_rect(rect: QRect) -> QRect:
        return QRect(rect.left() + 14, rect.top() + 20, 22, 22)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        source = index.data(SourceListModel.SourceRole)
        checked = bool(index.data(SourceListModel.CheckedRole))

        if source is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        card = option.rect.adjusted(2, 3, -4, -3)
        self._rounded(painter, card, "#FFFFFF", "#DDEAF6", 9)

        checkbox = self._check_rect(card)

        if checked:
            self._rounded(painter, checkbox, "#0B6872", "#0B6872", 5)
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.drawText(checkbox, Qt.AlignmentFlag.AlignCenter, "✓")
        else:
            self._rounded(painter, checkbox, "#FFFFFF", "#7D8FA3", 5)

        badge = QRect(card.left() + 56, card.top() + 12, 54, 38)
        self._rounded(painter, badge, "#E9F4FF", "#E9F4FF", 8)

        painter.setPen(QColor("#087AF7"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(
            badge,
            Qt.AlignmentFlag.AlignCenter,
            (getattr(source, "name", "") or "F")[:2].upper(),
        )

        name_x = badge.right() + 13
        status_w = 120
        status_rect = QRect(
            card.right() - status_w - 14,
            card.top() + 14,
            status_w,
            34,
        )

        text_width = max(100, status_rect.left() - name_x - 16)

        name_rect = QRect(name_x, card.top() + 10, text_width, 22)
        meta_rect = QRect(name_x, card.top() + 31, text_width, 20)

        painter.setPen(QColor("#08245F"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        fm = QFontMetrics(painter.font())
        painter.drawText(
            name_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            fm.elidedText(
                getattr(source, "name", ""),
                Qt.TextElideMode.ElideRight,
                name_rect.width(),
            ),
        )

        region = getattr(source, "region", "Nacional") or "Nacional"
        state = getattr(source, "state", "") or "BR"
        group = getattr(source, "group", "") or "Fonte"

        painter.setPen(QColor("#6079A5"))
        painter.setFont(QFont("Segoe UI", 9))
        meta = f"{group}  •  {region}  •  {state}"
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(painter.font()).elidedText(
                meta,
                Qt.TextElideMode.ElideRight,
                meta_rect.width(),
            ),
        )

        self._rounded(painter, status_rect, "#EAF9F2", "#C2EBD8", 7)
        painter.setPen(QColor("#078B5F"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(
            status_rect,
            Qt.AlignmentFlag.AlignCenter,
            "Disponível",
        )

        painter.restore()

    def editorEvent(self, event, model, option, index) -> bool:
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False

        source = index.data(SourceListModel.SourceRole)
        if source is None:
            return False

        point = (
            event.position().toPoint()
            if hasattr(event, "position")
            else event.pos()
        )

        card = option.rect.adjusted(2, 3, -4, -3)
        checkbox = self._check_rect(card)

        # Permite clicar no checkbox OU na linha inteira até antes do status.
        clickable = QRect(
            card.left(),
            card.top(),
            card.width() - 140,
            card.height(),
        )

        if not checkbox.contains(point) and not clickable.contains(point):
            return False

        current = bool(index.data(SourceListModel.CheckedRole))
        self.toggled.emit(getattr(source, "id", ""), not current)
        return True


class SourcesPage(BasePage):
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

        self.model = SourceListModel(self)
        self.delegate = SourceDelegate(self)
        self.delegate.toggled.connect(self._toggle_source)

        self.list_view = QListView()
        self.list_view.setObjectName("sourceListView")
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
        self.list_view.setSpacing(0)

        self.root.addWidget(self.list_view, 1)

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
        QListView#sourceListView {
            background:transparent;
            border:0;
            outline:0;
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
            return {
                source.id
                for source in (
                    tuple(self.controller.news_sources)
                    + tuple(self.controller.specialized_sources)
                )
            }

        return set(self.controller.selected_news_source_ids)

    def _all_news_changed(self, checked: bool) -> None:
        if self._guard or self._tab() == 1:
            return

        self.controller.news_all_sources = checked

        if checked:
            self.controller.selected_news_source_ids = set()

        self.refresh(self.controller.state)

    def _toggle_source(self, source_id: str, checked: bool) -> None:
        if not source_id:
            return

        if self._tab() == 1:
            self.controller.set_video_source(source_id, checked)
            self.refresh(self.controller.state)
            return

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

        self.controller.set_news_source(source_id, checked)
        self.refresh(self.controller.state)

    def refresh(self, _state: UiState) -> None:
        tab = self._tab()
        visible = self._visible_sources()
        selected = self._selected_ids()

        self._guard = True
        self.all_news.blockSignals(True)

        self.all_news.setChecked(
            self.controller.news_all_sources
            if tab != 1
            else False
        )

        self.all_news.blockSignals(False)
        self._guard = False

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

        self.model.set_rows(visible, selected)

        selected_count = sum(
            1
            for source in visible
            if source.id in selected
        )

        self.info.setText(
            f"▦   {len(visible)} fonte(s) visível(is)   "
            f"{selected_count} selecionada(s) neste filtro"
        )

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
            if checked:
                self.controller.news_all_sources = True
                self.controller.selected_news_source_ids = set()
            else:
                self.controller.news_all_sources = False
                self.controller.selected_news_source_ids = set()

        else:
            ids = self._selected_ids()
            spec_ids = {
                source.id
                for source in self.controller.specialized_sources
            }

            if self.controller.news_all_sources:
                self.controller.news_all_sources = False

            self.controller.selected_news_source_ids = (
                ids | spec_ids
                if checked
                else ids - spec_ids
            )

        self.refresh(self.controller.state)
