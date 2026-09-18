from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QVBoxLayout,
)

from monitor_noticias.ui.controller import MainUiController, UiState
from monitor_noticias.ui.pages import BasePage, ProxyTestThread


class SettingsPage(BasePage):
    """Configurações que não perdem alterações durante o refresh periódico."""

    def __init__(self, controller: MainUiController) -> None:
        super().__init__(controller)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(12)

        self._proxy_thread = None
        self._loaded = False
        self._dirty = False

        hero = QFrame()
        hero.setObjectName("settingsHero")

        hl = QHBoxLayout(hero)
        hl.setContentsMargins(18, 13, 18, 13)

        text = QVBoxLayout()

        title = QLabel("Central de configurações")
        title.setObjectName("settingsHeroTitle")

        subtitle = QLabel(
            "Ajuste rede, inicialização e horários automáticos. "
            "Alterações de automação só entram em vigor ao clicar em Aplicar automação."
        )
        subtitle.setObjectName("settingsMuted")
        subtitle.setWordWrap(True)

        text.addWidget(title)
        text.addWidget(subtitle)

        hl.addLayout(text, 1)

        self.saved = QLabel("✓  Proxy salvo")
        self.saved.setObjectName("settingsSaved")
        hl.addWidget(self.saved)

        self.root.addWidget(hero)

        top = QHBoxLayout()
        top.setSpacing(12)

        self.proxy_frame = QFrame()
        self.proxy_frame.setObjectName("settingsCard")

        pl = QVBoxLayout(self.proxy_frame)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(10)

        head = QHBoxLayout()

        icon = QLabel("▤")
        icon.setObjectName("settingsBlueIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        head.addWidget(icon)

        titles = QVBoxLayout()

        title = QLabel("Configuração de proxy")
        title.setObjectName("settingsTitle")

        self.proxy_hint = QLabel(
            "Informe servidor, usuário e senha para autenticação."
        )
        self.proxy_hint.setObjectName("settingsMuted")

        titles.addWidget(title)
        titles.addWidget(self.proxy_hint)

        head.addLayout(titles, 1)

        enabled = QLabel("Ativado")
        enabled.setObjectName("settingsStrong")
        head.addWidget(enabled)

        self.proxy_enabled = QCheckBox()
        head.addWidget(self.proxy_enabled)

        pl.addLayout(head)

        fields = QHBoxLayout()
        fields.setSpacing(8)

        self.host = self._field(
            fields,
            "Servidor",
            QLineEdit(),
        )

        self.port = self._field(
            fields,
            "Porta",
            QSpinBox(),
        )
        self.port.setRange(1, 65535)

        self.user = self._field(
            fields,
            "Usuário",
            QLineEdit(),
        )

        self.password = self._field(
            fields,
            "Senha",
            QLineEdit(),
        )
        self.password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        pl.addLayout(fields)

        buttons = QHBoxLayout()

        self.save_proxy = QPushButton("✓  Salvar e aplicar")
        self.save_proxy.setObjectName("settingsPrimary")

        self.test_proxy = QPushButton("↪  Testar conexão")
        self.test_proxy.setObjectName("settingsSecondary")

        buttons.addWidget(self.save_proxy)
        buttons.addWidget(self.test_proxy)
        buttons.addStretch()

        pl.addLayout(buttons)

        self.proxy_message = QLabel()
        self.proxy_message.setObjectName("settingsSuccess")
        self.proxy_message.setWordWrap(True)

        pl.addWidget(self.proxy_message)

        top.addWidget(self.proxy_frame, 3)

        automation = QFrame()
        automation.setObjectName("settingsCard")

        al = QVBoxLayout(automation)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(12)

        head = QHBoxLayout()

        icon = QLabel("⚙")
        icon.setObjectName("settingsBlueIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(54, 54)
        head.addWidget(icon)

        titles = QVBoxLayout()

        title = QLabel("Automação e inicialização")
        title.setObjectName("settingsTitle")

        subtitle = QLabel("Controles gerais do Monitor.")
        subtitle.setObjectName("settingsMuted")

        titles.addWidget(title)
        titles.addWidget(subtitle)

        head.addLayout(titles, 1)
        al.addLayout(head)

        self.general = QCheckBox()
        self.startup = QCheckBox()

        al.addWidget(
            self._toggle(
                "Buscas automáticas",
                "Liga ou pausa todas as rotinas automáticas.",
                self.general,
            )
        )

        al.addWidget(
            self._toggle(
                "Iniciar com o Windows",
                "Inicialização automática ao entrar no sistema.",
                self.startup,
            )
        )

        al.addStretch()
        top.addWidget(automation, 2)

        self.root.addLayout(top)

        services = QHBoxLayout()
        services.setSpacing(12)

        self.news_auto = QCheckBox()
        self.news_interval = QComboBox()
        self.news_interval.addItems(
            ["15", "30", "45", "60", "120"]
        )

        self.dem_auto = QCheckBox()
        self.dem_interval = QComboBox()
        self.dem_interval.addItems(
            ["15", "30", "45", "60", "120"]
        )

        self.video_auto = QCheckBox()

        services.addWidget(
            self._service(
                "▤",
                "Notícias",
                "Varredura das fontes selecionadas",
                self.news_auto,
                self.news_interval,
                "blue",
            ),
            1,
        )

        services.addWidget(
            self._service(
                "▣",
                "Demandas",
                "Pesquisa de todas as demandas ativas",
                self.dem_auto,
                self.dem_interval,
                "orange",
            ),
            1,
        )

        services.addWidget(
            self._service(
                "▶",
                "Vídeos",
                "Execução nos horários definidos abaixo",
                self.video_auto,
                None,
                "purple",
            ),
            1,
        )

        self.root.addLayout(services)

        schedule = QFrame()
        schedule.setObjectName("settingsCard")

        sl = QHBoxLayout(schedule)
        sl.setContentsMargins(16, 12, 16, 12)
        sl.setSpacing(12)

        text = QVBoxLayout()

        label = QLabel("Horários automáticos dos vídeos")
        label.setObjectName("settingsStrong")

        hint = QLabel(
            "Use HH:MM separados por vírgula. "
            "Ex: 08:00, 12:00, 15:00, 19:00, 21:00"
        )
        hint.setObjectName("settingsMuted")

        text.addWidget(label)
        text.addWidget(hint)

        sl.addLayout(text)

        self.video_times = QLineEdit()
        self.video_times.setPlaceholderText(
            "08:00, 12:00, 15:00, 19:00, 21:00"
        )
        sl.addWidget(self.video_times, 1)

        self.apply_auto = QPushButton("✓  Aplicar automação")
        self.apply_auto.setObjectName("settingsPrimary")
        sl.addWidget(self.apply_auto)

        self.root.addWidget(schedule)
        self.root.addStretch()

        self.save_proxy.clicked.connect(self._save_proxy)
        self.test_proxy.clicked.connect(self._test_proxy)
        self.apply_auto.clicked.connect(self._apply_auto)
        self.startup.toggled.connect(self._startup)

        # Qualquer edição impede que refresh() sobrescreva o formulário.
        for widget, signal_name in (
            (self.general, "toggled"),
            (self.news_auto, "toggled"),
            (self.dem_auto, "toggled"),
            (self.video_auto, "toggled"),
            (self.news_interval, "currentTextChanged"),
            (self.dem_interval, "currentTextChanged"),
            (self.video_times, "textEdited"),
        ):
            getattr(widget, signal_name).connect(self._mark_dirty)

        self.setStyleSheet(self._stylesheet())

    def _mark_dirty(self, *_args) -> None:
        if self._loaded:
            self._dirty = True

    def _stylesheet(self) -> str:
        return """
        QFrame#settingsHero, QFrame#settingsCard {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QLabel#settingsHeroTitle {
            color:#08245F;
            font-size:23px;
            font-weight:900;
        }
        QLabel#settingsMuted {
            color:#6079A5;
            font-size:10px;
        }
        QLabel#settingsSaved {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C2EBD8;
            border-radius:9px;
            padding:10px 14px;
            font-size:10px;
            font-weight:800;
        }
        QLabel#settingsBlueIcon {
            background:#E5F1FF;
            color:#087AF7;
            border-radius:11px;
            font-size:22px;
            font-weight:900;
        }
        QLabel#settingsTitle {
            color:#08245F;
            font-size:17px;
            font-weight:900;
        }
        QLabel#settingsStrong {
            color:#08245F;
            font-size:11px;
            font-weight:900;
        }
        QLabel#settingsFieldLabel {
            color:#244B7B;
            font-size:10px;
        }
        QPushButton#settingsPrimary {
            background:#0A7DF8;
            color:white;
            border:0;
            border-radius:8px;
            padding:9px 15px;
            font-weight:800;
        }
        QPushButton#settingsSecondary {
            background:white;
            color:#0C3974;
            border:1px solid #C9DDF2;
            border-radius:8px;
            padding:9px 15px;
            font-weight:800;
        }
        QLabel#settingsSuccess {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:7px;
            padding:8px 10px;
            font-size:10px;
        }
        QFrame#settingsToggleRow {
            border-bottom:1px solid #DFEAF6;
        }
        QFrame#settingsService {
            background:white;
            border:1px solid #D6E6F7;
            border-radius:12px;
        }
        QLabel#settingsServiceIcon {
            border-radius:10px;
            font-size:20px;
            font-weight:900;
        }
        QLabel#settingsServiceIcon[tone='blue'] {
            background:#E5F1FF;
            color:#087AF7;
        }
        QLabel#settingsServiceIcon[tone='orange'] {
            background:#FFF0CC;
            color:#EA9900;
        }
        QLabel#settingsServiceIcon[tone='purple'] {
            background:#F0E4FF;
            color:#8244F5;
        }
        """

    @staticmethod
    def _field(layout, label_text, widget):
        box = QVBoxLayout()

        label = QLabel(label_text)
        label.setObjectName("settingsFieldLabel")

        box.addWidget(label)
        box.addWidget(widget)

        layout.addLayout(box, 1)
        return widget

    @staticmethod
    def _toggle(title_text, subtitle_text, checkbox):
        frame = QFrame()
        frame.setObjectName("settingsToggleRow")

        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 8, 0, 12)

        text = QVBoxLayout()

        title = QLabel(title_text)
        title.setObjectName("settingsStrong")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("settingsMuted")

        text.addWidget(title)
        text.addWidget(subtitle)

        row.addLayout(text, 1)
        row.addWidget(checkbox)

        return frame

    def _service(
        self,
        icon_text,
        title_text,
        subtitle_text,
        checkbox,
        combo,
        tone,
    ):
        frame = QFrame()
        frame.setObjectName("settingsService")

        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 11, 14, 11)
        row.setSpacing(10)

        icon = QLabel(icon_text)
        icon.setObjectName("settingsServiceIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(48, 48)
        row.addWidget(icon)

        text = QVBoxLayout()

        title = QLabel(title_text)
        title.setObjectName("settingsTitle")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("settingsMuted")

        text.addWidget(title)
        text.addWidget(subtitle)

        row.addLayout(text, 1)

        checkbox.setText("Automático")
        row.addWidget(checkbox)

        if combo is not None:
            row.addWidget(QLabel("Intervalo"))
            row.addWidget(combo)

        return frame

    def _save_proxy(self):
        cfg = self.controller.save_proxy(
            self.proxy_enabled.isChecked(),
            self.host.text(),
            self.port.value(),
            self.user.text(),
            self.password.text(),
        )

        self.proxy_message.setText(
            "✓  Configuração salva e aplicada."
        )

        self.password.clear()
        self.host.setText(cfg.host)
        self.port.setValue(cfg.port)

    def _test_proxy(self):
        self.test_proxy.setEnabled(False)
        self.proxy_message.setText("Testando conexão...")

        self._proxy_thread = ProxyTestThread(self.controller)
        self._proxy_thread.completed.connect(
            self._proxy_done
        )
        self._proxy_thread.start()

    def _proxy_done(self, ok, text):
        self.proxy_message.setText(
            ("✓  " if ok else "⚠  ") + text
        )
        self.test_proxy.setEnabled(True)
        self._proxy_thread = None

    def _startup(self, checked):
        if not self._loaded:
            return

        ok = self.controller.set_start_with_windows(
            checked
        )

        if checked and not ok:
            self.startup.setToolTip(
                "Executável empacotado ainda não existe; "
                "preferência preservada para o portable final."
            )

    def _apply_auto(self):
        settings = self.controller.automation_settings

        settings.automatic_monitoring = self.general.isChecked()
        settings.news_automatic = self.news_auto.isChecked()
        settings.demand_automatic = self.dem_auto.isChecked()
        settings.video_automatic = self.video_auto.isChecked()

        settings.news_interval_minutes = int(
            self.news_interval.currentText()
        )
        settings.demand_interval_minutes = int(
            self.dem_interval.currentText()
        )

        settings.video_schedule_times = {
            value.strip()
            for value in self.video_times.text().split(",")
            if value.strip()
        }

        self._dirty = False
        self.proxy_message.setText(
            "✓  Automação salva e aplicada."
        )
        self.controller.refresh()

    @staticmethod
    def _set_checked(widget, value):
        blocker = QSignalBlocker(widget)
        widget.setChecked(bool(value))
        del blocker

    @staticmethod
    def _set_combo(widget, value):
        blocker = QSignalBlocker(widget)
        widget.setCurrentText(str(value))
        del blocker

    @staticmethod
    def _set_text(widget, value):
        blocker = QSignalBlocker(widget)
        widget.setText(str(value))
        del blocker

    def refresh(self, _state: UiState) -> None:
        # O MainWindow chama refresh a cada 500 ms.
        # Depois que o formulário foi carregado, não sobrescreve a edição
        # do usuário enquanto ele ainda não clicou em "Aplicar automação".
        cfg = self.controller.proxy_config

        self.saved.setText(
            "✓  Proxy salvo"
            if cfg.host
            else "Proxy não configurado"
        )

        if self._loaded and self._dirty:
            return

        settings = self.controller.automation_settings

        self._loaded = False

        self._set_checked(
            self.proxy_enabled,
            cfg.enabled,
        )
        self._set_text(
            self.host,
            cfg.host,
        )

        blocker = QSignalBlocker(self.port)
        self.port.setValue(cfg.port)
        del blocker

        self._set_text(
            self.user,
            cfg.username,
        )

        self.proxy_hint.setText(
            f"Servidor fixo {cfg.host}:{cfg.port}. "
            "Informe usuário e senha para autenticação."
            if cfg.host
            else "Informe os dados do servidor proxy."
        )

        self._set_checked(
            self.general,
            settings.automatic_monitoring,
        )
        self._set_checked(
            self.news_auto,
            settings.news_automatic,
        )
        self._set_checked(
            self.dem_auto,
            settings.demand_automatic,
        )
        self._set_checked(
            self.video_auto,
            settings.video_automatic,
        )

        self._set_combo(
            self.news_interval,
            settings.news_interval_minutes,
        )
        self._set_combo(
            self.dem_interval,
            settings.demand_interval_minutes,
        )

        self._set_text(
            self.video_times,
            ", ".join(
                sorted(settings.video_schedule_times)
            ),
        )

        self._set_checked(
            self.startup,
            self.controller.start_with_windows,
        )

        self._loaded = True
