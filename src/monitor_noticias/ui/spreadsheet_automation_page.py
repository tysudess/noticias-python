from __future__ import annotations

import base64
import json
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage


_EVENT_PREFIX = "CENTRAL_EVENT:"


class SpreadsheetAutomationPage(BasePage):
    """Automação WhatsApp -> Google Planilhas integrada ao Central.

    A interface é 100% PySide6 e faz parte do mesmo QStackedWidget do programa.
    Somente o motor Node/whatsapp-web.js roda como processo invisível em segundo
    plano. A página controla o processo, mostra QR Code, status e logs.

    Regra de rede:
    - proxy geral do Central DESATIVADO -> conexão direta;
    - proxy geral do Central ATIVADO -> o motor herda o proxy do Central;
    - não existe proxy próprio nesta página e nenhuma senha é gravada no JSON.
    """

    def __init__(
        self,
        controller: MainUiController,
        app_root: Path,
    ) -> None:
        super().__init__(controller)

        self.app_root = Path(app_root)
        self.tool_dir = self.app_root / "tools" / "spreadsheet_automation"
        self.engine_path = self.tool_dir / "engine" / "index.js"
        self.node_path = self.tool_dir / "node.exe"

        self.runtime_dir = self.app_root / "data" / "spreadsheet_automation"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.runtime_dir / "config.json"
        self.state_dir = self.runtime_dir / "state"
        self.auth_dir = self.runtime_dir / "whatsapp-auth"
        self.log_path = self.app_root / "logs" / "spreadsheet_automation.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.process: QProcess | None = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._manual_stop = False
        self._restart_attempts = 0
        self._network_signature_at_start: tuple | None = None

        self.stats = {
            "motor": "PARADO",
            "whatsapp": "DESCONHECIDO",
            "planilha": "AGUARDANDO",
            "network": "CONEXÃO DIRETA",
            "processadas": 0,
            "videos": 0,
            "erros": 0,
            "ultima_linha": "--",
            "ultima_atualizacao": "--",
        }
        self.last_news = {
            "titulo": "Nenhuma notícia processada ainda",
            "veiculo": "--",
            "data": "--",
            "assunto": "--",
            "analise": "--",
            "autor": "--",
            "link": "",
        }

        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(10)

        self._ensure_config()
        self._build_ui()
        self._load_config_into_form()
        self._update_network_preview()
        self._update_status_ui()

    # ------------------------------------------------------------------
    # CONFIGURAÇÃO LOCAL (SEM PROXY)
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_config() -> dict:
        return {
            "appsScriptUrl": "",
            "diagnosticoGrupos": False,
            "chromePath": "",
            "grupos": [],
        }

    def _ensure_config(self) -> None:
        if self.config_path.is_file():
            return

        default_file = self.tool_dir / "config.default.json"

        if default_file.is_file():
            try:
                cfg = json.loads(default_file.read_text(encoding="utf-8"))
                if isinstance(cfg, dict):
                    cfg.pop("proxy", None)
                    self._write_config(cfg)
                    return
            except Exception:
                pass

        self._write_config(self._fallback_config())

    def _read_config(self) -> dict:
        self._ensure_config()

        try:
            cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(cfg, dict):
                raise ValueError("configuração inválida")
        except Exception:
            cfg = self._fallback_config()

        # Garante que configurações antigas não mantenham credenciais de proxy.
        cfg.pop("proxy", None)
        cfg.setdefault("appsScriptUrl", "")
        cfg.setdefault("diagnosticoGrupos", False)
        cfg.setdefault("chromePath", "")
        cfg.setdefault("grupos", [])
        return cfg

    def _write_config(self, cfg: dict) -> None:
        clean = dict(cfg)
        clean.pop("proxy", None)
        clean["appsScriptUrl"] = str(clean.get("appsScriptUrl", "")).strip()
        clean["chromePath"] = str(clean.get("chromePath", "")).strip()
        clean["diagnosticoGrupos"] = bool(clean.get("diagnosticoGrupos", False))
        clean["grupos"] = [
            str(value).strip()
            for value in (clean.get("grupos", []) or [])
            if str(value).strip()
        ]

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.config_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(clean, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.config_path)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        nav = QFrame()
        nav.setObjectName("sheetNav")
        nav_l = QHBoxLayout(nav)
        nav_l.setContentsMargins(8, 7, 8, 7)
        nav_l.setSpacing(7)

        self.nav_buttons: list[QPushButton] = []
        self.views = QStackedWidget()

        for idx, label in enumerate(("Painel", "WhatsApp", "Configurações", "Log", "Sobre")):
            btn = QPushButton(label)
            btn.setObjectName("sheetTab")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda _=False, i=idx: self._set_view(i))
            nav_l.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_l.addStretch()

        self.network_chip = QLabel("Rede: conexão direta")
        self.network_chip.setObjectName("sheetNetworkChip")
        nav_l.addWidget(self.network_chip)

        self.root.addWidget(nav)
        self.root.addWidget(self.views, 1)

        self.views.addWidget(self._build_dashboard())
        self.views.addWidget(self._build_whatsapp())
        self.views.addWidget(self._build_settings())
        self.views.addWidget(self._build_log())
        self.views.addWidget(self._build_about())

        self.setStyleSheet(self._stylesheet())

    def _set_view(self, index: int) -> None:
        self.views.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

        # A aba WhatsApp usa a MESMA página controlada pelo whatsapp-web.js.
        # O motor envia capturas JPEG da página real para dentro do PySide.
        if index == 1:
            self._send_engine_command("VIEW_ON")
            self._send_engine_command("SCREENSHOT")
        else:
            self._send_engine_command("VIEW_OFF")

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)

        self.status_whatsapp = self._status_card(
            cards,
            "WhatsApp",
            "DESCONHECIDO",
            "Sessão do WhatsApp Web",
            "◉",
            "green",
        )
        self.status_sheet = self._status_card(
            cards,
            "Planilha",
            "AGUARDANDO",
            "Conexão com Apps Script",
            "▦",
            "blue",
        )
        self.status_motor = self._status_card(
            cards,
            "Motor",
            "PARADO",
            "Monitoramento dos grupos",
            "▶",
            "purple",
        )
        self.status_network = self._status_card(
            cards,
            "Rede",
            "DIRETA",
            "Usa o proxy geral do Central quando ativado",
            "⌁",
            "orange",
        )

        layout.addLayout(cards)

        self.qr_frame = QFrame()
        self.qr_frame.setObjectName("sheetQrCard")
        qr_l = QHBoxLayout(self.qr_frame)
        qr_l.setContentsMargins(16, 12, 16, 12)
        qr_l.setSpacing(18)

        self.qr_image = QLabel("QR")
        self.qr_image.setObjectName("sheetQrImage")
        self.qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_image.setFixedSize(190, 190)
        qr_l.addWidget(self.qr_image)

        qr_text = QVBoxLayout()
        qr_title = QLabel("Autenticação do WhatsApp")
        qr_title.setObjectName("sheetSectionTitle")
        qr_help = QLabel(
            "Abra WhatsApp → Aparelhos conectados → Conectar aparelho e leia este QR Code. "
            "Depois da primeira autenticação, a sessão fica salva dentro do Central."
        )
        qr_help.setObjectName("sheetMuted")
        qr_help.setWordWrap(True)
        self.qr_status = QLabel("Aguardando o motor solicitar autenticação.")
        self.qr_status.setObjectName("sheetInfoStrip")
        qr_text.addWidget(qr_title)
        qr_text.addWidget(qr_help)
        qr_text.addWidget(self.qr_status)
        qr_text.addStretch()
        qr_l.addLayout(qr_text, 1)

        self.qr_frame.hide()
        layout.addWidget(self.qr_frame)

        content = QHBoxLayout()
        content.setSpacing(10)

        groups_card = QFrame()
        groups_card.setObjectName("sheetCard")
        gl = QVBoxLayout(groups_card)
        gl.setContentsMargins(14, 12, 14, 12)
        gl.setSpacing(8)
        gl.addWidget(self._section_title("Grupos monitorados"))

        self.groups_box = QVBoxLayout()
        self.groups_box.setSpacing(6)
        gl.addLayout(self.groups_box)
        gl.addStretch()
        self.group_total = QLabel("Total: 0 grupos")
        self.group_total.setObjectName("sheetGreenText")
        gl.addWidget(self.group_total)
        content.addWidget(groups_card, 1)

        summary_card = QFrame()
        summary_card.setObjectName("sheetCard")
        sl = QVBoxLayout(summary_card)
        sl.setContentsMargins(14, 12, 14, 12)
        sl.setSpacing(4)
        sl.addWidget(self._section_title("Resumo geral"))
        self.metric_processadas = self._metric_row(sl, "Mensagens processadas", "0", True)
        self.metric_update = self._metric_row(sl, "Última atualização", "--")
        self.metric_videos = self._metric_row(sl, "Vídeos processados", "0")
        self.metric_errors = self._metric_row(sl, "Erros", "0")
        self.metric_line = self._metric_row(sl, "Última linha", "--")
        self.metric_network = self._metric_row(sl, "Rede", "Conexão direta")
        sl.addStretch()
        content.addWidget(summary_card, 1)

        news_card = QFrame()
        news_card.setObjectName("sheetCard")
        nl = QVBoxLayout(news_card)
        nl.setContentsMargins(14, 12, 14, 12)
        nl.setSpacing(5)
        nl.addWidget(self._section_title("Última notícia processada"))

        self.last_title = self._news_field(nl, "Título", "Nenhuma notícia processada ainda", strong=True)
        two = QHBoxLayout()
        self.last_vehicle = self._small_field(two, "Veículo", "--")
        self.last_date = self._small_field(two, "Data", "--")
        nl.addLayout(two)
        two2 = QHBoxLayout()
        self.last_subject = self._small_field(two2, "Assunto", "--")
        self.last_analysis = self._small_field(two2, "Análise", "--")
        nl.addLayout(two2)
        self.last_author = self._news_field(nl, "Autor", "--")
        self.last_link = self._news_field(nl, "Link", "--")
        nl.addStretch()
        content.addWidget(news_card, 2)

        layout.addLayout(content, 1)

        controls = QFrame()
        controls.setObjectName("sheetControls")
        ctl = QHBoxLayout(controls)
        ctl.setContentsMargins(10, 9, 10, 9)
        ctl.setSpacing(8)

        self.start_btn = QPushButton("▶  INICIAR")
        self.start_btn.setObjectName("sheetPrimary")
        self.start_btn.clicked.connect(self.start_engine)
        ctl.addWidget(self.start_btn)

        self.stop_btn = QPushButton("■  PARAR")
        self.stop_btn.setObjectName("sheetDanger")
        self.stop_btn.clicked.connect(self.stop_engine)
        self.stop_btn.setEnabled(False)
        ctl.addWidget(self.stop_btn)

        self.restart_btn = QPushButton("↻  REINICIAR")
        self.restart_btn.setObjectName("sheetSecondary")
        self.restart_btn.clicked.connect(self.restart_engine)
        ctl.addWidget(self.restart_btn)

        log_btn = QPushButton("▤  ABRIR LOG")
        log_btn.setObjectName("sheetSecondary")
        log_btn.clicked.connect(lambda: self._set_view(3))
        ctl.addWidget(log_btn)

        folder_btn = QPushButton("▣  ABRIR PASTA")
        folder_btn.setObjectName("sheetSecondary")
        folder_btn.clicked.connect(self._open_runtime_folder)
        ctl.addWidget(folder_btn)

        layout.addWidget(controls)

        self.dashboard_status = QLabel("Sistema pronto para iniciar.")
        self.dashboard_status.setObjectName("sheetBottomStatus")
        layout.addWidget(self.dashboard_status)

        return page

    def _build_whatsapp(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("sheetCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(10)

        head = QHBoxLayout()

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("WhatsApp Web")
        title.setObjectName("sheetSectionTitle")

        subtitle = QLabel(
            "Visualização da mesma sessão usada pela Automação de Planilhas. "
            "Se aparecer o QR Code aqui, leia com WhatsApp → Aparelhos conectados."
        )
        subtitle.setObjectName("sheetMuted")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        head.addLayout(title_box, 1)

        self.whatsapp_view_status = QLabel("Motor parado")
        self.whatsapp_view_status.setObjectName("sheetInfoStrip")
        head.addWidget(self.whatsapp_view_status)

        cl.addLayout(head)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.whatsapp_start_btn = QPushButton("▶  INICIAR WHATSAPP")
        self.whatsapp_start_btn.setObjectName("sheetPrimary")
        self.whatsapp_start_btn.clicked.connect(self._open_whatsapp_tab)
        controls.addWidget(self.whatsapp_start_btn)

        refresh = QPushButton("↻  ATUALIZAR TELA")
        refresh.setObjectName("sheetSecondary")
        refresh.clicked.connect(
            lambda: self._send_engine_command("SCREENSHOT")
        )
        controls.addWidget(refresh)

        reload_btn = QPushButton("⟳  RECARREGAR WHATSAPP")
        reload_btn.setObjectName("sheetSecondary")
        reload_btn.clicked.connect(
            lambda: self._send_engine_command("RELOAD_WHATSAPP")
        )
        controls.addWidget(reload_btn)

        show_browser = QPushButton("▣  ABRIR JANELA REAL")
        show_browser.setObjectName("sheetSecondary")
        show_browser.setToolTip(
            "Mostra a mesma janela do Chrome controlada pela automação. "
            "Não abre uma segunda sessão."
        )
        show_browser.clicked.connect(
            lambda: self._send_engine_command("SHOW_BROWSER")
        )
        controls.addWidget(show_browser)

        hide_browser = QPushButton("—  OCULTAR JANELA")
        hide_browser.setObjectName("sheetSecondary")
        hide_browser.clicked.connect(
            lambda: self._send_engine_command("HIDE_BROWSER")
        )
        controls.addWidget(hide_browser)

        controls.addStretch()
        cl.addLayout(controls)

        self.whatsapp_preview = QLabel(
            "Inicie a Automação de Planilhas.\n"
            "A tela real do WhatsApp Web aparecerá aqui."
        )
        self.whatsapp_preview.setObjectName("sheetWhatsappPreview")
        self.whatsapp_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.whatsapp_preview.setMinimumHeight(520)
        self.whatsapp_preview.setWordWrap(True)
        cl.addWidget(self.whatsapp_preview, 1)

        help_box = QLabel(
            "Esta visualização não cria outro login: ela é uma imagem atualizada "
            "da própria página do Chrome/Puppeteer usada pelo motor. "
            "Se precisar interagir diretamente, use “ABRIR JANELA REAL”."
        )
        help_box.setObjectName("sheetMuted")
        help_box.setWordWrap(True)
        cl.addWidget(help_box)

        layout.addWidget(card, 1)
        return page

    def _open_whatsapp_tab(self) -> None:
        if not self._is_running():
            self.start_engine()

        self._set_view(1)

        # Dá tempo para o Chromium ser criado antes do primeiro frame.
        QTimer.singleShot(
            1000,
            lambda: self._send_engine_command("SCREENSHOT"),
        )

    def _send_engine_command(self, command: str) -> None:
        if not self._is_running() or self.process is None:
            return

        try:
            self.process.write(
                (str(command).strip() + "\\n").encode("utf-8")
            )
        except Exception as exc:
            self._append_log(
                f"Falha ao enviar comando ao WhatsApp: {exc}",
                True,
            )

    def _show_whatsapp_frame(self, data_url: str) -> None:
        try:
            marker = "base64,"
            if marker not in data_url:
                raise ValueError("imagem inválida")

            raw = base64.b64decode(
                data_url.split(marker, 1)[1]
            )

            pixmap = QPixmap()
            if not pixmap.loadFromData(raw):
                raise ValueError("não foi possível carregar a imagem")

            self._whatsapp_last_pixmap = pixmap
            self._render_whatsapp_pixmap()

        except Exception as exc:
            self._append_log(
                f"Falha ao mostrar WhatsApp Web: {exc}",
                True,
            )

    def _render_whatsapp_pixmap(self) -> None:
        pixmap = getattr(
            self,
            "_whatsapp_last_pixmap",
            None,
        )

        if pixmap is None or pixmap.isNull():
            return

        size = self.whatsapp_preview.size()

        self.whatsapp_preview.setPixmap(
            pixmap.scaled(
                max(320, size.width() - 8),
                max(300, size.height() - 8),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        if hasattr(self, "whatsapp_preview"):
            self._render_whatsapp_pixmap()

    def _build_settings(self) -> QWidget:
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("sheetCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(18, 14, 18, 14)
        form.setSpacing(10)

        form.addWidget(self._section_title("Configurações da automação"))
        info = QLabel(
            "As configurações abaixo pertencem somente à automação de Planilhas. "
            "A rede é controlada exclusivamente pelo proxy geral do Central Inteligente de Mídia."
        )
        info.setObjectName("sheetMuted")
        info.setWordWrap(True)
        form.addWidget(info)

        form.addWidget(self._field_label("Apps Script URL"))
        self.apps_url = QLineEdit()
        self.apps_url.setPlaceholderText("https://script.google.com/macros/s/.../exec")
        form.addWidget(self.apps_url)

        row = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self._field_label("Aba da planilha"))
        auto_tab = QLineEdit("Automática pela data da matéria")
        auto_tab.setReadOnly(True)
        left.addWidget(auto_tab)
        row.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(self._field_label("Caminho do Chrome/Edge (opcional)"))
        self.chrome_path = QLineEdit()
        self.chrome_path.setPlaceholderText("Deixe vazio para detectar automaticamente")
        right.addWidget(self.chrome_path)
        row.addLayout(right, 1)
        form.addLayout(row)

        network_card = QFrame()
        network_card.setObjectName("sheetNetworkInfo")
        network_l = QHBoxLayout(network_card)
        network_l.setContentsMargins(12, 9, 12, 9)
        network_l.addWidget(QLabel("⌁"))
        self.settings_network = QLabel("Rede do motor: conexão direta")
        self.settings_network.setObjectName("sheetGreenText")
        network_l.addWidget(self.settings_network)
        network_l.addStretch()
        network_hint = QLabel("Altere em Configurações → Proxy do Central")
        network_hint.setObjectName("sheetMuted")
        network_l.addWidget(network_hint)
        form.addWidget(network_card)

        form.addWidget(self._field_label("IDs dos grupos — um por linha"))
        self.groups_edit = QPlainTextEdit()
        self.groups_edit.setPlaceholderText("120363...@g.us")
        self.groups_edit.setMinimumHeight(180)
        form.addWidget(self.groups_edit)

        self.diagnostic = QCheckBox("Ativar diagnóstico de grupos")
        form.addWidget(self.diagnostic)

        actions = QHBoxLayout()
        save = QPushButton("✓  SALVAR CONFIGURAÇÕES")
        save.setObjectName("sheetPrimary")
        save.clicked.connect(self._save_config_from_form)
        actions.addWidget(save)

        import_old = QPushButton("⇩  IMPORTAR CONFIG.JSON ANTIGO")
        import_old.setObjectName("sheetSecondary")
        import_old.clicked.connect(self._import_old_config)
        actions.addWidget(import_old)

        actions.addStretch()
        form.addLayout(actions)

        self.settings_status = QLabel("Configuração local pronta.")
        self.settings_status.setObjectName("sheetInfoStrip")
        form.addWidget(self.settings_status)

        layout.addWidget(card)
        layout.addStretch()
        return outer

    def _build_log(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        card = QFrame()
        card.setObjectName("sheetCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(self._section_title("Log do sistema"))
        head.addStretch()
        clear = QPushButton("LIMPAR TELA")
        clear.setObjectName("sheetSecondary")
        clear.clicked.connect(lambda: self.log_edit.clear())
        head.addWidget(clear)
        open_file = QPushButton("ABRIR ARQUIVO")
        open_file.setObjectName("sheetSecondary")
        open_file.clicked.connect(self._open_log_file)
        head.addWidget(open_file)
        cl.addLayout(head)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setObjectName("sheetLog")
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlainText("Pronto para iniciar.")
        cl.addWidget(self.log_edit, 1)

        layout.addWidget(card, 1)
        return page

    def _build_about(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("sheetCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(30, 28, 30, 28)
        cl.setSpacing(10)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("▦")
        icon.setObjectName("sheetAboutIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(92, 92)
        cl.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Automação de Planilhas")
        title.setObjectName("sheetAboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(title)

        text = QLabel(
            "Módulo integrado ao Central Inteligente de Mídia para monitorar grupos do WhatsApp, "
            "interpretar notícias e vídeos e enviar os dados para o Google Planilhas."
        )
        text.setObjectName("sheetMuted")
        text.setWordWrap(True)
        text.setMaximumWidth(760)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(text)

        version = QLabel("Motor integrado v1.2.0")
        version.setObjectName("sheetGreenText")
        cl.addWidget(version, 0, Qt.AlignmentFlag.AlignCenter)

        note = QLabel(
            "Proxy próprio removido. Conexão direta por padrão; quando o proxy geral do Central "
            "estiver ativado, o motor herda a mesma configuração somente em memória."
        )
        note.setObjectName("sheetMuted")
        note.setWordWrap(True)
        note.setMaximumWidth(760)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(note)

        layout.addWidget(card, 1)
        return page

    def _status_card(self, layout, title, value, subtitle, icon_text, tone):
        card = QFrame()
        card.setObjectName("sheetStatusCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(9)
        text = QVBoxLayout()
        cap = QLabel(title)
        cap.setObjectName("sheetStatusCaption")
        val = QLabel(value)
        val.setObjectName("sheetStatusValue")
        sub = QLabel(subtitle)
        sub.setObjectName("sheetMuted")
        sub.setWordWrap(True)
        text.addWidget(cap)
        text.addWidget(val)
        text.addWidget(sub)
        row.addLayout(text, 1)
        icon = QLabel(icon_text)
        icon.setObjectName("sheetStatusIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(48, 48)
        row.addWidget(icon)
        layout.addWidget(card, 1)
        return val

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sheetSectionTitle")
        return label

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sheetFieldLabel")
        return label

    @staticmethod
    def _metric_row(layout: QVBoxLayout, title: str, value: str, big: bool = False) -> QLabel:
        row = QFrame()
        row.setObjectName("sheetMetricRow")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(2, 7, 2, 7)
        cap = QLabel(title)
        cap.setObjectName("sheetMuted")
        val = QLabel(value)
        val.setObjectName("sheetMetricBig" if big else "sheetMetricValue")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rl.addWidget(cap, 1)
        rl.addWidget(val)
        layout.addWidget(row)
        return val

    @staticmethod
    def _news_field(layout: QVBoxLayout, title: str, value: str, strong: bool = False) -> QLabel:
        cap = QLabel(title)
        cap.setObjectName("sheetMuted")
        layout.addWidget(cap)
        val = QLabel(value)
        val.setObjectName("sheetNewsStrong" if strong else "sheetNewsValue")
        val.setWordWrap(True)
        layout.addWidget(val)
        return val

    @staticmethod
    def _small_field(layout: QHBoxLayout, title: str, value: str) -> QLabel:
        frame = QFrame()
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        cap = QLabel(title)
        cap.setObjectName("sheetMuted")
        val = QLabel(value)
        val.setObjectName("sheetNewsValue")
        fl.addWidget(cap)
        fl.addWidget(val)
        layout.addWidget(frame, 1)
        return val

    # ------------------------------------------------------------------
    # CONFIG FORM
    # ------------------------------------------------------------------

    def _load_config_into_form(self) -> None:
        cfg = self._read_config()
        self.apps_url.setText(cfg.get("appsScriptUrl", ""))
        self.chrome_path.setText(cfg.get("chromePath", ""))
        self.groups_edit.setPlainText("\n".join(cfg.get("grupos", [])))
        self.diagnostic.setChecked(bool(cfg.get("diagnosticoGrupos", False)))
        self._render_groups(cfg.get("grupos", []))

    def _save_config_from_form(self) -> None:
        cfg = {
            "appsScriptUrl": self.apps_url.text().strip(),
            "chromePath": self.chrome_path.text().strip(),
            "diagnosticoGrupos": self.diagnostic.isChecked(),
            "grupos": [
                line.strip()
                for line in self.groups_edit.toPlainText().splitlines()
                if line.strip()
            ],
        }
        self._write_config(cfg)
        self._render_groups(cfg["grupos"])

        if self._is_running():
            self.settings_status.setText(
                "Configurações salvas. Reinicie o motor para aplicar as alterações."
            )
        else:
            self.settings_status.setText("Configurações salvas com sucesso.")

        self._append_log("Configurações da Automação de Planilhas salvas.")

    def _import_old_config(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Importar config.json da Automação de Planilhas",
            str(self.app_root),
            "Configuração JSON (*.json);;Todos os arquivos (*.*)",
        )
        if not file_name:
            return

        try:
            cfg = json.loads(Path(file_name).read_text(encoding="utf-8"))
            if not isinstance(cfg, dict):
                raise ValueError("arquivo JSON inválido")
            cfg.pop("proxy", None)
            self._write_config(cfg)
            self._load_config_into_form()
            self.settings_status.setText(
                "Configuração importada. O proxy antigo foi descartado; a rede usa o Central."
            )
            self._append_log(f"Configuração importada de: {file_name}")
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Importação",
                f"Não foi possível importar a configuração:\n{exc}",
            )

    def _render_groups(self, groups: list[str]) -> None:
        while self.groups_box.count():
            item = self.groups_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, group_id in enumerate(groups, start=1):
            frame = QFrame()
            frame.setObjectName("sheetGroupItem")
            row = QHBoxLayout(frame)
            row.setContentsMargins(8, 7, 8, 7)
            row.setSpacing(8)
            badge = QLabel("♟")
            badge.setObjectName("sheetGroupBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(30, 30)
            row.addWidget(badge)
            text = QVBoxLayout()
            title = QLabel(f"Grupo {index}")
            title.setObjectName("sheetGroupTitle")
            gid = QLabel(group_id)
            gid.setObjectName("sheetMuted")
            gid.setWordWrap(True)
            text.addWidget(title)
            text.addWidget(gid)
            row.addLayout(text, 1)
            active = QLabel("ATIVO")
            active.setObjectName("sheetPill")
            row.addWidget(active)
            self.groups_box.addWidget(frame)

        self.group_total.setText(
            f"Total: {len(groups)} grupo{'s' if len(groups) != 1 else ''}"
        )

    # ------------------------------------------------------------------
    # PROCESSO NODE
    # ------------------------------------------------------------------

    def _resolve_node(self) -> str | None:
        if self.node_path.is_file():
            return str(self.node_path)
        return shutil.which("node")

    def _network_signature(self) -> tuple:
        cfg = self.controller.proxy_config
        return (
            bool(cfg.enabled),
            str(cfg.host or ""),
            int(cfg.port or 0),
            str(cfg.username or ""),
            str(cfg.password or ""),
        )

    def _network_label(self) -> str:
        cfg = self.controller.proxy_config
        if cfg.enabled:
            return "Proxy geral do Central"
        return "Conexão direta"

    def _build_process_environment(self) -> QProcessEnvironment:
        env = QProcessEnvironment.systemEnvironment()
        env.insert("CONFIG_PATH", str(self.config_path))
        env.insert("CENTRAL_STATE_DIR", str(self.state_dir))
        env.insert("CENTRAL_AUTH_DIR", str(self.auth_dir))

        cfg = self.controller.proxy_config
        if cfg.enabled:
            env.insert("CENTRAL_PROXY_ENABLED", "1")
            env.insert("CENTRAL_PROXY_HOST", str(cfg.host))
            env.insert("CENTRAL_PROXY_PORT", str(cfg.port))
            env.insert("CENTRAL_PROXY_USERNAME", str(cfg.username or ""))
            env.insert("CENTRAL_PROXY_PASSWORD", str(cfg.password or ""))
        else:
            env.insert("CENTRAL_PROXY_ENABLED", "0")
            env.insert("CENTRAL_PROXY_HOST", "")
            env.insert("CENTRAL_PROXY_PORT", "")
            env.insert("CENTRAL_PROXY_USERNAME", "")
            env.insert("CENTRAL_PROXY_PASSWORD", "")

        return env

    def _is_running(self) -> bool:
        return (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        )

    def start_engine(self) -> None:
        if self._is_running():
            self.dashboard_status.setText("O motor já está em execução.")
            return

        node = self._resolve_node()
        if not node:
            self.stats["motor"] = "ERRO"
            self.dashboard_status.setText(
                "node.exe não encontrado em tools/spreadsheet_automation."
            )
            self._append_log("ERRO: node.exe não encontrado.", True)
            self._update_status_ui()
            return

        if not self.engine_path.is_file():
            self.stats["motor"] = "ERRO"
            self.dashboard_status.setText(
                "Motor da Automação de Planilhas não encontrado."
            )
            self._append_log(f"ERRO: arquivo ausente: {self.engine_path}", True)
            self._update_status_ui()
            return

        self._save_config_from_form()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.auth_dir.mkdir(parents=True, exist_ok=True)

        self._manual_stop = False
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._network_signature_at_start = self._network_signature()

        process = QProcess(self)
        process.setProcessEnvironment(self._build_process_environment())
        process.setWorkingDirectory(str(self.tool_dir))
        process.setProgram(node)
        process.setArguments([str(self.engine_path)])
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)
        process.started.connect(self._process_started)
        self.process = process

        self.stats["motor"] = "INICIANDO"
        self.stats["whatsapp"] = "CONECTANDO"
        self.stats["planilha"] = "AGUARDANDO"
        self.stats["network"] = self._network_label().upper()
        self.dashboard_status.setText("Iniciando motor de Planilhas...")
        self._append_log("Iniciando Automação de Planilhas...")
        self._update_status_ui()
        process.start()

    def _process_started(self) -> None:
        # Se a aba WhatsApp estiver aberta, ativa o stream visual assim que o
        # processo Node estiver pronto para receber comandos.
        if self.views.currentIndex() == 1:
            self._send_engine_command("VIEW_ON")
            QTimer.singleShot(
                700,
                lambda: self._send_engine_command("SCREENSHOT"),
            )

    def stop_engine(self) -> None:
        self._manual_stop = True
        self._restart_attempts = 0

        if not self._is_running():
            self.stats["motor"] = "PARADO"
            self.stats["whatsapp"] = "DESCONECTADO"
            self.dashboard_status.setText("Motor já está parado.")
            self._update_status_ui()
            return

        assert self.process is not None
        self.dashboard_status.setText("Encerrando motor com segurança...")
        self._append_log("Solicitando encerramento do motor...")
        self.process.write(b"STOP\n")
        QTimer.singleShot(4000, self._force_stop_if_needed)

    def _force_stop_if_needed(self) -> None:
        if not self._is_running():
            return
        assert self.process is not None
        self._append_log("Motor não encerrou no prazo; finalizando processo.", True)
        self.process.kill()

    def restart_engine(self) -> None:
        if self._is_running():
            self._manual_stop = True
            assert self.process is not None
            self.process.write(b"STOP\n")
            QTimer.singleShot(1800, self._restart_after_stop)
        else:
            self.start_engine()

    def _restart_after_stop(self) -> None:
        if self._is_running():
            assert self.process is not None
            self.process.kill()
            QTimer.singleShot(500, self.start_engine)
        else:
            self.start_engine()

    def _read_stdout(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        self._stdout_buffer = self._consume_buffer(self._stdout_buffer + chunk, False)

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
        self._stderr_buffer = self._consume_buffer(self._stderr_buffer + chunk, True)

    def _consume_buffer(self, data: str, is_error: bool) -> str:
        pieces = data.split("\n")
        tail = pieces.pop() if pieces else ""
        for raw in pieces:
            line = raw.rstrip("\r")
            if line:
                self._handle_line(line, is_error)
        return tail

    def _handle_line(self, line: str, is_error: bool) -> None:
        if line.startswith(_EVENT_PREFIX):
            try:
                event = json.loads(line[len(_EVENT_PREFIX):])
                if isinstance(event, dict):
                    self._handle_event(event)
                    return
            except Exception:
                pass

        self._append_log(line, is_error)
        if is_error:
            self.stats["erros"] = int(self.stats["erros"]) + 1
            self._update_status_ui()

    def _handle_event(self, event: dict) -> None:
        kind = str(event.get("type", ""))

        if kind == "engine_start":
            self.stats["motor"] = "INICIANDO"
            self.dashboard_status.setText("Motor iniciado. Conectando ao WhatsApp...")

        elif kind == "network":
            mode = str(event.get("mode", "DIRECT"))
            self.stats["network"] = (
                "PROXY GERAL"
                if mode == "PROXY"
                else "CONEXÃO DIRETA"
            )

        elif kind == "browser":
            browser = str(event.get("path", ""))
            if browser:
                self._append_log(f"Navegador detectado: {browser}")

        elif kind == "browser_frame":
            self._show_whatsapp_frame(
                str(event.get("dataUrl", ""))
            )
            url = str(event.get("url", ""))
            title = str(event.get("title", ""))
            label = title or url or "WhatsApp Web"
            self.whatsapp_view_status.setText(label)

        elif kind == "browser_view_status":
            message = str(event.get("message", "WhatsApp Web"))
            self.whatsapp_view_status.setText(message)

        elif kind == "browser_window":
            message = str(event.get("message", "Janela do Chrome atualizada."))
            self.whatsapp_view_status.setText(message)

        elif kind == "qr":
            self.stats["motor"] = "AGUARDANDO QR"
            self.stats["whatsapp"] = "AGUARDANDO AUTENTICAÇÃO"
            self.qr_status.setText("QR Code pronto. Faça a leitura pelo WhatsApp.")
            self.whatsapp_view_status.setText("QR Code pronto para leitura")
            self._send_engine_command("SCREENSHOT")
            self._show_qr(str(event.get("dataUrl", "")))

        elif kind == "authenticated":
            self.stats["whatsapp"] = "AUTENTICADO"
            self.qr_status.setText("WhatsApp autenticado. Finalizando conexão...")
            self.whatsapp_view_status.setText("WhatsApp autenticado")

        elif kind == "loading":
            percent = event.get("percent", 0)
            self.stats["whatsapp"] = f"CARREGANDO {percent}%"

        elif kind == "ready":
            self.stats["motor"] = "RODANDO"
            self.stats["whatsapp"] = "CONECTADO"
            self._restart_attempts = 0
            self.qr_frame.hide()
            self.dashboard_status.setText("Automação ativa e monitorando os grupos.")
            self.whatsapp_view_status.setText("WhatsApp conectado")
            self._send_engine_command("SCREENSHOT")

        elif kind == "reconnecting":
            self.stats["whatsapp"] = "RECONECTANDO"
            self.dashboard_status.setText("WhatsApp desconectou; tentando reconectar...")

        elif kind == "disconnected":
            self.stats["whatsapp"] = "DESCONECTADO"

        elif kind == "auth_failure":
            self.stats["whatsapp"] = "ERRO"
            self.stats["erros"] = int(self.stats["erros"]) + 1
            self.dashboard_status.setText("Falha na autenticação do WhatsApp.")

        elif kind == "news_identified":
            data = event.get("data") or {}
            for key in self.last_news:
                if key in data:
                    self.last_news[key] = str(data.get(key) or "--")
            self._update_last_news_ui()

        elif kind == "sheet_success":
            self.stats["planilha"] = "OK"
            self.stats["processadas"] = int(self.stats["processadas"]) + 1
            if str(event.get("kind", "")) == "video":
                self.stats["videos"] = int(self.stats["videos"]) + 1
            self.stats["ultima_linha"] = str(event.get("line", "--") or "--")
            self.stats["ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        elif kind == "sheet_error":
            self.stats["planilha"] = "ERRO"
            self.stats["erros"] = int(self.stats["erros"]) + 1
            self.dashboard_status.setText(str(event.get("message", "Erro ao enviar para planilha.")))

        elif kind == "engine_error":
            self.stats["motor"] = "ERRO"
            self.stats["erros"] = int(self.stats["erros"]) + 1

        elif kind == "log":
            self._append_log(str(event.get("message", "")), bool(event.get("error", False)))

        self._update_status_ui()

    def _show_qr(self, data_url: str) -> None:
        try:
            marker = "base64,"
            if marker not in data_url:
                raise ValueError("QR inválido")
            raw = base64.b64decode(data_url.split(marker, 1)[1])
            pixmap = QPixmap()
            if not pixmap.loadFromData(raw):
                raise ValueError("não foi possível carregar o QR")
            self.qr_image.setPixmap(
                pixmap.scaled(
                    180,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.qr_frame.show()
        except Exception as exc:
            self.qr_image.setText("QR")
            self.qr_frame.show()
            self._append_log(f"Falha ao exibir QR Code: {exc}", True)

    def _process_error(self, error) -> None:
        self.stats["motor"] = "ERRO"
        self.stats["erros"] = int(self.stats["erros"]) + 1
        self.dashboard_status.setText(f"Falha no processo Node: {error}")
        self._append_log(f"Erro de QProcess: {error}", True)
        self._update_status_ui()

    def _process_finished(self, exit_code: int, _exit_status) -> None:
        if self._stdout_buffer.strip():
            self._handle_line(self._stdout_buffer.strip(), False)
        if self._stderr_buffer.strip():
            self._handle_line(self._stderr_buffer.strip(), True)
        self._stdout_buffer = ""
        self._stderr_buffer = ""

        was_manual = self._manual_stop
        self.process = None
        if hasattr(self, "whatsapp_view_status"):
            self.whatsapp_view_status.setText("Motor parado")
        self.stats["motor"] = "PARADO" if was_manual or exit_code == 0 else "ERRO"
        if self.stats["whatsapp"] != "ERRO":
            self.stats["whatsapp"] = "DESCONECTADO"
        self._update_status_ui()

        if was_manual:
            self.dashboard_status.setText("Motor parado.")
            return

        if exit_code != 0 and self._restart_attempts < 5:
            self._restart_attempts += 1
            self.stats["motor"] = "RECUPERANDO"
            self.dashboard_status.setText(
                f"Motor encerrou inesperadamente. Nova tentativa em 5s "
                f"({self._restart_attempts}/5)."
            )
            self._update_status_ui()
            QTimer.singleShot(5000, self.start_engine)
        elif exit_code != 0:
            self.dashboard_status.setText(
                "Motor encerrou com erro após 5 tentativas automáticas."
            )

    # ------------------------------------------------------------------
    # STATUS / LOG / REFRESH
    # ------------------------------------------------------------------

    def _append_log(self, message: str, is_error: bool = False) -> None:
        message = str(message or "").strip()
        if not message:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        visible = f"[{stamp}] {'ERRO: ' if is_error else ''}{message}"
        self.log_edit.appendPlainText(visible)
        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(visible + "\n")
        except Exception:
            pass

    def _update_status_ui(self) -> None:
        self.status_whatsapp.setText(str(self.stats["whatsapp"]))
        self.status_sheet.setText(str(self.stats["planilha"]))
        self.status_motor.setText(str(self.stats["motor"]))
        self.status_network.setText(str(self.stats["network"]))
        self.metric_processadas.setText(str(self.stats["processadas"]))
        self.metric_update.setText(str(self.stats["ultima_atualizacao"]))
        self.metric_videos.setText(str(self.stats["videos"]))
        self.metric_errors.setText(str(self.stats["erros"]))
        self.metric_line.setText(str(self.stats["ultima_linha"]))
        self.metric_network.setText(self._network_label())
        self.start_btn.setEnabled(not self._is_running())
        self.stop_btn.setEnabled(self._is_running())

    def _update_last_news_ui(self) -> None:
        self.last_title.setText(self.last_news["titulo"])
        self.last_vehicle.setText(self.last_news["veiculo"])
        self.last_date.setText(self.last_news["data"])
        self.last_subject.setText(self.last_news["assunto"])
        self.last_analysis.setText(self.last_news["analise"])
        self.last_author.setText(self.last_news["autor"])
        self.last_link.setText(self.last_news["link"] or "--")

    def _update_network_preview(self) -> None:
        label = self._network_label()
        self.network_chip.setText(f"Rede: {label.lower()}")
        self.settings_network.setText(f"Rede do motor: {label}")
        self.metric_network.setText(label)

    def refresh(self, _state: UiState) -> None:
        self._update_network_preview()

        if self._is_running() and self._network_signature_at_start is not None:
            current = self._network_signature()
            if current != self._network_signature_at_start:
                self.settings_status.setText(
                    "A configuração geral de rede mudou. Reinicie o motor de Planilhas para aplicar."
                )

    def _open_runtime_folder(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.runtime_dir)))

    def _open_log_file(self) -> None:
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_path)))

    def shutdown(self) -> bool:
        self._manual_stop = True
        if self.process is None:
            return True
        try:
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.write(b"STOP\n")
                if not self.process.waitForFinished(2500):
                    self.process.kill()
                    self.process.waitForFinished(1000)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass
        self.process = None
        return True

    # ------------------------------------------------------------------
    # STYLE
    # ------------------------------------------------------------------

    def _stylesheet(self) -> str:
        return """
        QFrame#sheetNav, QFrame#sheetCard, QFrame#sheetStatusCard, QFrame#sheetControls {
            background:#FFFFFF;
            border:1px solid #D5E5F5;
            border-radius:12px;
        }
        QPushButton#sheetTab {
            background:#F7FAFE;
            color:#214875;
            border:1px solid #D2E2F4;
            border-radius:8px;
            padding:8px 16px;
            font-weight:800;
        }
        QPushButton#sheetTab:checked {
            background:#087AF7;
            color:#FFFFFF;
            border-color:#087AF7;
        }
        QLabel#sheetNetworkChip {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:8px;
            padding:7px 11px;
            font-weight:800;
        }
        QLabel#sheetStatusCaption { color:#6079A5; font-size:10px; }
        QLabel#sheetStatusValue { color:#08245F; font-size:18px; font-weight:900; }
        QLabel#sheetMuted { color:#6A80A5; font-size:10px; }
        QLabel#sheetStatusIcon { border-radius:24px; font-size:20px; font-weight:900; }
        QLabel#sheetStatusIcon[tone='green'] { background:#DDF8EC; color:#078B5F; }
        QLabel#sheetStatusIcon[tone='blue'] { background:#E5F1FF; color:#087AF7; }
        QLabel#sheetStatusIcon[tone='purple'] { background:#F0E4FF; color:#8244F5; }
        QLabel#sheetStatusIcon[tone='orange'] { background:#FFF0CC; color:#EA9900; }
        QLabel#sheetSectionTitle { color:#08245F; font-size:16px; font-weight:900; }
        QFrame#sheetQrCard {
            background:#F5FAFF;
            border:1px solid #CFE3F7;
            border-radius:12px;
        }
        QLabel#sheetQrImage {
            background:#FFFFFF;
            border:1px solid #D1E1F1;
            border-radius:10px;
            color:#5B759B;
            font-size:22px;
            font-weight:900;
        }
        QLabel#sheetInfoStrip {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:8px;
            padding:8px 10px;
        }
        QFrame#sheetGroupItem {
            background:#F8FBFF;
            border:1px solid #DCE9F6;
            border-radius:8px;
        }
        QLabel#sheetGroupBadge {
            background:#DDF8EC;
            color:#078B5F;
            border-radius:8px;
        }
        QLabel#sheetGroupTitle { color:#08245F; font-weight:800; }
        QLabel#sheetPill {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:6px;
            padding:4px 7px;
            font-size:9px;
            font-weight:800;
        }
        QLabel#sheetGreenText { color:#078B5F; font-weight:800; }
        QFrame#sheetMetricRow { border:0; border-bottom:1px solid #E5EEF7; }
        QLabel#sheetMetricBig { color:#08A66B; font-size:24px; font-weight:900; }
        QLabel#sheetMetricValue { color:#08245F; font-size:11px; font-weight:800; }
        QLabel#sheetNewsStrong { color:#08245F; font-size:13px; font-weight:900; }
        QLabel#sheetNewsValue { color:#153E75; font-size:10px; font-weight:700; }
        QLabel#sheetFieldLabel { color:#244B7B; font-size:10px; font-weight:800; }
        QLineEdit, QPlainTextEdit {
            background:#FFFFFF;
            color:#0B2A63;
            border:1px solid #C8DDF2;
            border-radius:8px;
            padding:7px 9px;
        }
        QLineEdit:focus, QPlainTextEdit:focus { border-color:#087AF7; }
        QFrame#sheetNetworkInfo {
            background:#EAF9F2;
            border:1px solid #C4ECD9;
            border-radius:8px;
        }
        QPushButton#sheetPrimary {
            background:#0A7DF8;
            color:#FFFFFF;
            border:0;
            border-radius:8px;
            padding:9px 14px;
            font-weight:900;
        }
        QPushButton#sheetDanger {
            background:#FFF0F3;
            color:#D92F55;
            border:1px solid #FFB4C4;
            border-radius:8px;
            padding:9px 14px;
            font-weight:900;
        }
        QPushButton#sheetSecondary {
            background:#FFFFFF;
            color:#0C3974;
            border:1px solid #C9DDF2;
            border-radius:8px;
            padding:9px 13px;
            font-weight:800;
        }
        QPushButton:disabled { color:#9DABBC; background:#F1F4F8; }
        QLabel#sheetBottomStatus {
            color:#6079A5;
            padding:4px 6px;
        }
        QPlainTextEdit#sheetLog {
            background:#071522;
            color:#D7E8F4;
            border:1px solid #1C3B55;
            border-radius:9px;
            font-family:Consolas;
            font-size:10px;
        }
        QLabel#sheetAboutIcon {
            background:#EAF9F2;
            color:#078B5F;
            border-radius:22px;
            font-size:40px;
            font-weight:900;
        }
        QLabel#sheetWhatsappPreview {
            background:#0B141A;
            color:#C9D7DF;
            border:1px solid #24404F;
            border-radius:10px;
            padding:8px;
            font-size:13px;
            font-weight:700;
        }
        QLabel#sheetAboutTitle { color:#08245F; font-size:25px; font-weight:900; }
        """
