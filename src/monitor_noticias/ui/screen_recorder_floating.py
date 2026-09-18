from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class FloatingRecorderWidget(QWidget):
    record_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    area_requested = Signal()
    central_requested = Signal()

    def __init__(self) -> None:
        super().__init__(None)

        self._drag_origin: QPoint | None = None
        self._window_origin = QPoint()
        self._state = "idle"

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )

        shell = QFrame(self)
        shell.setObjectName("floatingRecorder")

        layout = QHBoxLayout(shell)
        layout.setContentsMargins(
            10,
            7,
            10,
            7,
        )
        layout.setSpacing(7)

        self.state_dot = QLabel("●")
        self.state_dot.setObjectName(
            "floatingDot"
        )
        layout.addWidget(self.state_dot)

        self.timer = QLabel("00:00:00")
        self.timer.setObjectName(
            "floatingTimer"
        )
        layout.addWidget(self.timer)

        self.record = QPushButton("REC")
        self.record.setObjectName(
            "floatingRec"
        )
        self.record.clicked.connect(
            self.record_requested.emit
        )
        layout.addWidget(self.record)

        self.pause = QPushButton("Ⅱ")
        self.pause.setObjectName(
            "floatingPause"
        )
        self.pause.clicked.connect(
            self.pause_requested.emit
        )
        layout.addWidget(self.pause)

        self.stop = QPushButton("■")
        self.stop.setObjectName(
            "floatingStop"
        )
        self.stop.clicked.connect(
            self.stop_requested.emit
        )
        layout.addWidget(self.stop)

        self.area = QPushButton("ÁREA")
        self.area.setObjectName(
            "floatingArea"
        )
        self.area.clicked.connect(
            self.area_requested.emit
        )
        self.area.setToolTip(
            "Mover ou redimensionar a área mesmo durante a gravação"
        )
        layout.addWidget(self.area)

        self.central = QPushButton("CENTRAL")
        self.central.setObjectName(
            "floatingCentral"
        )
        self.central.clicked.connect(
            self.central_requested.emit
        )
        layout.addWidget(self.central)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(shell)

        self.setStyleSheet(
            """
            QFrame#floatingRecorder {
                background:#071426;
                border:1px solid #29496D;
                border-radius:12px;
            }

            QLabel#floatingDot {
                color:#6F8198;
                font-size:18px;
                font-weight:900;
            }

            QLabel#floatingTimer {
                color:#FFFFFF;
                font-size:12px;
                font-weight:900;
                min-width:68px;
            }

            QPushButton {
                border-radius:8px;
                min-height:30px;
                padding:0 10px;
                font-size:9px;
                font-weight:900;
            }

            QPushButton#floatingRec {
                background:#E71D43;
                color:white;
                border:0;
            }

            QPushButton#floatingPause {
                background:#FFF1C8;
                color:#8B6100;
                border:1px solid #EBCB74;
            }

            QPushButton#floatingStop {
                background:#FFE5EA;
                color:#C72444;
                border:1px solid #F0A9B7;
            }

            QPushButton#floatingArea {
                background:#FFF0F3;
                color:#D8173C;
                border:1px solid #F0A9B7;
            }

            QPushButton#floatingCentral {
                background:#E7F2FF;
                color:#086DCE;
                border:1px solid #A9CDF2;
            }

            QPushButton:disabled {
                background:#233346;
                color:#718096;
                border-color:#30455E;
            }
            """
        )

        self.set_state("idle")
        self.adjustSize()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._exclude_from_capture()

        if self.pos() == QPoint(0, 0):
            self.move_to_default_position()

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

    def move_to_default_position(self) -> None:
        screen = QApplication.primaryScreen()

        if screen is None:
            return

        area = screen.availableGeometry()
        self.adjustSize()

        self.move(
            area.right()
            - self.width()
            - 24,
            area.top()
            + 24,
        )

    def set_elapsed(
        self,
        value: str,
    ) -> None:
        self.timer.setText(value)

    def set_state(
        self,
        state: str,
    ) -> None:
        self._state = state

        recording = state == "recording"
        paused = state == "paused"
        starting = state == "starting"
        finalizing = state == "finalizing"
        busy = recording or paused or starting

        self.record.setEnabled(
            not busy and not finalizing
        )
        self.pause.setEnabled(
            recording or paused
        )
        self.stop.setEnabled(
            busy
        )

        # A área pode ser reajustada durante gravação e pausa.
        self.area.setEnabled(
            not starting and not finalizing
        )

        self.pause.setText(
            "▶"
            if paused
            else "Ⅱ"
        )

        if recording:
            self.state_dot.setStyleSheet(
                "color:#FF3158;"
            )
        elif paused:
            self.state_dot.setStyleSheet(
                "color:#F4B000;"
            )
        elif finalizing:
            self.state_dot.setStyleSheet(
                "color:#2F90FF;"
            )
        else:
            self.state_dot.setStyleSheet(
                "color:#6F8198;"
            )

    def set_area_editing(
        self,
        editing: bool,
    ) -> None:
        self.area.setText(
            "OK ÁREA"
            if editing
            else "ÁREA"
        )
        self.area.setToolTip(
            (
                "Concluir o ajuste contínuo da área"
                if editing
                else "Mover ou redimensionar a área mesmo durante a gravação"
            )
        )

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        child = self.childAt(
            event.position().toPoint()
        )

        if isinstance(child, QPushButton):
            return

        self._drag_origin = (
            event.globalPosition().toPoint()
        )
        self._window_origin = self.pos()
        event.accept()

    def mouseMoveEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if (
            self._drag_origin is None
            or not (
                event.buttons()
                & Qt.MouseButton.LeftButton
            )
        ):
            return

        delta = (
            event.globalPosition().toPoint()
            - self._drag_origin
        )
        self.move(
            self._window_origin + delta
        )
        event.accept()

    def mouseReleaseEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)
