from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .core import Clip, format_time, total_duration

BG = "#07111f"
BORDER = "#243650"
TEXT = "#f1f5ff"
MUTED = "#a8b4c7"
FADED = "#66758d"
BLUE = "#168fff"
BLUE_2 = "#37a6ff"


class TimelineWidget(QWidget):
    """Timeline visual equivalente ao widget do editor PySide6 aprovado.

    Não implementa zoom, drag de clips, thumbnails ou split porque esses recursos
    não existem no motor ativo da release V8 analisada.
    """

    seekRequested = Signal(int)
    clipSelected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.clips: list[Clip] = []
        self.playhead_ms = 0
        self.selected_index = -1
        self.pixels_per_second = 8.0
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def total_duration(self) -> int:
        return total_duration(self.clips)

    def set_clips(self, clips: Sequence[Clip]) -> None:
        self.clips = list(clips)
        self.updateGeometry()
        self.update()

    def set_playhead(self, ms: int) -> None:
        self.playhead_ms = max(0, min(int(ms), max(0, self.total_duration())))
        self.update()

    def set_selected(self, index: int) -> None:
        self.selected_index = index
        self.update()

    def _timeline_rect(self) -> QRectF:
        return QRectF(170, 35, max(650, self.width() - 190), 100)

    def _x_for_time(self, ms: int) -> float:
        rect = self._timeline_rect()
        total = max(1, self.total_duration())
        return rect.left() + rect.width() * (ms / total)

    def _time_for_x(self, x: float) -> int:
        rect = self._timeline_rect()
        total = max(1, self.total_duration())
        fraction = (x - rect.left()) / max(1.0, rect.width())
        return int(max(0.0, min(1.0, fraction)) * total)

    def _clip_at(self, x: float, y: float) -> int:
        if not self.clips:
            return -1
        rect = self._timeline_rect()
        if not (rect.left() <= x <= rect.right() and 48 <= y <= 92):
            return -1
        total = max(1, self.total_duration())
        cursor = rect.left()
        for index, clip in enumerate(self.clips):
            width = rect.width() * (clip.duration_ms / total)
            if cursor <= x <= cursor + width:
                return index
            cursor += width
        return -1

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG))

        rect = self._timeline_rect()
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(QBrush(QColor("#0a1320")))
        painter.drawRoundedRect(rect, 4, 4)

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(MUTED))
        painter.drawText(18, 64, "▭  Vídeo 1")
        painter.drawText(18, 110, "♫  Áudio 1")

        total = max(1, self.total_duration())
        marks = 6 if total > 60000 else 5
        for i in range(marks + 1):
            t = int(total * i / max(1, marks))
            x = self._x_for_time(t)
            painter.setPen(QPen(QColor(BORDER), 1))
            painter.drawLine(int(x), 27, int(x), 135)
            painter.setPen(QColor(MUTED))
            painter.drawText(int(x) + 4, 25, format_time(t))

        if self.clips:
            cursor = rect.left()
            for index, clip in enumerate(self.clips):
                width = max(28.0, rect.width() * (clip.duration_ms / total))
                video_rect = QRectF(cursor + 3, 50, width - 6, 36)
                audio_rect = QRectF(cursor + 3, 96, width - 6, 28)
                selected = index == self.selected_index
                painter.setPen(QPen(QColor(BLUE_2 if selected else BORDER), 2 if selected else 1))
                painter.setBrush(QBrush(QColor(BLUE if selected else "#123d6a")))
                painter.drawRoundedRect(video_rect, 4, 4)
                painter.setPen(QColor(TEXT))
                painter.drawText(
                    video_rect.adjusted(8, 0, -8, 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    f"{index + 1}. {clip.path.name}",
                )

                painter.setPen(QPen(QColor("#0b777b"), 1))
                painter.setBrush(QBrush(QColor(0, 160, 170, 65)))
                painter.drawRoundedRect(audio_rect, 4, 4)
                painter.setPen(QColor(MUTED))
                painter.drawText(
                    audio_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    "Áudio original" if clip.info.has_audio else "Sem áudio",
                )
                cursor += width
        else:
            painter.setPen(QColor(FADED))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Adicione vídeos para aparecerem na timeline")

        play_x = self._x_for_time(self.playhead_ms)
        painter.setPen(QPen(QColor(BLUE_2), 3))
        painter.drawLine(int(play_x), 35, int(play_x), 140)
        painter.setBrush(QBrush(QColor(BLUE_2)))
        painter.drawRoundedRect(QRectF(play_x - 4, 32, 8, 9), 3, 3)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        x = float(event.position().x())
        y = float(event.position().y())
        index = self._clip_at(x, y)
        if index >= 0:
            self.selected_index = index
            self.clipSelected.emit(index)
        self.seekRequested.emit(self._time_for_x(x))
        self.update()
