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
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
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
    SecureCredentialStore,
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
            "Clique no jornal para baixar automaticamente a edição da data selecionada. "
            "Quando houver PDF oficial, o arquivo original é preservado sem recompressão."
        )
        subtitle.setObjectName("digitalMuted")
        subtitle.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        hl.addLayout(text_box, 1)

        safe = QLabel("●  Download automático • sessão protegida")
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

        providers_title = QLabel("Clique no jornal para baixar")
        providers_title.setObjectName("digitalSectionTitle")
        providers_layout.addWidget(providers_title)

        providers_help = QLabel(
            "Um clique inicia o download da edição completa. Nenhuma janela de navegador "
            "é aberta durante o fluxo normal."
        )
        providers_help.setObjectName("digitalMuted")
        providers_help.setWordWrap(True)
        providers_layout.addWidget(providers_help)

        self.provider_table = QTableWidget(0, 4)
        self.provider_table.setObjectName("digitalProviders")
        self.provider_table.setHorizontalHeaderLabels(
            ["Jornal", "Sessão", "Edição", "Método"]
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
        self.provider_table.cellClicked.connect(
            self._provider_clicked
        )
        providers_layout.addWidget(self.provider_table, 1)
        content.addWidget(providers_card, 3)

        action_card = QFrame()
        action_card.setObjectName("digitalCard")
        action_card.setMinimumWidth(430)
        action_card.setMinimumHeight(620)
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
        self.date_edit.setMinimumHeight(38)
        self.date_edit.dateChanged.connect(
            self._date_changed
        )
        action_layout.addWidget(self.date_edit)

        credentials_label = QLabel("Acesso local do jornal")
        credentials_label.setObjectName("digitalCaption")
        credentials_label.setToolTip(
            "Opcional. Usuário e senha ficam criptografados somente neste computador."
        )
        action_layout.addWidget(credentials_label)

        self.credential_user = QLineEdit()
        self.credential_user.setPlaceholderText("Usuário / e-mail")
        self.credential_user.setObjectName("digitalCredential")
        self.credential_user.setReadOnly(False)
        self.credential_user.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.credential_user.setMinimumHeight(38)
        self.credential_user.setClearButtonEnabled(True)
        action_layout.addWidget(self.credential_user)

        self.credential_password = QLineEdit()
        self.credential_password.setPlaceholderText("Senha")
        self.credential_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.credential_password.setObjectName("digitalCredential")
        self.credential_password.setReadOnly(False)
        self.credential_password.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.credential_password.setMinimumHeight(38)
        action_layout.addWidget(self.credential_password)

        credential_actions = QHBoxLayout()
        credential_actions.setSpacing(6)

        self.save_credentials_button = QPushButton("Salvar acesso neste PC")
        self.save_credentials_button.setProperty("secondary", True)
        self.save_credentials_button.clicked.connect(self.save_current_credentials)
        self.save_credentials_button.setMinimumHeight(38)
        credential_actions.addWidget(self.save_credentials_button, 1)

        self.clear_credentials_button = QPushButton("Apagar acesso")
        self.clear_credentials_button.setProperty("danger", True)
        self.clear_credentials_button.clicked.connect(self.clear_current_credentials)
        self.clear_credentials_button.setMinimumHeight(38)
        credential_actions.addWidget(self.clear_credentials_button)

        action_layout.addLayout(credential_actions)

        self.download_button = QPushButton("⇩  Baixar edição completa agora")
        self.download_button.setObjectName("digitalDownload")
        self.download_button.clicked.connect(self.download_current)
        self.download_button.setMinimumHeight(42)
        action_layout.addWidget(self.download_button)

        self.open_button = QPushButton("↗  Entrar / renovar sessão")
        self.open_button.setProperty("secondary", True)
        self.open_button.clicked.connect(self.open_current)
        self.open_button.setMinimumHeight(40)
        self.open_button.setToolTip(
            "Use somente quando o jornal informar que a autenticação expirou. "
            "O download normal não abre navegador."
        )
        action_layout.addWidget(self.open_button)

        self.clear_session_button = QPushButton("×  Limpar sessão deste jornal")
        self.clear_session_button.setProperty("secondary", True)
        self.clear_session_button.clicked.connect(self.clear_current_session)
        self.clear_session_button.setMinimumHeight(40)
        action_layout.addWidget(self.clear_session_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        action_layout.addWidget(self.progress)

        self.status = QLabel(
            "Clique em um jornal à esquerda. A Central tentará baixar diretamente "
            "a edição completa da data selecionada."
        )
        self.status.setObjectName("digitalStatus")
        self.status.setWordWrap(True)
        action_layout.addWidget(self.status)

        rule = QLabel(
            "Qualidade: PDF oficial → exportação autorizada → páginas HD autorizadas. "
            "Não há quebra de DRM, CAPTCHA ou paywall. Se você salvar o acesso, "
            "ele fica criptografado somente neste computador e nunca entra no GitHub."
        )
        rule.setObjectName("digitalRule")
        rule.setWordWrap(True)
        action_layout.addWidget(rule)

        action_layout.addStretch(1)

        # V83: preserva alturas confortáveis mesmo quando a janela não tem
        # espaço vertical suficiente. O painel direito passa a rolar em vez
        # de achatar/encavalar campos e botões.
        action_scroll = QScrollArea()
        action_scroll.setObjectName("digitalActionScroll")
        action_scroll.setWidgetResizable(True)
        action_scroll.setFrameShape(QFrame.Shape.NoFrame)
        action_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        action_scroll.setWidget(action_card)
        action_scroll.setMinimumWidth(430)
        content.addWidget(action_scroll, 2)
        root.addLayout(content, 4)

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
        root.addWidget(history_card, 1)

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
        QPushButton#digitalDownload {
            min-height:38px;
            font-weight:900;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #087AF7,stop:1 #16A3EE);
        }
        QLineEdit#digitalCredential {
            background:#FFFFFF;
            color:#08245F;
            border:1px solid #CADCEF;
            border-radius:8px;
            padding:8px 10px;
            min-height:34px;
            font-size:11px;
        }
        QLineEdit#digitalCredential:focus {
            border:2px solid #087AF7;
            background:#FFFFFF;
        }
        QScrollArea#digitalActionScroll {
            background:transparent;
            border:0;
        }
        QScrollArea#digitalActionScroll > QWidget > QWidget {
            background:transparent;
        }
        QTableWidget#digitalProviders, QTableWidget#digitalHistory {
            background:white;
            border:1px solid #DFEAF6;
            border-radius:9px;
            alternate-background-color:#F8FBFF;
            selection-background-color:#E7F3FF;
            selection-color:#08245F;
        }
        QTableWidget#digitalProviders::item {
            padding:7px 5px;
        }
        QTableWidget#digitalHistory::item {
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

    def _provider_clicked(self, row: int, _column: int) -> None:
        item = self.provider_table.item(row, 0)
        if item is None:
            return

        provider_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not provider_id:
            return

        self._selected_provider_id = provider_id
        self.provider_table.selectRow(row)
        self._sync_selected_panel()
        self.download_current()

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
            "Baixa a edição completa automaticamente, sem abrir navegador."
            if provider.can_try_download
            else "A edição completa está documentada somente no aplicativo oficial."
        )
        self._load_selected_credentials()

    def _refresh_providers(self) -> None:
        self.provider_table.setRowCount(len(self.providers))

        selected_row = 0
        for row, provider in enumerate(self.providers):
            if provider.id == self._selected_provider_id:
                selected_row = row

            vault = SecureSessionStore(self.paths, provider.id)
            credentials = SecureCredentialStore(self.paths, provider.id)
            has_session = vault.exists()
            has_credentials = credentials.exists()
            if has_session and has_credentials:
                session = "Sessão + acesso"
            elif has_session:
                session = "Sessão local"
            elif has_credentials:
                session = "Acesso salvo"
            else:
                session = "Sem sessão"

            if provider.supports_direct_pdf:
                method = "PDF direto"
            elif provider.official_pdf_documented:
                method = "PDF oficial"
            elif provider.can_try_download:
                method = "Exportação"
            else:
                method = "App"

            values = (
                provider.name,
                session,
                provider.edition_kind,
                method,
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

    def _credential_store(
        self,
        provider: DigitalNewspaperProvider,
    ) -> SecureCredentialStore:
        return SecureCredentialStore(self.paths, provider.id)

    def _load_selected_credentials(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            self.credential_user.clear()
            self.credential_password.clear()
            return

        store = self._credential_store(provider)
        saved = store.load()
        self.credential_password.clear()
        if saved is None:
            self.credential_user.clear()
            self.credential_password.setPlaceholderText("Senha")
            return

        username, _password = saved
        self.credential_user.setText(username)
        self.credential_password.setPlaceholderText("Senha salva localmente")

    def save_current_credentials(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return

        username = self.credential_user.text().strip()
        password = self.credential_password.text()
        if not username or not password:
            self.status.setText(
                "Informe usuário/e-mail e senha para salvar o acesso localmente."
            )
            return

        try:
            self._credential_store(provider).save(username, password)
        except Exception as exc:
            self.status.setText(
                f"{provider.name}: não foi possível salvar no cofre seguro: {exc}"
            )
            return

        self.credential_password.clear()
        self.credential_password.setPlaceholderText("Senha salva localmente")
        self.status.setText(
            f"{provider.name}: acesso salvo criptografado somente neste computador."
        )
        self._refresh_providers()

    def clear_current_credentials(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        self._credential_store(provider).clear()
        self.credential_user.clear()
        self.credential_password.clear()
        self.credential_password.setPlaceholderText("Senha")
        self.status.setText(
            f"{provider.name}: usuário e senha locais removidos."
        )
        self._refresh_providers()

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
        dialog.prepare_manual_login()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self.status.setText(
            f"{provider.name}: janela de autenticação aberta. Se houver acesso salvo "
            "localmente, a Central preencherá os campos sem expor a senha no código."
        )

    def download_current(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return

        if not provider.can_try_download:
            self.status.setText(
                f"{provider.name}: a edição completa está documentada somente no "
                "aplicativo oficial; a Central não extrai o pacote interno do app."
            )
            self.progress.hide()
            return

        dialog = self._browser_for(provider)
        dialog.set_target_date(self._date_value())

        # V78: CRÍTICO — não chamar show()/raise_()/activateWindow() aqui.
        # O fluxo normal acontece inteiramente em segundo plano.
        dialog.start_automatic_download()
        self.progress.show()
        self.status.setText(
            f"{provider.name}: buscando a edição completa de "
            f"{self._date_value().strftime('%d/%m/%Y')} em segundo plano…"
        )

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
        lowered = text.lower()
        if any(
            marker in lowered
            for marker in (
                "concluído",
                "nenhum pdf",
                "não está disponível",
                "autenticação necessária",
                "sessão pode precisar",
                "cancelado",
                "interrompido",
                "não era um pdf",
                "não passou na validação",
                "respondeu http",
                "não concluiu o carregamento",
            )
        ):
            self.progress.hide()

    def _session_changed(self, provider_id: str) -> None:
        # V83: não chamar _refresh_providers() aqui. Durante o login oculto
        # vários cookies chegam em sequência; a atualização completa recarregava
        # o painel selecionado e apagava o que o usuário estava digitando nos
        # campos de usuário/senha. Atualizamos somente a célula de sessão.
        for row, provider in enumerate(self.providers):
            if provider.id != provider_id:
                continue

            vault = SecureSessionStore(self.paths, provider.id)
            credentials = SecureCredentialStore(self.paths, provider.id)
            has_session = vault.exists()
            has_credentials = credentials.exists()
            if has_session and has_credentials:
                session = "Sessão + acesso"
            elif has_session:
                session = "Sessão local"
            elif has_credentials:
                session = "Acesso salvo"
            else:
                session = "Sem sessão"

            item = self.provider_table.item(row, 1)
            if item is None:
                item = QTableWidgetItem(session)
                self.provider_table.setItem(row, 1, item)
            else:
                item.setText(session)
            break

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
            f"✓ {provider.name}: edição completa salva em PDF sem recompressão: {output}"
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
                dialog.shutdown()
                dialog.close()
            except Exception:
                pass
        self.browser_dialogs.clear()
