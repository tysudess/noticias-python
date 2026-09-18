from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


class TermsPage(BasePage):
    """Gerenciamento dos termos de Notícias e Vídeos.

    Correções principais:
    - não recria as listas a cada refresh/tick da janela;
    - preserva seleção e posição do scroll;
    - permite selecionar um ou vários termos;
    - exclusão funciona para todos os itens selecionados;
    - usa o VideoTermStore real do RuntimeUiController quando disponível.
    """

    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)

        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)

        self._news_signature: tuple[str, ...] | None = None
        self._video_signature: tuple[str, ...] | None = None

        row = QHBoxLayout()
        row.setSpacing(12)
        self.root.addLayout(row, 1)

        self.news_list = QListWidget()
        self.video_list = QListWidget()

        self.news_count = QLabel()
        self.video_count = QLabel()

        row.addWidget(
            self._card(
                "▣",
                "Termos de Notícias",
                "Usados na varredura de matérias",
                self.news_list,
                self.news_count,
                self._add_news,
                self._remove_news_many,
                "blue",
            ),
            1,
        )

        row.addWidget(
            self._card(
                "▶",
                "Termos de Vídeos",
                "Lista independente para vídeos",
                self.video_list,
                self.video_count,
                self._add_video,
                self._remove_video_many,
                "purple",
            ),
            1,
        )

        self.setStyleSheet(self._stylesheet())

    # ------------------------------------------------------------------
    # DADOS
    # ------------------------------------------------------------------

    def _video_terms(self) -> list[str]:
        # Em produção, RuntimeUiController mantém a fonte real dos termos de
        # vídeo em VideoTermStore. Usamos esse estado primeiro.
        runtime_terms = getattr(
            self.controller,
            "video_terms",
            None,
        )

        if runtime_terms is not None:
            return sorted(
                {
                    str(value).strip()
                    for value in runtime_terms
                    if str(value).strip()
                },
                key=str.casefold,
            )

        # Fallback de compatibilidade para controllers antigos/testes.
        default = set(self.controller.state.terms)
        values = self.controller.prefs.get_string_set(
            "desktop_video_terms",
            default,
        )

        return sorted(
            {
                str(value).strip()
                for value in (values or set())
                if str(value).strip()
            },
            key=str.casefold,
        )

    def _add_news(self, value: str) -> None:
        value = value.strip()
        if not value:
            return

        self.controller.add_term(value)

    def _add_video(self, value: str) -> None:
        value = value.strip()
        if not value:
            return

        add_runtime = getattr(
            self.controller,
            "add_video_term",
            None,
        )

        if callable(add_runtime):
            add_runtime(value)
            return

        # Fallback de compatibilidade.
        terms = set(self._video_terms())
        terms.add(value)

        self.controller.prefs.update(
            desktop_video_terms=terms
        )
        self.controller.refresh()

    def _remove_news_many(
        self,
        values: list[str],
    ) -> None:
        # Copiamos os textos antes de qualquer refresh síncrono do controller.
        values = [
            value.strip()
            for value in values
            if value.strip()
        ]

        for value in values:
            self.controller.remove_term(value)

    def _remove_video_many(
        self,
        values: list[str],
    ) -> None:
        values = [
            value.strip()
            for value in values
            if value.strip()
        ]

        remove_runtime = getattr(
            self.controller,
            "remove_video_term",
            None,
        )

        if callable(remove_runtime):
            for value in values:
                remove_runtime(value)
            return

        # Fallback de compatibilidade.
        terms = set(self._video_terms())

        for value in values:
            terms.discard(value)

        self.controller.prefs.update(
            desktop_video_terms=terms
        )
        self.controller.refresh()

    # ------------------------------------------------------------------
    # COMPONENTES
    # ------------------------------------------------------------------

    def _card(
        self,
        icon_text,
        title_text,
        subtitle_text,
        listw,
        count_label,
        add_cb,
        remove_many_cb,
        tone,
    ):
        frame = QFrame()
        frame.setObjectName("termCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()

        icon = QLabel(icon_text)
        icon.setObjectName("termIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        icon.setFixedSize(54, 54)
        header.addWidget(icon)

        text = QVBoxLayout()

        title = QLabel(title_text)
        title.setObjectName("termTitle")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("termSubtitle")

        text.addWidget(title)
        text.addWidget(subtitle)

        header.addLayout(text, 1)

        count_label.setObjectName("termCount")
        header.addWidget(count_label)

        layout.addLayout(header)

        add_row = QHBoxLayout()

        edit = QLineEdit()
        edit.setObjectName("termInput")
        edit.setPlaceholderText(
            "⌕  Novo termo"
        )
        add_row.addWidget(edit, 1)

        add = QPushButton("+  Adicionar")
        add.setObjectName("termAdd")
        add_row.addWidget(add)

        layout.addLayout(add_row)

        listw.setObjectName("termList")

        # O problema anterior era agravado pelo refresh periódico da MainWindow:
        # a lista era apagada e reconstruída, fazendo a seleção desaparecer.
        # Agora permitimos seleção real e a preservamos no refresh.
        listw.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        listw.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        listw.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        listw.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        layout.addWidget(listw, 1)

        footer = QHBoxLayout()

        hint = QLabel(
            "Clique para selecionar • Ctrl permite selecionar vários"
        )
        hint.setObjectName("termHint")
        footer.addWidget(hint)

        footer.addStretch()

        delete = QPushButton(
            "▣  Excluir selecionado"
        )
        delete.setObjectName("termDelete")
        delete.setEnabled(False)
        footer.addWidget(delete)

        layout.addLayout(footer)

        def add_value() -> None:
            value = edit.text().strip()

            if not value:
                return

            add_cb(value)
            edit.clear()
            edit.setFocus()

        def selected_values() -> list[str]:
            return [
                item.text()
                for item in listw.selectedItems()
            ]

        def delete_selected() -> None:
            values = selected_values()

            if not values:
                return

            remove_many_cb(values)

        def update_delete_state() -> None:
            count = len(
                listw.selectedItems()
            )

            delete.setEnabled(
                count > 0
            )

            delete.setText(
                "▣  Excluir selecionado"
                if count <= 1
                else f"▣  Excluir {count} selecionados"
            )

        add.clicked.connect(add_value)
        edit.returnPressed.connect(add_value)
        delete.clicked.connect(delete_selected)

        listw.itemSelectionChanged.connect(
            update_delete_state
        )

        return frame

    # ------------------------------------------------------------------
    # REFRESH SEM PERDER SELEÇÃO
    # ------------------------------------------------------------------

    @staticmethod
    def _sync_list(
        listw: QListWidget,
        values: list[str],
        old_signature: tuple[str, ...] | None,
    ) -> tuple[str, ...]:
        clean_values = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        signature = tuple(clean_values)

        # Fundamental: se o conteúdo não mudou, NÃO fazemos clear().
        # A MainWindow atualiza a página periodicamente; limpar aqui fazia a
        # seleção desaparecer entre o clique do usuário e o botão Excluir.
        if signature == old_signature:
            return signature

        selected = {
            item.text()
            for item in listw.selectedItems()
        }

        current_text = (
            listw.currentItem().text()
            if listw.currentItem()
            else ""
        )

        scrollbar = listw.verticalScrollBar()
        scroll_value = scrollbar.value()

        listw.blockSignals(True)
        listw.clear()
        listw.addItems(clean_values)

        first_selected = None

        for row in range(
            listw.count()
        ):
            item = listw.item(row)

            if item.text() in selected:
                item.setSelected(True)

                if first_selected is None:
                    first_selected = item

            if (
                current_text
                and item.text()
                == current_text
            ):
                listw.setCurrentItem(item)

        if (
            listw.currentItem() is None
            and first_selected is not None
        ):
            listw.setCurrentItem(
                first_selected
            )

        listw.blockSignals(False)

        # Restauramos a posição depois da reconstrução.
        scrollbar.setValue(
            min(
                scroll_value,
                scrollbar.maximum(),
            )
        )

        # Garante que o estado visual do botão delete seja recalculado.
        listw.itemSelectionChanged.emit()

        return signature

    # ------------------------------------------------------------------
    # ESTILO
    # ------------------------------------------------------------------

    def _stylesheet(self) -> str:
        return """
        QFrame#termCard {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }

        QLabel#termIcon {
            border-radius:12px;
            font-size:22px;
            font-weight:900;
        }

        QLabel#termIcon[tone='blue'] {
            background:#E5F1FF;
            color:#087AF7;
        }

        QLabel#termIcon[tone='purple'] {
            background:#F0E4FF;
            color:#8244F5;
        }

        QLabel#termTitle {
            color:#08245F;
            font-size:18px;
            font-weight:900;
        }

        QLabel#termSubtitle {
            color:#6079A5;
            font-size:10px;
        }

        QLabel#termCount {
            background:#EAF4FF;
            color:#087AF7;
            border-radius:8px;
            padding:10px 14px;
            font-size:10px;
            font-weight:800;
        }

        QLabel#termHint {
            color:#7187A8;
            font-size:9px;
        }

        QLineEdit#termInput {
            min-height:34px;
            padding:0 10px;
        }

        QPushButton#termAdd {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:8px 14px;
            font-weight:800;
        }

        QListWidget#termList {
            background:transparent;
            border:0;
            outline:0;
        }

        QListWidget#termList::item {
            background:#F8FBFF;
            color:#183E72;
            border:1px solid #D8E7F6;
            border-radius:7px;
            padding:8px 10px;
            margin-bottom:4px;
        }

        QListWidget#termList::item:hover {
            background:#F1F7FE;
            border-color:#BDD7F0;
        }

        QListWidget#termList::item:selected {
            background:#DDEEFF;
            color:#075ECA;
            border:2px solid #1689F8;
            font-weight:800;
        }

        QPushButton#termDelete {
            background:#FFF1F4;
            color:#E03155;
            border:1px solid #FFB8C8;
            border-radius:8px;
            padding:8px 13px;
            font-weight:800;
        }

        QPushButton#termDelete:hover:enabled {
            background:#FFE5EB;
            border-color:#F47B95;
        }

        QPushButton#termDelete:disabled {
            background:#F4F6F9;
            color:#A9B2C1;
            border-color:#E0E5EC;
        }

        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            border-radius:5px;
        }

        QScrollBar::handle:vertical {
            background:#82B5E8;
            min-height:42px;
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

    # ------------------------------------------------------------------
    # ATUALIZAÇÃO
    # ------------------------------------------------------------------

    def refresh(
        self,
        state: UiState,
    ) -> None:
        news_terms = sorted(
            {
                str(value).strip()
                for value in state.terms
                if str(value).strip()
            },
            key=str.casefold,
        )

        video_terms = self._video_terms()

        self._news_signature = self._sync_list(
            self.news_list,
            news_terms,
            self._news_signature,
        )

        self._video_signature = self._sync_list(
            self.video_list,
            video_terms,
            self._video_signature,
        )

        self.news_count.setText(
            f"{len(news_terms)} termo(s)"
        )

        self.video_count.setText(
            f"{len(video_terms)} termo(s)"
        )
