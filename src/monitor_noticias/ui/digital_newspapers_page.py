from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.digital_newspapers.browser import (
    DigitalNewspaperBrowserDialog,
)
from monitor_noticias.digital_newspapers.providers import (
    DIGITAL_NEWSPAPER_PROVIDERS,
    DigitalNewspaperProvider,
)
from monitor_noticias.digital_newspapers.storage import (
    DigitalNewspaperHistoryEntry,
    DigitalNewspaperHistoryStore,
    SecureSessionStore,
)


class DigitalNewspapersPage(QWidget):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.providers = DIGITAL_NEWSPAPER_PROVIDERS
        self.history_store = DigitalNewspaperHistoryStore(paths)
        self.browser_dialogs: dict[str, DigitalNewspaperBrowserDialog] = {}
        self._selected_provider_id = (
            self.providers[0].id
            if self.providers
            else ""
        )
        self._build_ui()
        self._refresh_providers()
        self._refresh_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("digitalHero")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(16, 13, 16, 13)
        hl.setSpacing(12)

        icon = QLabel("▥")
        icon.setObjectName("digitalHeroIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(48, 48)
        hl.addWidget(icon)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title = QLabel("Jornais Digitais")
        title.setObjectName("digitalTitle")
        subtitle = QLabel(
            "Acesse suas próprias assinaturas e preserve o arquivo oficial sempre que o jornal disponibilizar PDF."
        )
        subtitle.setObjectName("digitalMuted")
        subtitle.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        hl.addLayout(text_box, 1)

        safe = QLabel("●  Sessões protegidas localmente")
        safe.setObjectName("digitalSafeChip")
        hl.addWidget(safe)
        root.addWidget(hero)

        content = QHBoxLayout()
        content.setSpacing(10)

        providers_card = QFrame()
        providers_card.setObjectName("digitalCard")
        providers_layout = QVBoxLayout(providers_card)
        providers_layout.setContentsMargins(14, 12, 14, 12)
        providers_layout.setSpacing(8)

        providers_title = QLabel("Jornais disponíveis")
        providers_title.setObjectName("digitalSectionTitle")
        providers_layout.addWidget(providers_title)

        self.provider_table = QTableWidget(0, 4)
        self.provider_table.setObjectName("digitalProviders")
        self.provider_table.setHorizontalHeaderLabels(
            ["Jornal", "Sessão", "Edição", "PDF"]
        )
        self.provider_table.verticalHeader().setVisible(False)
        self.provider_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.provider_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.provider_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.provider_table.setAlternatingRowColors(True)
        self.provider_table.setShowGrid(False)
        header = self.provider_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.provider_table.itemSelectionChanged.connect(
            self._selection_changed
        )
        self.provider_table.cellDoubleClicked.connect(
            lambda _row, _col: self.download_current()
        )
        providers_layout.addWidget(self.provider_table, 1)
        content.addWidget(providers_card, 3)

        action_card = QFrame()
        action_card.setObjectName("digitalCard")
        action_card.setMinimumWidth(360)
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)
        action_layout.setSpacing(10)

        action_title = QLabel("Edição selecionada")
        action_title.setObjectName("digitalSectionTitle")
        action_layout.addWidget(action_title)

        self.selected_name = QLabel("—")
        self.selected_name.setObjectName("digitalSelectedName")
        self.selected_name.setWordWrap(True)
        action_layout.addWidget(self.selected_name)

        self.selected_note = QLabel("—")
        self.selected_note.setObjectName("digitalMuted")
        self.selected_note.setWordWrap(True)
        action_layout.addWidget(self.selected_note)

        date_label = QLabel("Data da edição")
        date_label.setObjectName("digitalCaption")
        action_layout.addWidget(date_label)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.dateChanged.connect(
            self._date_changed
        )
        action_layout.addWidget(self.date_edit)

        self.open_button = QPushButton("↗  Abrir edição / entrar")
        self.open_button.setObjectName("digitalPrimary")
        self.open_button.clicked.connect(self.open_current)
        action_layout.addWidget(self.open_button)

        self.download_button = QPushButton("⇩  Baixar edição completa")
        self.download_button.setObjectName("digitalDownload")
        self.download_button.clicked.connect(self.download_current)
        action_layout.addWidget(self.download_button)

        self.clear_session_button = QPushButton("×  Limpar sessão deste jornal")
        self.clear_session_button.setProperty("secondary", True)
        self.clear_session_button.clicked.connect(self.clear_current_session)
        action_layout.addWidget(self.clear_session_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        action_layout.addWidget(self.progress)

        self.status = QLabel(
            "Selecione um jornal. O primeiro acesso abre o login oficial dentro da Central."
        )
        self.status.setObjectName("digitalStatus")
        self.status.setWordWrap(True)
        action_layout.addWidget(self.status)

        rule = QLabel(
            "Qualidade: PDF oficial → exportação autorizada → páginas HD autorizadas. "
            "Captura de tela não é usada como PDF oficial."
        )
        rule.setObjectName("digitalRule")
        rule.setWordWrap(True)
        action_layout.addWidget(rule)

        action_layout.addStretch(1)
        content.addWidget(action_card, 2)
        root.addLayout(content, 3)

        history_card = QFrame()
        history_card.setObjectName("digitalCard")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(14, 12, 14, 12)
        history_layout.setSpacing(8)

        history_head = QHBoxLayout()
        history_title = QLabel("Histórico")
        history_title.setObjectName("digitalSectionTitle")
        history_head.addWidget(history_title)
        history_head.addStretch(1)

        open_folder = QPushButton("▣  Abrir pasta")
        open_folder.setProperty("secondary", True)
        open_folder.clicked.connect(self.open_output_folder)
        history_head.addWidget(open_folder)

        clear_history = QPushButton("Limpar histórico")
        clear_history.setProperty("danger", True)
        clear_history.clicked.connect(self.clear_history)
        history_head.addWidget(clear_history)
        history_layout.addLayout(history_head)

        self.history_table = QTableWidget(0, 7)
        self.history_table.setObjectName("digitalHistory")
        self.history_table.setHorizontalHeaderLabels(
            [
                "Jornal",
                "Data",
                "Páginas",
                "Qualidade",
                "Método",
                "Arquivo",
                "Status",
            ]
        )
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.history_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        h = self.history_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        history_layout.addWidget(self.history_table, 1)
        root.addWidget(history_card, 2)

        self.setStyleSheet(self._stylesheet())

    def _stylesheet(self) -> str:
        return """
        QFrame#digitalHero, QFrame#digitalCard {
            background:#FFFFFF;
            border:1px solid #D6E6F7;
            border-radius:14px;
        }
        QLabel#digitalHeroIcon {
            background:#E7F3FF;
            color:#087AF7;
            border-radius:12px;
            font-size:25px;
            font-weight:900;
        }
        QLabel#digitalTitle {
            color:#08245F;
            font-size:20px;
            font-weight:900;
        }
        QLabel#digitalSectionTitle {
            color:#08245F;
            font-size:14px;
            font-weight:900;
        }
        QLabel#digitalSelectedName {
            color:#087AF7;
            font-size:18px;
            font-weight:900;
        }
        QLabel#digitalMuted {
            color:#6079A5;
            font-size:10px;
        }
        QLabel#digitalCaption {
            color:#315783;
            font-size:10px;
            font-weight:800;
        }
        QLabel#digitalSafeChip {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #BFE8D5;
            border-radius:9px;
            padding:7px 10px;
            font-weight:800;
        }
        QLabel#digitalStatus {
            background:#EDF6FF;
            color:#24548A;
            border:1px solid #D1E5F8;
            border-radius:9px;
            padding:10px;
            min-height:42px;
        }
        QLabel#digitalRule {
            background:#FFF8E8;
            color:#735310;
            border:1px solid #F4D991;
            border-radius:9px;
            padding:10px;
            font-size:10px;
        }
        QPushButton#digitalPrimary, QPushButton#digitalDownload {
            min-height:34px;
            font-weight:900;
        }
        QPushButton#digitalDownload {
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #087AF7,stop:1 #16A3EE);
        }
        QTableWidget#digitalProviders, QTableWidget#digitalHistory {
            background:white;
            border:1px solid #DFEAF6;
            border-radius:9px;
            alternate-background-color:#F8FBFF;
            selection-background-color:#E7F3FF;
            selection-color:#08245F;
        }
        QTableWidget::item {
            padding:5px;
        }
        """

    def _selected_provider(self) -> DigitalNewspaperProvider | None:
        for provider in self.providers:
            if provider.id == self._selected_provider_id:
                return provider
        return None

    def _selection_changed(self) -> None:
        rows = self.provider_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        item = self.provider_table.item(row, 0)
        if item is None:
            return
        provider_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if provider_id:
            self._selected_provider_id = provider_id
        self._sync_selected_panel()

    def _sync_selected_panel(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            self.selected_name.setText("—")
            self.selected_note.setText("—")
            self.download_button.setEnabled(False)
            return

        self.selected_name.setText(provider.name)
        self.selected_note.setText(
            f"{provider.edition_kind}. {provider.note}"
        )
        self.download_button.setEnabled(provider.can_try_download)
        self.download_button.setToolTip(
            "Procura apenas PDF/download/exportação oferecidos pelo próprio site."
            if provider.can_try_download
            else "A edição completa está documentada somente no aplicativo oficial."
        )

    def _refresh_providers(self) -> None:
        self.provider_table.setRowCount(len(self.providers))

        selected_row = 0
        for row, provider in enumerate(self.providers):
            if provider.id == self._selected_provider_id:
                selected_row = row

            vault = SecureSessionStore(self.paths, provider.id)
            session = "Sessão local" if vault.exists() else "Sem sessão"
            pdf = (
                "PDF oficial"
                if provider.official_pdf_documented
                else (
                    "Exportação"
                    if provider.can_try_download
                    else "App"
                )
            )

            values = (
                provider.name,
                session,
                provider.edition_kind,
                pdf,
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        provider.id,
                    )
                self.provider_table.setItem(row, col, item)

        if self.providers:
            self.provider_table.selectRow(selected_row)
        self._sync_selected_panel()

    def _date_value(self) -> date:
        qdate = self.date_edit.date()
        return date(qdate.year(), qdate.month(), qdate.day())

    def _date_changed(self, _value) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        dialog = self.browser_dialogs.get(provider.id)
        if dialog is not None:
            dialog.set_target_date(self._date_value())

    def _browser_for(
        self,
        provider: DigitalNewspaperProvider,
    ) -> DigitalNewspaperBrowserDialog:
        dialog = self.browser_dialogs.get(provider.id)
        if dialog is not None:
            dialog.set_target_date(self._date_value())
            return dialog

        dialog = DigitalNewspaperBrowserDialog(
            paths=self.paths,
            provider=provider,
            target_date=self._date_value(),
            parent=self.window(),
        )
        dialog.status_changed.connect(self._browser_status)
        dialog.session_changed.connect(
            lambda _has, pid=provider.id:
                self._session_changed(pid)
        )
        dialog.pdf_completed.connect(
            lambda path, pages, method, p=provider:
                self._pdf_completed(p, path, pages, method)
        )
        dialog.finished.connect(
            lambda _result, pid=provider.id:
                self.browser_dialogs.pop(pid, None)
        )
        self.browser_dialogs[provider.id] = dialog
        return dialog

    def open_current(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        dialog = self._browser_for(provider)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.status.setText(
            f"{provider.name}: navegador interno aberto. Faça login diretamente no site do jornal."
        )

    def download_current(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return

        if not provider.can_try_download:
            self.status.setText(
                f"{provider.name}: a edição completa está documentada somente no aplicativo oficial; "
                "a V77 não extrai o pacote interno do app."
            )
            return

        dialog = self._browser_for(provider)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.try_download_edition()
        self.progress.show()

    def clear_current_session(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        dialog = self.browser_dialogs.get(provider.id)
        if dialog is not None:
            dialog.clear_session()
        else:
            SecureSessionStore(self.paths, provider.id).clear()
        self.status.setText(
            f"{provider.name}: sessão protegida removida."
        )
        self._refresh_providers()

    def _browser_status(self, text: str) -> None:
        self.status.setText(text)
        if (
            "concluído" in text.lower()
            or "nenhum download" in text.lower()
            or "cancelado" in text.lower()
            or "interrompido" in text.lower()
        ):
            self.progress.hide()

    def _session_changed(self, _provider_id: str) -> None:
        self._refresh_providers()

    def _pdf_completed(
        self,
        provider: DigitalNewspaperProvider,
        path: str,
        pages: int,
        method: str,
    ) -> None:
        output = Path(path)
        entry = DigitalNewspaperHistoryEntry.completed(
            newspaper=provider.name,
            provider_id=provider.id,
            edition_date=self._date_value().isoformat(),
            pages=pages,
            quality="Original / sem recompressão",
            method=method,
            path=output,
        )
        self.history_store.append(entry)
        self.progress.hide()
        self.status.setText(
            f"✓ {provider.name}: PDF salvo sem recompressão em {output}"
        )
        self._refresh_history()

    def _refresh_history(self) -> None:
        rows = self.history_store.list(limit=100)
        self.history_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            values = (
                entry.newspaper,
                entry.edition_date,
                str(entry.pages or "—"),
                entry.quality,
                entry.method,
                entry.path,
                entry.status,
            )
            for col, value in enumerate(values):
                self.history_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(value),
                )

    def clear_history(self) -> None:
        self.history_store.clear()
        self._refresh_history()
        self.status.setText("Histórico de Jornais Digitais limpo.")

    def open_output_folder(self) -> None:
        folder = Path(self.paths.state_root) / "JornaisDigitais"
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(folder))
        )

    def refresh(self, _state=None) -> None:
        pass

    def shutdown(self) -> None:
        for dialog in list(self.browser_dialogs.values()):
            try:
                dialog.close()
            except Exception:
                pass
        self.browser_dialogs.clear()
