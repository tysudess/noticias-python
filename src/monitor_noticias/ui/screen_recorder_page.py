from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QScreen,
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
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.screen_recorder_audio import (
    AudioDevice,
    WasapiSegmentRecorder,
    backend_available,
    list_wasapi_devices,
)
from monitor_noticias.ui.screen_recorder_floating import (
    FloatingRecorderWidget,
)


CREATE_NO_WINDOW = 0x08000000 if sys.platform.startswith("win") else 0


class CaptureAreaOutline(QWidget):
    """Moldura vermelha persistente que não bloqueia o mouse."""

    BORDER = 4

    def __init__(self) -> None:
        super().__init__(None)

        self._capture_rect = QRect()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._exclude_from_capture()
        self.raise_()

    def _exclude_from_capture(self) -> None:
        if not sys.platform.startswith("win"):
            return

        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(
                int(self.winId()),
                0x00000011,
            )
        except Exception:
            pass

    def set_capture_rect(
        self,
        rect: QRect | None,
    ) -> None:
        if rect is None or rect.isEmpty():
            self._capture_rect = QRect()
            self.hide()
            return

        self._capture_rect = QRect(
            rect.normalized()
        )

        self.setGeometry(
            self._capture_rect.adjusted(
                -self.BORDER,
                -self.BORDER,
                self.BORDER,
                self.BORDER,
            )
        )

        if not self.isVisible():
            self.show()

        self.raise_()
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        frame = self.rect().adjusted(
            self.BORDER // 2,
            self.BORDER // 2,
            -(self.BORDER // 2) - 1,
            -(self.BORDER // 2) - 1,
        )

        painter.setPen(
            QPen(
                QColor("#FF274B"),
                self.BORDER,
            )
        )
        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )
        painter.drawRect(frame)

        badge = QRect(
            10,
            10,
            122,
            30,
        )
        painter.setPen(
            Qt.PenStyle.NoPen
        )
        painter.setBrush(
            QColor("#E71D43")
        )
        painter.drawRoundedRect(
            badge,
            7,
            7,
        )
        painter.setPen(
            QColor("#FFFFFF")
        )
        painter.setFont(
            QFont(
                "Segoe UI",
                10,
                QFont.Weight.Bold,
            )
        )
        painter.drawText(
            badge,
            Qt.AlignmentFlag.AlignCenter,
            "● ÁREA REC",
        )


class RegionEditorOverlay(QWidget):
    """Editor de área em tela cheia.

    Pode criar uma área do zero ou editar uma área existente.
    A tela cheia evita o problema da versão anterior em que a própria moldura
    mudava WindowTransparentForInput e depois deixava de receber o mouse.
    """

    accepted = Signal(QRect)
    cancelled = Signal()
    cleared = Signal()

    HANDLE = 12
    MIN_W = 160
    MIN_H = 100

    def __init__(
        self,
        screen: QScreen,
        initial: QRect | None = None,
    ) -> None:
        super().__init__(None)

        self.screen = screen
        self._screen_geometry = QRect(
            screen.geometry()
        )

        self._selection = QRect()
        self._drag_mode = ""
        self._drag_start = QPoint()
        self._drag_rect = QRect()
        self._creating = False

        if initial is not None and not initial.isEmpty():
            local = QRect(initial)
            local.translate(
                -self._screen_geometry.x(),
                -self._screen_geometry.y(),
            )
            self._selection = local.intersected(
                QRect(
                    0,
                    0,
                    self._screen_geometry.width(),
                    self._screen_geometry.height(),
                )
            )

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
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )
        self.setGeometry(
            self._screen_geometry
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
            return

        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            self._confirm()
            return

        if event.key() in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            self.cleared.emit()
            self.close()
            return

        if self._selection.isEmpty():
            super().keyPressEvent(event)
            return

        step = (
            10
            if (
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )
            else 1
        )

        rect = QRect(
            self._selection
        )

        if event.key() == Qt.Key.Key_Left:
            rect.translate(-step, 0)
        elif event.key() == Qt.Key.Key_Right:
            rect.translate(step, 0)
        elif event.key() == Qt.Key.Key_Up:
            rect.translate(0, -step)
        elif event.key() == Qt.Key.Key_Down:
            rect.translate(0, step)
        else:
            super().keyPressEvent(event)
            return

        self._selection = self._clamp(
            rect
        )
        self.update()

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = event.position().toPoint()

        if self._selection.isEmpty():
            self._creating = True
            self._drag_start = point
            self._selection = QRect(
                point,
                point,
            )
            self.update()
            return

        mode = self._hit_test(point)

        if not mode:
            # Clicar fora começa uma NOVA seleção imediatamente.
            self._creating = True
            self._drag_start = point
            self._selection = QRect(
                point,
                point,
            )
            self.update()
            return

        self._creating = False
        self._drag_mode = mode
        self._drag_start = point
        self._drag_rect = QRect(
            self._selection
        )

    def mouseMoveEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        point = event.position().toPoint()

        if (
            event.buttons()
            & Qt.MouseButton.LeftButton
        ):
            if self._creating:
                self._selection = self._clamp(
                    QRect(
                        self._drag_start,
                        point,
                    ).normalized()
                )
                self.update()
                return

            if self._drag_mode:
                delta = (
                    point
                    - self._drag_start
                )
                rect = QRect(
                    self._drag_rect
                )

                if self._drag_mode == "move":
                    rect.translate(
                        delta.x(),
                        delta.y(),
                    )
                else:
                    if "left" in self._drag_mode:
                        rect.setLeft(
                            self._drag_rect.left()
                            + delta.x()
                        )
                    if "right" in self._drag_mode:
                        rect.setRight(
                            self._drag_rect.right()
                            + delta.x()
                        )
                    if "top" in self._drag_mode:
                        rect.setTop(
                            self._drag_rect.top()
                            + delta.y()
                        )
                    if "bottom" in self._drag_mode:
                        rect.setBottom(
                            self._drag_rect.bottom()
                            + delta.y()
                        )

                rect = rect.normalized()
                rect = self._minimum(
                    rect
                )
                self._selection = self._clamp(
                    rect
                )
                self.update()
                return

        self._update_cursor(point)

    def mouseReleaseEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._creating:
            self._creating = False

            if (
                self._selection.width()
                < self.MIN_W
                or self._selection.height()
                < self.MIN_H
            ):
                self._selection = QRect()

        self._drag_mode = ""
        self._update_cursor(
            event.position().toPoint()
        )
        self.update()

    def mouseDoubleClickEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if (
            event.button()
            == Qt.MouseButton.LeftButton
            and not self._selection.isEmpty()
            and self._selection.contains(
                event.position().toPoint()
            )
        ):
            self._confirm()

    def _confirm(self) -> None:
        if (
            self._selection.width()
            < self.MIN_W
            or self._selection.height()
            < self.MIN_H
        ):
            return

        rect = QRect(
            self._selection
        )
        rect.translate(
            self._screen_geometry.x(),
            self._screen_geometry.y(),
        )

        self.accepted.emit(rect)
        self.close()

    def _hit_test(
        self,
        point: QPoint,
    ) -> str:
        if self._selection.isEmpty():
            return ""

        rect = QRect(
            self._selection
        )

        near_left = abs(
            point.x()
            - rect.left()
        ) <= self.HANDLE
        near_right = abs(
            point.x()
            - rect.right()
        ) <= self.HANDLE
        near_top = abs(
            point.y()
            - rect.top()
        ) <= self.HANDLE
        near_bottom = abs(
            point.y()
            - rect.bottom()
        ) <= self.HANDLE

        if near_left and near_top:
            return "left-top"
        if near_right and near_top:
            return "right-top"
        if near_left and near_bottom:
            return "left-bottom"
        if near_right and near_bottom:
            return "right-bottom"
        if near_left:
            return "left"
        if near_right:
            return "right"
        if near_top:
            return "top"
        if near_bottom:
            return "bottom"
        if rect.contains(point):
            return "move"

        return ""

    def _update_cursor(
        self,
        point: QPoint,
    ) -> None:
        mapping = {
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "left-top": Qt.CursorShape.SizeFDiagCursor,
            "right-bottom": Qt.CursorShape.SizeFDiagCursor,
            "right-top": Qt.CursorShape.SizeBDiagCursor,
            "left-bottom": Qt.CursorShape.SizeBDiagCursor,
            "move": Qt.CursorShape.SizeAllCursor,
        }

        self.setCursor(
            mapping.get(
                self._hit_test(point),
                Qt.CursorShape.CrossCursor,
            )
        )

    def _minimum(
        self,
        rect: QRect,
    ) -> QRect:
        rect = QRect(rect)

        if rect.width() < self.MIN_W:
            rect.setWidth(
                self.MIN_W
            )

        if rect.height() < self.MIN_H:
            rect.setHeight(
                self.MIN_H
            )

        return rect

    def _clamp(
        self,
        rect: QRect,
    ) -> QRect:
        bounds = QRect(
            0,
            0,
            self.width(),
            self.height(),
        )

        rect = QRect(rect)

        if rect.width() > bounds.width():
            rect.setWidth(
                bounds.width()
            )
        if rect.height() > bounds.height():
            rect.setHeight(
                bounds.height()
            )

        if rect.left() < bounds.left():
            rect.moveLeft(
                bounds.left()
            )
        if rect.top() < bounds.top():
            rect.moveTop(
                bounds.top()
            )
        if rect.right() > bounds.right():
            rect.moveRight(
                bounds.right()
            )
        if rect.bottom() > bounds.bottom():
            rect.moveBottom(
                bounds.bottom()
            )

        return rect

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        painter.fillRect(
            self.rect(),
            QColor(4, 14, 28, 155),
        )

        if self._selection.isEmpty():
            painter.setPen(
                QColor("#FFFFFF")
            )
            painter.setFont(
                QFont(
                    "Segoe UI",
                    14,
                    QFont.Weight.Bold,
                )
            )
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "ARRASTE PARA CRIAR UMA NOVA ÁREA\n"
                "Enter confirma • Esc cancela",
            )
            return

        rect = QRect(
            self._selection
        )

        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_Clear
        )
        painter.fillRect(
            rect,
            Qt.GlobalColor.transparent,
        )
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver
        )

        painter.setPen(
            QPen(
                QColor("#FF274B"),
                4,
            )
        )
        painter.setBrush(
            Qt.BrushStyle.NoBrush
        )
        painter.drawRect(rect)

        painter.setPen(
            QColor("#FFFFFF")
        )
        painter.setFont(
            QFont(
                "Segoe UI",
                10,
                QFont.Weight.Bold,
            )
        )
        painter.drawText(
            rect.adjusted(
                12,
                10,
                -12,
                -10,
            ),
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft,
            f"{rect.width()}×{rect.height()}  "
            "• arraste centro para mover "
            "• bordas/cantos para redimensionar",
        )

        painter.setBrush(
            QColor("#FF274B")
        )
        painter.setPen(
            QPen(
                QColor("#FFFFFF"),
                2,
            )
        )

        points = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight(),
            QPoint(
                rect.center().x(),
                rect.top(),
            ),
            QPoint(
                rect.center().x(),
                rect.bottom(),
            ),
            QPoint(
                rect.left(),
                rect.center().y(),
            ),
            QPoint(
                rect.right(),
                rect.center().y(),
            ),
        ]

        for point in points:
            painter.drawRect(
                QRect(
                    point.x() - 5,
                    point.y() - 5,
                    10,
                    10,
                )
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
    OFF = "off"

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
        self._region_editor: RegionEditorOverlay | None = None
        self._capture_overlay = CaptureAreaOutline()

        self._audio_loaded = False
        self._audio_devices: dict[str, AudioDevice] = {}
        self._audio_engine: WasapiSegmentRecorder | None = None
        self._audio_segments: list[Path | None] = []
        self._session_audio_device: AudioDevice | None = None

        self._hidden_by_recorder = False
        self._module_enabled = False
        self._closing = False

        # Não existe mais pré-visualização contínua. Isso reduz CPU/GPU e evita
        # o efeito de espelho infinito quando a Central captura a própria tela.

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(250)
        self._status_timer.timeout.connect(
            self._update_runtime
        )
        self._status_timer.start()

        self._build_ui()

        self.floating = FloatingRecorderWidget()
        self.floating.record_requested.connect(
            self.start_recording
        )
        self.floating.pause_requested.connect(
            self.toggle_pause
        )
        self.floating.stop_requested.connect(
            self.stop_recording
        )
        self.floating.central_requested.connect(
            self._show_central
        )
        self.floating.hide()

        self._refresh_screens()
        self._refresh_recordings()
        self._apply_state(
            self.OFF,
            "Gravador de Tela desligado por padrão.",
        )
        self._update_capture_labels()
        self._update_capture_overlay()

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

        self.power_button = QPushButton("⏻  LIGAR")
        self.power_button.setObjectName("recPower")
        self.power_button.setCheckable(True)
        self.power_button.setChecked(False)
        self.power_button.setMinimumWidth(126)
        self.power_button.toggled.connect(
            self._toggle_module
        )
        hero_l.addWidget(self.power_button)

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

        capture_card = QFrame()
        capture_card.setObjectName("recCard")
        capture_l = QVBoxLayout(capture_card)
        capture_l.setContentsMargins(16, 14, 16, 14)
        capture_l.setSpacing(10)

        capture_title = QLabel("Área de captura")
        capture_title.setObjectName("recSectionTitle")
        capture_l.addWidget(capture_title)

        self.region_badge = QLabel("● REC  Tela inteira")
        self.region_badge.setObjectName("recSmallBadge")
        self.region_badge.setWordWrap(True)
        capture_l.addWidget(self.region_badge)

        self.capture_details = QLabel(
            "Monitor inteiro. A moldura vermelha mostra exatamente "
            "o que será gravado."
        )
        self.capture_details.setObjectName("recMuted")
        self.capture_details.setWordWrap(True)
        capture_l.addWidget(self.capture_details)

        capture_actions = QHBoxLayout()
        capture_actions.setSpacing(8)

        self.new_region_button = QPushButton(
            "＋  Nova área"
        )
        self.new_region_button.setObjectName(
            "recSecondary"
        )
        self.new_region_button.clicked.connect(
            self._choose_region
        )
        capture_actions.addWidget(
            self.new_region_button
        )

        self.adjust_region = QPushButton(
            "↔  Ajustar área"
        )
        self.adjust_region.setObjectName(
            "recSecondary"
        )
        self.adjust_region.clicked.connect(
            self._adjust_region
        )
        capture_actions.addWidget(
            self.adjust_region
        )

        self.clear_region = QPushButton(
            "×  Remover área"
        )
        self.clear_region.setObjectName(
            "recSecondary"
        )
        self.clear_region.clicked.connect(
            self._clear_region
        )
        capture_actions.addWidget(
            self.clear_region
        )

        self.quick_rec = QPushButton(
            "●  REC"
        )
        self.quick_rec.setObjectName(
            "recQuickRec"
        )
        self.quick_rec.clicked.connect(
            self._quick_record
        )
        capture_actions.addWidget(
            self.quick_rec
        )

        capture_l.addLayout(
            capture_actions
        )

        capture_help = QLabel(
            "Você pode recriar a área quantas vezes quiser. "
            "Ao ajustar, arraste o centro para mover e as bordas/cantos para redimensionar."
        )
        capture_help.setObjectName(
            "recAudioStatus"
        )
        capture_help.setWordWrap(True)
        capture_l.addWidget(
            capture_help
        )

        center.addWidget(
            capture_card,
            1,
        )

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
        config_l.addWidget(
            self._field(
                "Modo de captura",
                self.mode_combo,
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
        self.audio_combo.addItem("Sem áudio", "none")
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

        self.audio_status = QLabel(
            "Ao ligar o módulo, a Central procura áudio do sistema via WASAPI."
        )
        self.audio_status.setObjectName(
            "recAudioStatus"
        )
        self.audio_status.setWordWrap(True)
        config_l.addWidget(
            self.audio_status
        )

        self.audio_combo.currentIndexChanged.connect(
            self._audio_selection_changed
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

        QPushButton#recPower {
            background:#EAF9F2;
            color:#078B5F;
            border:1px solid #BFE8D5;
            border-radius:9px;
            padding:8px 14px;
            font-size:10px;
            font-weight:900;
        }

        QPushButton#recPower:!checked {
            background:#F1F4F8;
            color:#75859A;
            border-color:#D9E1EB;
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

        QPushButton#recQuickRec {
            background:#E71D43;
            color:#FFFFFF;
            border:0;
            border-radius:8px;
            padding:8px 10px;
            font-size:10px;
            font-weight:900;
        }

        QPushButton#recQuickRec:hover {
            background:#C91436;
        }

        QLabel#recAudioStatus {
            background:#F8FBFF;
            color:#5E7599;
            border:1px solid #DCE8F5;
            border-radius:7px;
            padding:6px 8px;
            font-size:9px;
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
        self._refresh_recordings()

        if not self._module_enabled:
            self._capture_overlay.hide()
            self.floating.hide()
            self._apply_state(
                self.OFF,
                "Gravador de Tela desligado por padrão.",
            )
            return

        if not self._audio_loaded:
            self._load_audio_devices()

        self._update_capture_labels()
        self._update_capture_overlay()

        if not self.floating.isVisible():
            self.floating.show()

    def showEvent(self, event) -> None:
        super().showEvent(event)

        if self._module_enabled:
            self._update_capture_overlay()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)

        # A moldura e o widget flutuante continuam disponíveis mesmo quando
        # o usuário navega para outra aba.
        if self._module_enabled:
            self._update_capture_overlay()


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

    # ------------------------------------------------------------------
    # REGION
    # ------------------------------------------------------------------

    def _choose_region(self) -> None:
        """Cria uma NOVA área, mesmo que já exista outra."""
        if self.is_active or not self._module_enabled:
            return

        self._close_region_editor()

        screen = self._selected_screen()

        if screen is None:
            return

        self.mode_combo.setCurrentText(
            "Área personalizada"
        )

        # Esconde a moldura antiga enquanto o usuário cria a nova.
        self._capture_overlay.hide()

        editor = RegionEditorOverlay(
            screen,
            None,
        )
        editor.accepted.connect(
            self._region_accepted
        )
        editor.cancelled.connect(
            self._region_editor_cancelled
        )
        editor.cleared.connect(
            self._clear_region
        )

        self._region_editor = editor
        editor.show()

    def _adjust_region(self) -> None:
        if (
            self.is_active
            or not self._module_enabled
            or self._region is None
        ):
            return

        self._close_region_editor()

        screen = self._selected_screen()

        if screen is None:
            return

        self._capture_overlay.hide()

        editor = RegionEditorOverlay(
            screen,
            self._region,
        )
        editor.accepted.connect(
            self._region_accepted
        )
        editor.cancelled.connect(
            self._region_editor_cancelled
        )
        editor.cleared.connect(
            self._clear_region
        )

        self._region_editor = editor
        editor.show()

    def _region_accepted(
        self,
        rect: QRect,
    ) -> None:
        self._region_editor = None
        self._region = QRect(
            rect.normalized()
        )
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(
            "Área personalizada"
        )
        self.mode_combo.blockSignals(False)

        self._update_capture_labels()
        self._update_capture_overlay()

        self.status_text.setText(
            "Área definida: "
            f"X {self._region.x()} • "
            f"Y {self._region.y()} • "
            f"{self._region.width()}×{self._region.height()}"
        )

    def _region_editor_cancelled(self) -> None:
        self._region_editor = None
        self._update_capture_overlay()
        self.status_text.setText(
            "Ajuste cancelado."
        )

    def _close_region_editor(self) -> None:
        editor = self._region_editor
        self._region_editor = None

        if editor is not None:
            try:
                editor.close()
            except Exception:
                pass

    def _clear_region(self) -> None:
        if self.is_active:
            return

        self._close_region_editor()
        self._region = None

        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(
            "Tela inteira"
        )
        self.mode_combo.blockSignals(False)

        self._update_capture_labels()
        self._update_capture_overlay()

        self.status_text.setText(
            "Área personalizada removida. "
            "A captura voltou para a tela inteira."
        )

    def _mode_changed(
        self,
        text: str,
    ) -> None:
        if text == "Tela inteira":
            self._region = None

        elif (
            text == "Área personalizada"
            and self._region is None
            and self._module_enabled
            and not self.is_active
        ):
            QTimer.singleShot(
                0,
                self._choose_region,
            )
            return

        self._update_capture_labels()
        self._update_capture_overlay()

    def _screen_changed(
        self,
        _index: int,
    ) -> None:
        if self.is_active:
            return

        self._close_region_editor()
        self._region = None

        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(
            "Tela inteira"
        )
        self.mode_combo.blockSignals(False)

        self._update_capture_labels()
        self._update_capture_overlay()

    def _update_capture_labels(self) -> None:
        custom = (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is not None
        )

        if custom:
            rect = self._region
            self.source_value.setText(
                "Área personalizada"
            )
            self.region_badge.setText(
                "● REC  "
                f"{rect.width()}×{rect.height()} "
                f"• X {rect.x()} • Y {rect.y()}"
            )
            self.capture_details.setText(
                "Área personalizada ativa. "
                "Use Nova área para refazer do zero, Ajustar área para mover/redimensionar "
                "ou Remover área para voltar à tela inteira."
            )
        else:
            screen = self._selected_screen()
            geometry = (
                screen.geometry()
                if screen is not None
                else QRect()
            )
            self.source_value.setText(
                "Tela inteira"
            )
            self.region_badge.setText(
                "● REC  Tela inteira"
            )
            self.capture_details.setText(
                "Monitor inteiro: "
                f"{geometry.width()}×{geometry.height()}."
            )

        self.region_badge.setStyleSheet(
            "background:#FFE7EC;"
            "color:#D8173C;"
            "border:1px solid #F3AABC;"
            "border-radius:7px;"
            "padding:7px 10px;"
            "font-size:10px;"
            "font-weight:900;"
        )

        idle = (
            self._module_enabled
            and not self.is_active
        )

        self.new_region_button.setEnabled(
            idle
        )
        self.adjust_region.setEnabled(
            idle
            and custom
        )
        self.clear_region.setEnabled(
            idle
            and custom
        )

    def _current_capture_rect(
        self,
    ) -> QRect | None:
        if not self._module_enabled:
            return None

        if (
            self.mode_combo.currentText()
            == "Área personalizada"
            and self._region is not None
        ):
            return QRect(
                self._region
            )

        screen = self._selected_screen()

        if screen is None:
            return None

        return QRect(
            screen.geometry()
        )

    def _update_capture_overlay(self) -> None:
        if not self._module_enabled:
            self._capture_overlay.hide()
            return

        self._capture_overlay.set_capture_rect(
            self._current_capture_rect()
        )

    # ------------------------------------------------------------------
    # AUDIO
    # ------------------------------------------------------------------

    def _load_audio_devices(self) -> None:
        """Carrega áudio do sistema via WASAPI loopback e microfones."""
        previous = self.audio_combo.currentData()

        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        self.audio_combo.addItem(
            "Sem áudio",
            "none",
        )
        self._audio_devices = {}

        devices, diagnostic = (
            list_wasapi_devices()
        )

        try:
            (
                self.logs_dir
                / "screen_recorder_audio_devices.log"
            ).write_text(
                diagnostic,
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            pass

        system_index = -1
        first_mic_index = -1

        for device in devices:
            self._audio_devices[
                device.key
            ] = device

            if device.kind == "system":
                label = (
                    "Áudio do sistema • WASAPI "
                    f"({device.name})"
                )
            else:
                label = (
                    "Microfone • "
                    f"{device.name}"
                )

            self.audio_combo.addItem(
                label,
                device.key,
            )

            index = (
                self.audio_combo.count()
                - 1
            )

            if (
                device.kind == "system"
                and system_index < 0
            ):
                system_index = index

            if (
                device.kind == "microphone"
                and first_mic_index < 0
            ):
                first_mic_index = index

        self.audio_combo.blockSignals(False)
        self._audio_loaded = True

        old_index = (
            self.audio_combo.findData(
                previous
            )
            if previous
            else -1
        )

        if old_index >= 0:
            selected = old_index
        elif system_index >= 0:
            # Áudio do sistema é o padrão quando o módulo está ligado.
            selected = system_index
        elif first_mic_index >= 0:
            selected = first_mic_index
        else:
            selected = 0

        self.audio_combo.setCurrentIndex(
            selected
        )

        if not backend_available():
            self.audio_status.setText(
                "PyAudioWPatch não está disponível. "
                "O portable precisa ser recompilado com a V18."
            )
        elif system_index >= 0:
            self.audio_status.setText(
                "Áudio do sistema detectado via WASAPI loopback. "
                "Não depende de Stereo Mix."
            )
        elif first_mic_index >= 0:
            self.audio_status.setText(
                "O Windows não expôs loopback de saída, "
                "mas há microfone disponível."
            )
        else:
            self.audio_status.setText(
                "Nenhum dispositivo WASAPI foi encontrado. "
                "Veja logs/screen_recorder_audio_devices.log."
            )

        self._audio_selection_changed(
            self.audio_combo.currentIndex()
        )

    def _selected_audio_device(
        self,
    ) -> AudioDevice | None:
        key = self.audio_combo.currentData()

        if not key or key == "none":
            return None

        return self._audio_devices.get(
            str(key)
        )

    def _audio_selection_changed(
        self,
        _index: int,
    ) -> None:
        device = self._selected_audio_device()

        if device is None:
            self.audio_value.setText(
                "Sem áudio"
            )
            return

        self.audio_value.setText(
            "Sistema"
            if device.kind == "system"
            else "Microfone"
        )

    # ------------------------------------------------------------------
    # POWER / QUICK REC
    # ------------------------------------------------------------------

    def _quick_record(self) -> None:
        if not self._module_enabled:
            return

        if self._state in {
            self.RECORDING,
            self.PAUSED,
            self.STARTING,
        }:
            self.stop_recording()
            return

        self.start_recording()

    def _quick_record(self) -> None:
        if not self._module_enabled:
            return

        if self._state in {
            self.RECORDING,
            self.PAUSED,
            self.STARTING,
        }:
            self.stop_recording()
            return

        self.start_recording()

    def _toggle_module(
        self,
        enabled: bool,
    ) -> None:
        if enabled == self._module_enabled:
            return

        if not enabled and self.is_active:
            answer = QMessageBox.question(
                self,
                "Desligar Gravador de Tela",
                "Existe uma gravação em andamento. "
                "Deseja finalizar a gravação e desligar o módulo?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                self.power_button.blockSignals(
                    True
                )
                self.power_button.setChecked(
                    True
                )
                self.power_button.blockSignals(
                    False
                )
                return

        self._module_enabled = enabled

        if not enabled:
            self._close_region_editor()

            if self._state in {
                self.RECORDING,
                self.PAUSED,
                self.STARTING,
            }:
                self.stop_recording()

            self._capture_overlay.hide()
            self.floating.hide()

            self.power_button.setText(
                "⏻  LIGAR"
            )
            self._apply_state(
                self.OFF,
                "Gravador de Tela desligado.",
            )
            return

        self.power_button.setText(
            "⏻  DESLIGAR"
        )
        self._refresh_screens()
        self._load_audio_devices()

        self._apply_state(
            self.IDLE,
            "Gravador de Tela ligado e pronto.",
        )
        self._update_capture_labels()
        self._update_capture_overlay()

        self.floating.show()
        self.floating.raise_()

    def _show_central(self) -> None:
        window = self.window()

        if window is None:
            return

        window.show()
        window.raise_()
        window.activateWindow()

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
        self._close_region_editor()

        if not self._module_enabled:
            QMessageBox.information(
                self,
                "Gravador desligado",
                "Ligue o Gravador de Tela antes de iniciar uma gravação.",
            )
            return

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
        self._audio_segments = []
        self._session_audio_device = (
            self._selected_audio_device()
        )
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

        segment_number = len(
            self._segments
        ) + 1

        segment = (
            self._session_dir
            / f"segment_{segment_number:03d}.mp4"
        )
        audio_path = (
            self._session_dir
            / f"audio_{segment_number:03d}.wav"
        )

        rect = self._capture_rect()
        fps = self._fps()
        crf = self._crf()

        # Áudio via WASAPI loopback/microfone em arquivo WAV paralelo.
        self._audio_engine = None

        if self._session_audio_device is not None:
            try:
                recorder = (
                    WasapiSegmentRecorder(
                        self._session_audio_device,
                        audio_path,
                    )
                )
                recorder.start()
                self._audio_engine = recorder
            except Exception as exc:
                self.audio_status.setText(
                    "Falha ao iniciar áudio WASAPI: "
                    f"{exc}"
                )
                self.status_text.setText(
                    "A gravação não iniciou porque o áudio selecionado falhou."
                )
                return False

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
            "1"
            if self.draw_mouse.isChecked()
            else "0",
            "-offset_x",
            str(rect.x()),
            "-offset_y",
            str(rect.y()),
            "-video_size",
            f"{rect.width()}x{rect.height()}",
            "-i",
            "desktop",
            "-map",
            "0:v:0",
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
            self._stop_audio_engine()
            self._close_log()
            self.status_text.setText(
                f"Falha ao iniciar: {exc}"
            )
            return False

        time.sleep(0.18)

        if self._process.poll() is not None:
            self._stop_audio_engine()
            self._close_log()
            return False

        self._segments.append(
            segment
        )
        self._audio_segments.append(
            audio_path
            if self._session_audio_device is not None
            else None
        )
        self._segment_started_at = (
            time.monotonic()
        )

        if self._session_audio_device is None:
            self.audio_value.setText(
                "Sem áudio"
            )
        else:
            self.audio_value.setText(
                "Sistema"
                if (
                    self._session_audio_device.kind
                    == "system"
                )
                else "Microfone"
            )

        return True

    def _stop_audio_engine(self) -> None:
        recorder = self._audio_engine
        self._audio_engine = None

        if recorder is not None:
            try:
                recorder.stop()
            except Exception:
                pass


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

        if process is not None and process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write(
                        b"q\n"
                    )
                    process.stdin.flush()
            except Exception:
                pass

            try:
                process.wait(
                    timeout=12
                )
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                    process.wait(
                        timeout=4
                    )
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

        self._stop_audio_engine()
        self._close_log()


    def _finalize_session(self) -> bool:
        if self._final_path is None:
            return False

        records: list[
            tuple[Path, Path | None]
        ] = []

        for index, video in enumerate(
            self._segments
        ):
            if (
                not video.is_file()
                or video.stat().st_size <= 1024
            ):
                continue

            audio = (
                self._audio_segments[index]
                if index < len(self._audio_segments)
                else None
            )
            records.append(
                (video, audio)
            )

        if not records:
            return False

        try:
            if self._final_path.exists():
                self._final_path.unlink()
        except Exception:
            pass

        prepared: list[Path] = []

        for index, (
            video,
            audio,
        ) in enumerate(records, start=1):
            if self._session_audio_device is None:
                prepared.append(video)
                continue

            muxed = (
                self._session_dir
                / f"muxed_{index:03d}.mp4"
            )

            if not self._mux_audio_segment(
                video,
                audio,
                muxed,
            ):
                return False

            prepared.append(muxed)

        if len(prepared) == 1:
            try:
                shutil.move(
                    str(prepared[0]),
                    str(self._final_path),
                )
                return (
                    self._final_path.is_file()
                    and self._final_path.stat().st_size
                    > 1024
                )
            except Exception:
                return False

        if self._session_dir is None:
            return False

        concat_file = (
            self._session_dir
            / "concat.txt"
        )

        lines = []

        for path in prepared:
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

        if self._run_finalize_command(
            copy_cmd
        ):
            return True

        # Fallback recodificando caso algum detalhe entre segmentos varie.
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
        ]

        if self._session_audio_device is not None:
            fallback += [
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ]

        fallback += [
            "-movflags",
            "+faststart",
            str(self._final_path),
        ]

        return self._run_finalize_command(
            fallback
        )

    def _mux_audio_segment(
        self,
        video: Path,
        audio: Path | None,
        output: Path,
    ) -> bool:
        device = self._session_audio_device

        if device is None:
            return False

        has_audio = (
            audio is not None
            and audio.is_file()
            and audio.stat().st_size > 64
        )

        if has_audio:
            command = [
                str(self.ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-i",
                str(video),
                "-i",
                str(audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output),
            ]
        else:
            layout = (
                "mono"
                if device.channels == 1
                else "stereo"
            )

            command = [
                str(self.ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-i",
                str(video),
                "-f",
                "lavfi",
                "-i",
                (
                    "anullsrc="
                    f"channel_layout={layout}:"
                    f"sample_rate={device.rate}"
                ),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output),
            ]

        return self._run_finalize_command(
            command,
            output_path=output,
        )


    def _run_finalize_command(
        self,
        command: list[str],
        *,
        output_path: Path | None = None,
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

            expected = (
                output_path
                if output_path is not None
                else self._final_path
            )

            return (
                result.returncode == 0
                and expected is not None
                and expected.is_file()
                and expected.stat().st_size > 1024
            )
        except Exception:
            return False

    def _cleanup_session(self) -> None:
        self._process = None
        self._segment_started_at = None
        self._stop_audio_engine()
        self._segments = []
        self._audio_segments = []
        self._session_audio_device = None

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
        elapsed_text = self._clock_text(
            self._elapsed_seconds()
        )
        self.duration_value.setText(
            elapsed_text
        )

        if hasattr(self, "floating"):
            self.floating.set_elapsed(
                elapsed_text
            )

        if (
            self._state == self.RECORDING
            and self._process is not None
            and self._process.poll() is not None
        ):
            self._process = None
            self._stop_audio_engine()
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

        is_idle = (
            self._module_enabled
            and state in {
                self.IDLE,
                self.ERROR,
            }
        )
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
            self._module_enabled
            and (
                recording
                or paused
                or starting
            )
        )

        self.quick_rec.setEnabled(
            self._module_enabled
            and not finalizing
        )
        self.quick_rec.setText(
            "■  STOP"
            if state in {
                self.RECORDING,
                self.PAUSED,
                self.STARTING,
            }
            else "●  REC"
        )

        self.pause_button.setText(
            "▶  Continuar"
            if paused
            else "Ⅱ  Pausar"
        )

        for widget in (
            self.screen_combo,
            self.mode_combo,
            self.new_region_button,
            self.adjust_region,
            self.clear_region,
            self.fps_combo,
            self.quality_combo,
            self.audio_combo,
            self.refresh_audio,
            self.countdown_combo,
            self.draw_mouse,
            self.hide_central,
        ):
            widget.setEnabled(
                self._module_enabled
                and is_idle
            )

        if state == self.OFF:
            self.state_chip.setText("DESLIGADO")
            self.state_chip.setStyleSheet(
                "background:#F1F4F8;color:#75859A;"
                "border:1px solid #D9E1EB;"
                "border-radius:9px;padding:8px 14px;"
                "font-weight:900;"
            )

        elif state == self.IDLE:
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

        self._update_capture_labels()

        if hasattr(self, "floating"):
            self.floating.set_state(
                state
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
        self._close_region_editor()

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
            self._status_timer.stop()
            self._capture_overlay.hide()
            self._stop_audio_engine()

            if hasattr(self, "floating"):
                self.floating.hide()
                self.floating.close()

            self._close_log()

        return True
