from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from monitor_noticias.ui.settings_page import SettingsPage


class ReferenceSettingsPage(SettingsPage):
    """Versão visual final da aba Configurações.

    Mantém integralmente a lógica original de proxy, automação, persistência e
    refresh; altera somente composição e acabamento visual.
    """

    def __init__(self, controller) -> None:
        super().__init__(controller)

        self.root.setSpacing(14)

        self.proxy_frame.setMinimumHeight(300)

        for switch in (
            self.proxy_enabled,
            self.general,
            self.startup,
            self.news_auto,
            self.dem_auto,
            self.video_auto,
        ):
            switch.setObjectName("settingsSwitch")

        # Nos cards inferiores o texto fica no badge, como na imagem de referência.
        self.news_auto.setText("")
        self.dem_auto.setText("")
        self.video_auto.setText("")

        self.news_interval.setMinimumWidth(96)
        self.dem_interval.setMinimumWidth(96)

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
        row.setContentsMargins(16, 13, 16, 13)
        row.setSpacing(12)

        icon = QLabel(icon_text)
        icon.setObjectName("settingsServiceIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)
        row.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(4)

        title = QLabel(title_text)
        title.setObjectName("settingsTitle")

        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("settingsMuted")
        subtitle.setWordWrap(True)

        active = QLabel("Automático ativo")
        active.setObjectName("settingsActiveBadge")
        active.setMaximumWidth(125)

        text.addWidget(title)
        text.addWidget(subtitle)
        text.addWidget(active)
        row.addLayout(text, 1)

        right = QVBoxLayout()
        right.setSpacing(7)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        checkbox.setText("")
        checkbox.setObjectName("settingsSwitch")
        right.addWidget(
            checkbox,
            0,
            Qt.AlignmentFlag.AlignRight,
        )

        if combo is not None:
            interval = QHBoxLayout()
            interval.setSpacing(6)

            label = QLabel("Intervalo")
            label.setObjectName("settingsMuted")
            interval.addWidget(label)

            interval.addWidget(combo)

            unit = QLabel("min")
            unit.setObjectName("settingsMuted")
            interval.addWidget(unit)

            right.addLayout(interval)

        row.addLayout(right)

        return frame

    def _stylesheet(self) -> str:
        return """
        QFrame#settingsHero,
        QFrame#settingsCard,
        QFrame#settingsService {
            background:#FFFFFF;
            border:1px solid #D4E4F5;
            border-radius:13px;
        }

        QFrame#settingsHero {
            min-height:74px;
        }

        QLabel#settingsHeroTitle {
            color:#08245F;
            font-size:24px;
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
            border-radius:10px;
            padding:13px 18px;
            font-size:10px;
            font-weight:900;
        }

        QLabel#settingsBlueIcon {
            background:#E5F1FF;
            color:#087AF7;
            border-radius:12px;
            font-size:23px;
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

        QLabel#settingsActiveBadge {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:8px;
            padding:6px 10px;
            font-size:10px;
            font-weight:900;
        }

        QLineEdit,
        QSpinBox,
        QComboBox {
            min-height:34px;
            background:#FFFFFF;
            color:#0B2A63;
            border:1px solid #C8DDF2;
            border-radius:8px;
            padding:5px 9px;
        }

        QLineEdit:focus,
        QSpinBox:focus,
        QComboBox:focus {
            border:1px solid #087AF7;
        }

        QPushButton#settingsPrimary {
            background:#0A7DF8;
            color:#FFFFFF;
            border:0;
            border-radius:9px;
            padding:11px 17px;
            font-weight:900;
        }

        QPushButton#settingsPrimary:hover {
            background:#066DDF;
        }

        QPushButton#settingsSecondary {
            background:#FFFFFF;
            color:#0C3974;
            border:1px solid #C9DDF2;
            border-radius:9px;
            padding:11px 17px;
            font-weight:900;
        }

        QLabel#settingsSuccess {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #C4ECD9;
            border-radius:8px;
            padding:10px 12px;
            font-size:10px;
        }

        QFrame#settingsToggleRow {
            border:0;
            border-bottom:1px solid #DFEAF6;
        }

        QFrame#settingsService {
            min-height:112px;
        }

        QLabel#settingsServiceIcon {
            border-radius:11px;
            font-size:21px;
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

        QCheckBox#settingsSwitch {
            spacing:0;
            min-width:50px;
            max-width:50px;
            min-height:28px;
            max-height:28px;
        }

        QCheckBox#settingsSwitch::indicator {
            width:46px;
            height:24px;
            border-radius:12px;
            border:1px solid #BFCFE1;
            background:#CBD7E7;
        }

        QCheckBox#settingsSwitch::indicator:checked {
            border:1px solid #087AF7;
            background:#087AF7;
        }

        QCheckBox#settingsSwitch::indicator:hover {
            border-color:#087AF7;
        }
        """
