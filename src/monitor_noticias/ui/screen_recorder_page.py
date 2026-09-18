from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QScreen,
    QUrl,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


CREATE_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0


class RegionSelectionOverlay(QWidget):
    selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, screen: QScreen) -> None:
        super().__init__(None)
        self.screen = screen
        self._origin: QPoint | None = None
        self._current: QPoint | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen.geometry())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = event.position().toPoint()
        self._current = self._origin
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is None:
            return
        self._current = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() != Qt.MouseButton.LeftButton
            or self._origin is None
        ):
            return

        self._current = event.position().toPoint()
        local = QRect(
            self._origin,
            self._current,
        ).normalized()

        if local.width() < 40 or local.height() < 40:
            self._origin = None
            self._current = None
            self.update()
            return

        top_left = self.geometry().topLeft() + local.topLeft()
        global_rect = QRect(
            top_left,
            local.size(),
        )

        self.selected.emit(global_rect)
        self.close()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(
            self.rect(),
            QColor(5, 18, 39, 160),
        )

        if self._origin is None or self._current is None:
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "ARRASTE PARA SELECIONAR A ÁREA\nESC para cancelar",
            )
            return

        rect = QRect(
            self._origin,
            self._current,
        ).normalized()

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        painter.fillRect(rect, Qt.GlobalColor.transparent)

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )
        painter.setPen(
            QPen(
                QColor("#19A0FF"),
                3,
            )
        )
        painter.drawRect(rect)

        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            rect.adjusted(10, 10, -10, -10),
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft,
            f"{rect.width()} × {rect.height()}",
        )


class ScreenRecorderPage(QWidget):
    state_changed = Signal(str)
    recording_finished = Signal(str)

    IDLE = "idle"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    FINALIZING = "finalizing"
    ERROR = "error"

    def __init__(
        self,
        app_root: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.app_root = Path(app_root)
        self.ffmpeg = self.app_root / "bin" / "ffmpeg.exe"
        self.recordings_dir = (
            self.app_root
            / "Videos"
            / "GravacoesTela"
        )
        self.temp_root = (
            self.app_root
            / "temp"
            / "screen_recorder"
        )
        self.logs_dir = self.app_root / "logs"

        for directory in (
            self.recordings_dir,
            self.temp_root,
            self.logs_dir,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        self._state = self.IDLE
        self._process: subprocess.Popen | None = None
        self._log_handle = None
        self._session_dir: Path | None = None
        self._segments: list[Path] = []
        self._final_path: Path | None = None
        self._segment_started_at: float | None = None
        self._elapsed_before_segment = 0.0
        self._region: QRect | None = None
        self._overlay: RegionSelectionOverlay | None = None
        self._hidden_by_recorder = False
        self._audio_loaded = False
        self._closing = False

        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(700)
        self._preview_timer.timeout.connect(
            self._update_preview
        )

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(250)
        self._status_timer.timeout.connect(
            self._update_runtime
        )
        self._status_timer.start()

        self._build_ui()
        self._refresh_screens()
        self._refresh_recordings()
        self._apply_state(self.IDLE)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("screenRecorderScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        body = QWidget()
        body.setObjectName("screenRecorderBody")
        body.setMinimumWidth(980)

        root = QVBoxLayout(body)
        root.setContentsMargins(0, 0, 4, 12)
        root.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("recHero")
        hero_l = QHBoxLayout(hero)
        hero_l.setContentsMargins(18, 14, 18, 14)
        hero_l.setSpacing(16)

        hero_icon = QLabel("●")
        hero_icon.setObjectName("recHeroIcon")
        hero_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_icon.setFixedSize(58, 58)
        hero_l.addWidget(hero_icon)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(2)

        title = QLabel("Gravador de Tela")
        title.setObjectName("recHeroTitle")

        subtitle = QLabel(
            "Grave a tela do Windows diretamente dentro da Central Inteligente de Mídia."
        )
        subtitle.setObjectName("recHeroSubtitle")

        hero_text.addWidget(title)
        hero_text.addWidget(subtitle)
        hero_l.addLayout(hero_text, 1)

        self.state_chip = QLabel("PRONTO")
        self.state_chip.setObjectName("recStateChip")
        self.state_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_chip.setMinimumWidth(126)
        hero_l.addWidget(self.state_chip)

        root.addWidget(hero)

        stats = QHBoxLayout()
        stats.setSpacing(10)

        self.duration_value = self._stat_card(
            stats,
            "Duração",
            "00:00:00",
            "◷",
        )
        self.source_value = self._stat_card(
            stats,
            "Origem",
            "Tela inteira",
            "▣",
        )
        self.audio_value = self._stat_card(
            stats,
            "Áudio",
            "Sem áudio",
            "♫",
        )
        self.format_value = self._stat_card(
            stats,
            "Formato",
            "MP4 • H.264",
            "MP4",
        )

        root.addLayout(stats)

        center = QHBoxLayout()
        center.setSpacing(12)

        preview_card = QFrame()
        preview_card.setObjectName("recCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(10)

        ph = QHBoxLayout()

        preview_title = QLabel("Pré-visualização")
        preview_title.setObjectName("recSectionTitle")
        ph.addWidget(preview_title)

        ph.addStretch()

        self.region_badge = QLabel("Tela inteira")
        self.region_badge.setObjectName("recSmallBadge")
        ph.addWidget(self.region_badge)

        preview_layout.addLayout(ph)

        self.preview = QLabel("Preparando pré-visualização…")
        self.preview.setObjectName("recPreview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(390)
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        preview_layout.addWidget(self.preview, 1)

        hint = QLabel(
            "A prévia é apenas uma referência visual. "
            "A gravação usa o FFmpeg incluído no portable."
        )
        hint.setObjectName("recMuted")
        preview_layout.addWidget(hint)

        center.addWidget(preview_card, 2)

        config_card = QFrame()
        config_card.setObjectName("recCard")
        config_l = QVBoxLayout(config_card)
        config_l.setContentsMargins(16, 14, 16, 14)
        config_l.setSpacing(10)

        cfg_title = QLabel("Configuração da gravação")
        cfg_title.setObjectName("recSectionTitle")
        config_l.addWidget(cfg_title)

        self.screen_combo = QComboBox()
        self.screen_combo.setObjectName("recCombo")
        self.screen_combo.currentIndexChanged.connect(
            self._screen_changed
        )
        config_l.addWidget(
            self._field(
                "Monitor",
                self.screen_combo,
            )
        )

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("recCombo")
        self.mode_combo.addItems(
            [
                "Tela inteira",
                "Área personalizada",
            ]
        )
        self.mode_combo.currentTextChanged.connect(
            self._mode_changed
        )

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(self.mode_combo, 1)

        self.select_region = QPushButton(
            "Selecionar área"
        )
        self.select_region.setObjectName(
            "recSecondary"
        )
        self.select_region.clicked.connect(
            self._choose_region
        )
        mode_row.addWidget(self.select_region)

        mode_wrap = QWidget()
        mode_wrap.setLayout(mode_row)
        config_l.addWidget(
            self._field(
                "Área de captura",
                mode_wrap,
            )
        )

        self.fps_combo = QComboBox()
        self.fps_combo.setObjectName("recCombo")
        self.fps_combo.addItems(
            [
                "30 FPS",
                "60 FPS",
            ]
        )
        config_l.addWidget(
            self._field(
                "Taxa de quadros",
                self.fps_combo,
            )
        )

        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("recCombo")
        self.quality_combo.addItems(
            [
                "Alta qualidade • CRF 18",
                "Equilibrada • CRF 20",
                "Arquivo menor • CRF 23",
            ]
        )
        self.quality_combo.setCurrentIndex(1)
        config_l.addWidget(
            self._field(
                "Qualidade",
                self.quality_combo,
            )
        )

        audio_row = QHBoxLayout()
        audio_row.setSpacing(8)

        self.audio_combo = QComboBox()
        self.audio_combo.setObjectName("recCombo")
        self.audio_combo.addItem("Sem áudio")
        audio_row.addWidget(self.audio_combo, 1)

        self.refresh_audio = QPushButton("↻")
        self.refresh_audio.setObjectName("recSquare")
        self.refresh_audio.setToolTip(
            "Atualizar dispositivos de áudio"
        )
        self.refresh_audio.clicked.connect(
            self._load_audio_devices
        )
        audio_row.addWidget(self.refresh_audio)

        audio_wrap = QWidget()
        audio_wrap.setLayout(audio_row)
        config_l.addWidget(
            self._field(
                "Áudio",
                audio_wrap,
            )
        )

        self.countdown_combo = QComboBox()
        self.countdown_combo.setObjectName("recCombo")
        self.countdown_combo.addItems(
            [
                "Sem contagem",
                "3 segundos",
                "5 segundos",
            ]
        )
        self.countdown_combo.setCurrentIndex(1)
        config_l.addWidget(
            self._field(
                "Contagem regressiva",
                self.countdown_combo,
            )
        )

        self.draw_mouse = QCheckBox(
            "Mostrar ponteiro do mouse na gravação"
        )
        self.draw_mouse.setChecked(True)
        config_l.addWidget(self.draw_mouse)

        self.hide_central = QCheckBox(
            "Ocultar a Central depois de iniciar"
        )
        self.hide_central.setChecked(False)
        config_l.addWidget(self.hide_central)

        network_note = QLabel(
            "Este módulo é local e não utiliza o proxy da Central."
        )
        network_note.setObjectName("recNote")
        network_note.setWordWrap(True)
        config_l.addWidget(network_note)

        config_l.addStretch()

        center.addWidget(config_card, 1)
        root.addLayout(center)

        output_card = QFrame()
        output_card.setObjectName("recCard")
        output_l = QVBoxLayout(output_card)
        output_l.setContentsMargins(16, 14, 16, 14)
        output_l.setSpacing(10)

        output_title = QLabel("Destino")
        output_title.setObjectName("recSectionTitle")
        output_l.addWidget(output_title)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self.output_path = QLineEdit(
            str(self.recordings_dir)
        )
        self.output_path.setObjectName("recPath")
        self.output_path.setReadOnly(True)
        folder_row.addWidget(self.output_path, 1)

        choose_folder = QPushButton("Escolher pasta")
        choose_folder.setObjectName("recSecondary")
        choose_folder.clicked.connect(
            self._choose_output_folder
        )
        folder_row.addWidget(choose_folder)

        open_folder = QPushButton("Abrir pasta")
        open_folder.setObjectName("recSecondary")
        open_folder.clicked.connect(
            self._open_folder
        )
        folder_row.addWidget(open_folder)

        output_l.addLayout(folder_row)
        root.addWidget(output_card)

        controls = QFrame()
        controls.setObjectName("recControls")
        controls_l = QHBoxLayout(controls)
        controls_l.setContentsMargins(16, 13, 16, 13)
        controls_l.setSpacing(10)

        self.status_text = QLabel("Pronto para gravar.")
        self.status_text.setObjectName("recStatus")
        controls_l.addWidget(self.status_text, 1)

        self.pause_button = QPushButton("Ⅱ  Pausar")
        self.pause_button.setObjectName("recPause")
        self.pause_button.clicked.connect(
            self.toggle_pause
        )
        controls_l.addWidget(self.pause_button)

        self.stop_button = QPushButton("■  Parar")
        self.stop_button.setObjectName("recStop")
        self.stop_button.clicked.connect(
            self.stop_recording
        )
        controls_l.addWidget(self.stop_button)

        self.start_button = QPushButton("●  INICIAR GRAVAÇÃO")
        self.start_button.setObjectName("recStart")
        self.start_button.clicked.connect(
            self.start_recording
        )
        controls_l.addWidget(self.start_button)

        root.addWidget(controls)

        history = QFrame()
        history.setObjectName("recCard")
        history_l = QVBoxLayout(history)
        history_l.setContentsMargins(16, 14, 16, 14)
        history_l.setSpacing(9)

        hh = QHBoxLayout()

        hist_title = QLabel("Gravações recentes")
        hist_title.setObjectName("recSectionTitle")
        hh.addWidget(hist_title)

        hh.addStretch()

        refresh_hist = QPushButton("↻ Atualizar")
        refresh_hist.setObjectName("recSecondary")
        refresh_hist.clicked.connect(
            self._refresh_recordings
        )
        hh.addWidget(refresh_hist)

        history_l.addLayout(hh)

        self.history_list = QListWidget()
        self.history_list.setObjectName("recHistory")
        self.history_list.setMinimumHeight(140)
        self.history_list.itemDoubleClicked.connect(
            self._open_history_item
        )
        history_l.addWidget(self.history_list)

        recent_actions = QHBoxLayout()
        recent_actions.addStretch()

        self.open_last = QPushButton(
            "▶  Abrir última gravação"
        )
        self.open_last.setObjectName("recSecondary")
        self.open_last.clicked.connect(
            self._open_last_recording
        )
        recent_actions.addWidget(self.open_last)

        history_l.addLayout(recent_actions)
        root.addWidget(history)

        self.scroll.setWidget(body)
        outer.addWidget(self.scroll)

        self.setStyleSheet(
            self._stylesheet()
        )

    def _stat_card(
        self,
        row: QHBoxLayout,
        title: str,
        value: str,
        icon: str,
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("recStatCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setObjectName("recStatIcon")
        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        icon_label.setFixedSize(40, 40)
        layout.addWidget(icon_label)

        text = QVBoxLayout()
        text.setSpacing(0)

        caption = QLabel(title)
        caption.setObjectName("recStatCaption")

        value_label = QLabel(value)
        value_label.setObjectName("recStatValue")

        text.addWidget(caption)
        text.addWidget(value_label)
        layout.addLayout(text, 1)

        row.addWidget(card, 1)
        return value_label

    @staticmethod
    def _field(
        label: str,
        widget: QWidget,
    ) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        caption = QLabel(label)
        caption.setObjectName("recFieldLabel")

        layout.addWidget(caption)
        layout.addWidget(widget)

        return wrap

    def _stylesheet(self) -> str:
        return """
        QScrollArea#screenRecorderScroll {
            background:transparent;
            border:0;
        }

        QWidget#screenRecorderBody {
            background:transparent;
        }

        QFrame#recHero,
        QFrame#recCard,
        QFrame#recControls,
        QFrame#recStatCard {
            background:#FFFFFF;
            border:1px solid #D7E6F5;
            border-radius:12px;
        }

        QLabel#recHeroIcon {
            background:#FFE8ED;
            color:#F03F61;
            border-radius:16px;
            font-size:30px;
            font-weight:900;
        }

        QLabel#recHeroTitle {
            color:#08245F;
            font-size:23px;
            font-weight:900;
        }

        QLabel#recHeroSubtitle,
        QLabel#recMuted {
            color:#6079A5;
            font-size:10px;
        }

        QLabel#recStateChip {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #BFE8D5;
            border-radius:9px;
            padding:8px 14px;
            font-size:10px;
            font-weight:900;
        }

        QLabel#recStatIcon {
            background:#EDF6FF;
            color:#087AF7;
            border-radius:11px;
            font-weight:900;
        }

        QLabel#recStatCaption {
            color:#7286A8;
            font-size:9px;
        }

        QLabel#recStatValue {
            color:#08245F;
            font-size:13px;
            font-weight:900;
        }

        QLabel#recSectionTitle {
            color:#08245F;
            font-size:16px;
            font-weight:900;
        }

        QLabel#recSmallBadge {
            background:#EDF6FF;
            color:#087AF7;
            border:1px solid #D4E7FA;
            border-radius:7px;
            padding:5px 9px;
            font-size:9px;
            font-weight:800;
        }

        QLabel#recPreview {
            background:#071426;
            color:#8EA9C8;
            border:1px solid #17365D;
            border-radius:10px;
            min-height:390px;
        }

        QLabel#recFieldLabel {
            color:#244B7B;
            font-size:10px;
            font-weight:800;
        }

        QComboBox#recCombo,
        QLineEdit#recPath {
            background:#FFFFFF;
            color:#08245F;
            border:1px solid #C9DCF2;
            border-radius:8px;
            min-height:35px;
            padding:0 10px;
        }

        QPushButton#recSecondary,
        QPushButton#recSquare {
            background:#FFFFFF;
            color:#123B73;
            border:1px solid #C8DCF2;
            border-radius:8px;
            padding:8px 12px;
            font-weight:700;
        }

        QPushButton#recSquare {
            min-width:38px;
            max-width:38px;
        }

        QLabel#recNote {
            background:#F5FAFF;
            color:#55739C;
            border:1px solid #DCEAF7;
            border-radius:8px;
            padding:8px 10px;
            font-size:9px;
        }

        QLabel#recStatus {
            color:#244B7B;
            font-size:11px;
            font-weight:700;
        }

        QPushButton#recStart {
            background:#F23C5B;
            color:#FFFFFF;
            border:0;
            border-radius:9px;
            padding:11px 18px;
            font-size:11px;
            font-weight:900;
        }

        QPushButton#recStart:hover {
            background:#D92D4B;
        }

        QPushButton#recPause {
            background:#FFF7DF;
            color:#A36C00;
            border:1px solid #F4D686;
            border-radius:9px;
            padding:10px 15px;
            font-weight:800;
        }

        QPushButton#recStop {
            background:#FFF0F3;
            color:#D62F50;
            border:1px solid #F4B5C2;
            border-radius:9px;
            padding:10px 15px;
            font-weight:800;
        }

        QPushButton:disabled {
            background:#F1F4F8;
            color:#A8B4C4;
            border-color:#E1E7EF;
        }

        QListWidget#recHistory {
            background:#F8FBFF;
            color:#163C72;
            border:1px solid #DBE8F5;
            border-radius:8px;
            outline:0;
        }

        QListWidget#recHistory::item {
            padding:8px 10px;
            border-bottom:1px solid #E8F0F7;
        }

        QListWidget#recHistory::item:selected {
            background:#DDEEFF;
            color:#075ECA;
        }

        QScrollBar:vertical {
            background:#EDF4FB;
            width:10px;
            border-radius:5px;
        }

        QScrollBar::handle:vertical {
            background:#83B5E7;
            min-height:45px;
            border-radius:5px;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height:0;
        }
        """

    # ------------------------------------------------------------------
    # ACTIVATION / PREVIEW
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state in {
            self.STARTING,
            self.RECORDING,
            self.PAUSED,
            self.FINALIZING,
        }

    def on_activated(self) -> None:
        self._refresh_screens()

        if not self._audio_loaded:
            self._load_audio_devices()

        if not self._preview_timer.isActive():
            self._preview_timer.start()

        self._update_preview()
        self._refresh_recordings()

    def showEvent(self, event) -> None:
        super().showEvent(event)

        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._preview_timer.stop()

    def refresh(self, _state=None) -> None:
        # Compatível com o restante das páginas do Central.
        pass

    def _refresh_screens(self) -> None:
        current_name = self.screen_combo.currentData()

        self.screen_combo.blockSignals(True)
        self.screen_combo.clear()

        screens = QApplication.screens()

        for index, screen in enumerate(screens, start=1):
            geometry = screen.geometry()
            name = screen.name() or f"Monitor {index}"
            label = (
                f"{index} — {name} • "
                f"{geometry.width()}×{geometry.height()}"
            )
            self.screen_combo.addItem(
                label,
                name,
            )

        if current_name:
            idx = self.screen_combo.findData(
                current_name
            )
            if idx >= 0:
                self.screen_combo.setCurrentIndex(idx)

        self.screen_combo.blockSignals(False)

    def _selected_screen(self) -> QScreen:
        screens = QApplication.screens()

        if not screens:
            return QApplication.primaryScreen()

        index = self.screen_combo.currentIndex()
        index = min(max(index, 0), len(screens) - 1)
        return screens[index]

    def _screen_changed(self, _index: int) -> None:
        self._region = None
        self._update_capture_labels()
        self._update_preview()

    def _mode_changed(self, text: str) -> None:
        if text == "Tela inteira":
            self._region = None

        self._update_capture_labels()
        self._update_preview()

    def _update_capture_labels(self) -> None:
        if (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is not None
        ):
            text = (
                f"{self._region.width()}×"
                f"{self._region.height()}"
            )
            self.region_badge.setText(text)
            self.source_value.setText("Área personalizada")
        else:
            self.region_badge.setText("Tela inteira")
            self.source_value.setText("Tela inteira")

    def _update_preview(self) -> None:
        if not self.isVisible():
            return

        screen = self._selected_screen()

        if screen is None:
            self.preview.setText(
                "Nenhum monitor disponível."
            )
            return

        pixmap = screen.grabWindow(0)

        if pixmap.isNull():
            self.preview.setText(
                "Não foi possível gerar a prévia."
            )
            return

        if (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is not None
        ):
            screen_geo = screen.geometry()
            local = QRect(
                self._region.x() - screen_geo.x(),
                self._region.y() - screen_geo.y(),
                self._region.width(),
                self._region.height(),
            )
            pixmap = pixmap.copy(local)

        size = self.preview.size()

        if size.width() <= 1 or size.height() <= 1:
            return

        scaled = pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)

    # ------------------------------------------------------------------
    # REGION
    # ------------------------------------------------------------------

    def _choose_region(self) -> None:
        if self.is_active:
            return

        screen = self._selected_screen()

        if screen is None:
            return

        self.mode_combo.setCurrentText(
            "Área personalizada"
        )

        self._overlay = RegionSelectionOverlay(
            screen
        )
        self._overlay.selected.connect(
            self._region_selected
        )
        self._overlay.cancelled.connect(
            self._region_cancelled
        )
        self._overlay.show()

    def _region_selected(self, rect: QRect) -> None:
        self._region = rect.normalized()
        self._overlay = None
        self._update_capture_labels()
        self._update_preview()

    def _region_cancelled(self) -> None:
        self._overlay = None

    # ------------------------------------------------------------------
    # AUDIO
    # ------------------------------------------------------------------

    def _load_audio_devices(self) -> None:
        self.audio_combo.clear()
        self.audio_combo.addItem("Sem áudio")
        self._audio_loaded = True

        if not self.ffmpeg.is_file():
            return

        try:
            result = subprocess.run(
                [
                    str(self.ffmpeg),
                    "-hide_banner",
                    "-list_devices",
                    "true",
                    "-f",
                    "dshow",
                    "-i",
                    "dummy",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=12,
                creationflags=CREATE_NO_WINDOW,
            )
            text = (
                result.stdout
                + "\n"
                + result.stderr
            )
        except Exception:
            return

        devices: list[str] = []

        for line in text.splitlines():
            match = re.search(
                r'"([^"]+)"\s+\(audio\)',
                line,
                flags=re.IGNORECASE,
            )
            if match:
                name = match.group(1).strip()
                if name and name not in devices:
                    devices.append(name)

        for name in devices:
            label = name

            if "stereo mix" in name.casefold():
                label += "  •  áudio do sistema"

            self.audio_combo.addItem(
                label,
                name,
            )

    # ------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------

    def _choose_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta das gravações",
            str(self.recordings_dir),
        )

        if not folder:
            return

        self.recordings_dir = Path(folder)
        self.recordings_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.output_path.setText(
            str(self.recordings_dir)
        )
        self._refresh_recordings()

    def _open_folder(self) -> None:
        self.recordings_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(self.recordings_dir)
            )
        )

    def _refresh_recordings(self) -> None:
        self.history_list.clear()

        try:
            files = sorted(
                self.recordings_dir.glob("*.mp4"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            files = []

        for path in files[:20]:
            try:
                stat = path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                stamp = datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%d/%m/%Y %H:%M")
                text = (
                    f"{path.name}    •    "
                    f"{stamp}    •    "
                    f"{size_mb:.1f} MB"
                )
            except Exception:
                text = path.name

            self.history_list.addItem(text)
            item = self.history_list.item(
                self.history_list.count() - 1
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                str(path),
            )

        self.open_last.setEnabled(
            self.history_list.count() > 0
        )

    def _open_history_item(self, item) -> None:
        path = item.data(
            Qt.ItemDataRole.UserRole
        )

        if path:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(path)
            )

    def _open_last_recording(self) -> None:
        if self.history_list.count() <= 0:
            return
        self._open_history_item(
            self.history_list.item(0)
        )

    # ------------------------------------------------------------------
    # RECORDING
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        if self._state not in {
            self.IDLE,
            self.ERROR,
        }:
            return

        if not self.ffmpeg.is_file():
            QMessageBox.critical(
                self,
                "FFmpeg não encontrado",
                "O arquivo bin/ffmpeg.exe não foi encontrado no portable.",
            )
            return

        if (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is None
        ):
            QMessageBox.information(
                self,
                "Selecione uma área",
                "Clique em “Selecionar área” antes de iniciar a gravação.",
            )
            return

        self._apply_state(
            self.STARTING,
            "Preparando gravação…",
        )

        delay = {
            0: 0,
            1: 3,
            2: 5,
        }.get(
            self.countdown_combo.currentIndex(),
            0,
        )

        self._countdown_remaining = delay

        if delay <= 0:
            self._begin_session()
            return

        self._countdown_tick()

    def _countdown_tick(self) -> None:
        if self._state != self.STARTING:
            return

        if self._countdown_remaining <= 0:
            self._begin_session()
            return

        self.status_text.setText(
            f"A gravação começa em "
            f"{self._countdown_remaining}…"
        )
        self.state_chip.setText(
            str(self._countdown_remaining)
        )
        self._countdown_remaining -= 1

        QTimer.singleShot(
            1000,
            self._countdown_tick,
        )

    def _begin_session(self) -> None:
        if self._state != self.STARTING:
            return

        stamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        self._session_dir = (
            self.temp_root
            / f"session_{stamp}"
        )
        self._session_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.recordings_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._final_path = (
            self.recordings_dir
            / f"Gravacao_Tela_{stamp}.mp4"
        )
        self._segments = []
        self._elapsed_before_segment = 0.0

        if not self._start_segment():
            self._apply_state(
                self.ERROR,
                "Falha ao iniciar o FFmpeg. Consulte logs/screen_recorder.log.",
            )
            return

        self._apply_state(
            self.RECORDING,
            "Gravando…",
        )

        if self.hide_central.isChecked():
            window = self.window()
            if window is not None:
                self._hidden_by_recorder = True
                window.hide()

    def _capture_rect(self) -> QRect:
        if (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is not None
        ):
            rect = QRect(self._region)
        else:
            screen = self._selected_screen()
            rect = QRect(screen.geometry())

        width = max(2, rect.width())
        height = max(2, rect.height())

        # H.264 / yuv420p trabalha melhor com dimensões pares.
        if width % 2:
            width -= 1
        if height % 2:
            height -= 1

        return QRect(
            rect.x(),
            rect.y(),
            width,
            height,
        )

    def _fps(self) -> int:
        return (
            60
            if self.fps_combo.currentIndex() == 1
            else 30
        )

    def _crf(self) -> int:
        return {
            0: 18,
            1: 20,
            2: 23,
        }.get(
            self.quality_combo.currentIndex(),
            20,
        )

    def _audio_device(self) -> str | None:
        if self.audio_combo.currentIndex() <= 0:
            return None

        data = self.audio_combo.currentData()

        if data:
            return str(data)

        text = self.audio_combo.currentText()
        return text.split("  •  ")[0].strip()

    def _start_segment(self) -> bool:
        if self._session_dir is None:
            return False

        segment_number = len(self._segments) + 1
        segment = (
            self._session_dir
            / f"segment_{segment_number:03d}.mp4"
        )

        rect = self._capture_rect()
        fps = self._fps()
        crf = self._crf()
        audio = self._audio_device()

        command = [
            str(self.ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-thread_queue_size",
            "1024",
            "-f",
            "gdigrab",
            "-framerate",
            str(fps),
            "-draw_mouse",
            "1" if self.draw_mouse.isChecked() else "0",
            "-offset_x",
            str(rect.x()),
            "-offset_y",
            str(rect.y()),
            "-video_size",
            f"{rect.width()}x{rect.height()}",
            "-i",
            "desktop",
        ]

        if audio:
            command += [
                "-thread_queue_size",
                "1024",
                "-f",
                "dshow",
                "-i",
                f"audio={audio}",
            ]

        command += [
            "-map",
            "0:v:0",
        ]

        if audio:
            command += [
                "-map",
                "1:a:0",
            ]

        command += [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
        ]

        if audio:
            command += [
                "-c:a",
                "aac",
                "-b:a",
                "160k",
            ]

        command += [
            "-movflags",
            "+faststart",
            str(segment),
        ]

        try:
            log_path = (
                self.logs_dir
                / "screen_recorder.log"
            )
            self._log_handle = open(
                log_path,
                "ab",
                buffering=0,
            )

            self._log_handle.write(
                (
                    "\n\n=== "
                    + datetime.now().isoformat()
                    + " ===\n"
                    + " ".join(command)
                    + "\n"
                ).encode(
                    "utf-8",
                    errors="ignore",
                )
            )

            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self._log_handle,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as exc:
            self._close_log()
            self.status_text.setText(
                f"Falha ao iniciar: {exc}"
            )
            return False

        # Dá um instante para o FFmpeg acusar erro imediato.
        time.sleep(0.18)

        if self._process.poll() is not None:
            self._close_log()
            return False

        self._segments.append(segment)
        self._segment_started_at = time.monotonic()

        self.audio_value.setText(
            "Sem áudio"
            if not audio
            else self.audio_combo.currentText()
        )

        return True

    def toggle_pause(self) -> None:
        if self._state == self.RECORDING:
            self._pause_recording()
        elif self._state == self.PAUSED:
            self._resume_recording()

    def _pause_recording(self) -> None:
        if self._state != self.RECORDING:
            return

        self._finish_current_segment()
        self._apply_state(
            self.PAUSED,
            "Gravação pausada. Clique em Continuar para retomar.",
        )

    def _resume_recording(self) -> None:
        if self._state != self.PAUSED:
            return

        if not self._start_segment():
            self._apply_state(
                self.ERROR,
                "Não foi possível continuar a gravação.",
            )
            return

        self._apply_state(
            self.RECORDING,
            "Gravando…",
        )

    def stop_recording(self) -> None:
        if self._state not in {
            self.STARTING,
            self.RECORDING,
            self.PAUSED,
            self.ERROR,
        }:
            return

        if self._state == self.STARTING:
            self._apply_state(
                self.IDLE,
                "Gravação cancelada antes de iniciar.",
            )
            return

        if self._state == self.RECORDING:
            self._finish_current_segment()

        if not self._segments:
            self._apply_state(
                self.IDLE,
                "Nenhum segmento foi gravado.",
            )
            self._restore_window_after_recording()
            return

        self._apply_state(
            self.FINALIZING,
            "Finalizando arquivo MP4…",
        )

        QApplication.processEvents()

        ok = self._finalize_session()

        if ok and self._final_path is not None:
            self._apply_state(
                self.IDLE,
                f"Gravação salva: {self._final_path.name}",
            )
            self.recording_finished.emit(
                str(self._final_path)
            )
        else:
            self._apply_state(
                self.ERROR,
                "Não foi possível finalizar a gravação. Consulte o log.",
            )

        self._cleanup_session()
        self._refresh_recordings()
        self._restore_window_after_recording()

    def _finish_current_segment(self) -> None:
        if self._segment_started_at is not None:
            self._elapsed_before_segment += max(
                0.0,
                time.monotonic()
                - self._segment_started_at,
            )

        self._segment_started_at = None

        process = self._process
        self._process = None

        if process is None:
            self._close_log()
            return

        if process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write(b"q\n")
                    process.stdin.flush()
            except Exception:
                pass

            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                    process.wait(timeout=4)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

        self._close_log()

    def _finalize_session(self) -> bool:
        valid_segments = [
            path
            for path in self._segments
            if path.is_file()
            and path.stat().st_size > 1024
        ]

        if (
            not valid_segments
            or self._final_path is None
        ):
            return False

        try:
            if self._final_path.exists():
                self._final_path.unlink()
        except Exception:
            pass

        if len(valid_segments) == 1:
            try:
                shutil.move(
                    str(valid_segments[0]),
                    str(self._final_path),
                )
                return self._final_path.is_file()
            except Exception:
                return False

        if self._session_dir is None:
            return False

        concat_file = (
            self._session_dir
            / "concat.txt"
        )

        lines = []

        for path in valid_segments:
            safe = str(
                path.resolve()
            ).replace(
                "'",
                r"'\''",
            )
            lines.append(
                f"file '{safe}'"
            )

        concat_file.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        copy_cmd = [
            str(self.ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(self._final_path),
        ]

        if self._run_finalize_command(copy_cmd):
            return True

        # Fallback: se os segmentos diferirem em algum detalhe,
        # recodifica a junção.
        fallback = [
            str(self.ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(self._crf()),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(self._final_path),
        ]

        return self._run_finalize_command(
            fallback
        )

    def _run_finalize_command(
        self,
        command: list[str],
    ) -> bool:
        try:
            log_path = (
                self.logs_dir
                / "screen_recorder.log"
            )

            with open(
                log_path,
                "ab",
                buffering=0,
            ) as log:
                result = subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=log,
                    timeout=180,
                    creationflags=CREATE_NO_WINDOW,
                )

            return (
                result.returncode == 0
                and self._final_path is not None
                and self._final_path.is_file()
                and self._final_path.stat().st_size > 1024
            )
        except Exception:
            return False

    def _cleanup_session(self) -> None:
        self._process = None
        self._segment_started_at = None
        self._segments = []

        if (
            self._session_dir is not None
            and self._session_dir.exists()
        ):
            try:
                shutil.rmtree(
                    self._session_dir,
                    ignore_errors=True,
                )
            except Exception:
                pass

        self._session_dir = None

    def _close_log(self) -> None:
        handle = self._log_handle
        self._log_handle = None

        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # STATE / RUNTIME
    # ------------------------------------------------------------------

    def _elapsed_seconds(self) -> float:
        value = self._elapsed_before_segment

        if (
            self._state == self.RECORDING
            and self._segment_started_at is not None
        ):
            value += max(
                0.0,
                time.monotonic()
                - self._segment_started_at,
            )

        return value

    @staticmethod
    def _clock_text(seconds: float) -> str:
        total = max(0, int(seconds))
        return (
            f"{total // 3600:02d}:"
            f"{(total % 3600) // 60:02d}:"
            f"{total % 60:02d}"
        )

    def _update_runtime(self) -> None:
        self.duration_value.setText(
            self._clock_text(
                self._elapsed_seconds()
            )
        )

        if (
            self._state == self.RECORDING
            and self._process is not None
            and self._process.poll() is not None
        ):
            self._process = None
            self._close_log()
            self._apply_state(
                self.ERROR,
                "O FFmpeg encerrou inesperadamente. Consulte logs/screen_recorder.log.",
            )
            self._restore_window_after_recording()

    def _apply_state(
        self,
        state: str,
        message: str | None = None,
    ) -> None:
        self._state = state

        is_idle = state in {
            self.IDLE,
            self.ERROR,
        }
        recording = state == self.RECORDING
        paused = state == self.PAUSED
        starting = state == self.STARTING
        finalizing = state == self.FINALIZING

        self.start_button.setEnabled(
            is_idle
        )
        self.pause_button.setEnabled(
            recording or paused
        )
        self.stop_button.setEnabled(
            recording
            or paused
            or starting
        )

        self.pause_button.setText(
            "▶  Continuar"
            if paused
            else "Ⅱ  Pausar"
        )

        for widget in (
            self.screen_combo,
            self.mode_combo,
            self.select_region,
            self.fps_combo,
            self.quality_combo,
            self.audio_combo,
            self.refresh_audio,
            self.countdown_combo,
            self.draw_mouse,
            self.hide_central,
        ):
            widget.setEnabled(
                is_idle
            )

        if state == self.IDLE:
            self.state_chip.setText("PRONTO")
            self.state_chip.setStyleSheet(
                "background:#EAF9F2;color:#078B5F;"
                "border:1px solid #BFE8D5;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        elif state == self.RECORDING:
            self.state_chip.setText("● GRAVANDO")
            self.state_chip.setStyleSheet(
                "background:#FFE8ED;color:#D93050;"
                "border:1px solid #F5B5C3;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        elif state == self.PAUSED:
            self.state_chip.setText("Ⅱ PAUSADO")
            self.state_chip.setStyleSheet(
                "background:#FFF7DF;color:#9B6B00;"
                "border:1px solid #F0D48C;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        elif finalizing:
            self.state_chip.setText("FINALIZANDO")
            self.state_chip.setStyleSheet(
                "background:#EDF6FF;color:#087AF7;"
                "border:1px solid #CFE4FA;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        elif starting:
            self.state_chip.setText("PREPARANDO")

        else:
            self.state_chip.setText("ATENÇÃO")
            self.state_chip.setStyleSheet(
                "background:#FFF1F3;color:#D93050;"
                "border:1px solid #F5B5C3;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        if message:
            self.status_text.setText(
                message
            )

        self.state_changed.emit(state)

    def _restore_window_after_recording(self) -> None:
        if not self._hidden_by_recorder:
            return

        self._hidden_by_recorder = False

        window = self.window()

        if window is not None and not self._closing:
            window.show()
            window.raise_()
            window.activateWindow()

    # ------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------

    def shutdown(self) -> bool:
        self._closing = True

        try:
            if self._state == self.RECORDING:
                self._finish_current_segment()
                self._finalize_session()

            elif self._state == self.PAUSED:
                self._finalize_session()

            elif self._state == self.STARTING:
                self._apply_state(
                    self.IDLE,
                    "Gravação cancelada.",
                )

            self._cleanup_session()
        finally:
            self._preview_timer.stop()
            self._status_timer.stop()
            self._close_log()

        return True
