from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class RangeSlider(QWidget):
    """Linha do tempo com três controles independentes.

    - alça esquerda: início do corte;
    - alça direita: fim do corte;
    - marcador triangular/linha: posição atual (playhead).

    Clicar fora das alças de início/fim movimenta somente o playhead.
    Assim a reprodução pode ser navegada sem alterar o intervalo de corte.
    """

    valuesChanged = Signal(int, int)
    handleReleased = Signal(int, int)
    handleMoved = Signal(str, int)
    positionChanged = Signal(int)
    positionReleased = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = 0
        self._maximum = 1000
        self._start = 0
        self._end = 1000
        self._position = 0
        self._drag = None
        self._margin = 18
        self._handle_radius = 8
        self._hit_radius = 13
        self._minimum_span = 1
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            'Arraste as bolinhas para alterar início/fim. '
            'Clique ou arraste em outro ponto da linha para mover somente a posição do vídeo.'
        )

    def setRange(self, minimum, maximum):
        self._minimum = int(minimum)
        self._maximum = max(self._minimum + 1, int(maximum))
        self._start = max(self._minimum, min(self._start, self._maximum))
        self._end = max(self._start + self._minimum_span, min(self._end, self._maximum))
        self._position = max(self._minimum, min(self._position, self._maximum))
        self.update()

    def setValues(self, start, end, emit=True):
        start = max(self._minimum, min(int(start), self._maximum))
        end = max(self._minimum, min(int(end), self._maximum))
        if end < start + self._minimum_span:
            end = min(self._maximum, start + self._minimum_span)
            if end < start + self._minimum_span:
                start = max(self._minimum, end - self._minimum_span)
        self._start, self._end = start, end
        self.update()
        if emit:
            self.valuesChanged.emit(self._start, self._end)

    def values(self):
        return self._start, self._end

    def setPosition(self, value, emit=False):
        self._position = max(self._minimum, min(int(value), self._maximum))
        self.update()
        if emit:
            self.positionChanged.emit(self._position)

    def position(self):
        return self._position

    def _track_rect(self):
        y = self.height() / 2 + 1
        return QRectF(self._margin, y - 3, max(1, self.width() - 2 * self._margin), 6)

    def _x_for_value(self, value):
        rect = self._track_rect()
        span = max(1, self._maximum - self._minimum)
        ratio = (value - self._minimum) / span
        return rect.left() + rect.width() * ratio

    def _value_for_x(self, x):
        rect = self._track_rect()
        ratio = (x - rect.left()) / max(1.0, rect.width())
        ratio = max(0.0, min(1.0, ratio))
        return int(round(self._minimum + ratio * (self._maximum - self._minimum)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._track_rect()
        pal = self.palette()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pal.mid())
        painter.drawRoundedRect(rect, 3, 3)

        x1 = self._x_for_value(self._start)
        x2 = self._x_for_value(self._end)
        selected = QRectF(x1, rect.top(), max(1, x2 - x1), rect.height())
        painter.setBrush(pal.highlight())
        painter.drawRoundedRect(selected, 3, 3)

        # Playhead: linha + triângulo. É independente das alças de corte.
        pos_x = self._x_for_value(self._position)
        painter.setPen(QPen(pal.text().color(), 2))
        painter.drawLine(int(pos_x), int(rect.top() - 11), int(pos_x), int(rect.bottom() + 10))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pal.text())
        triangle = QPolygonF([
            QPointF(pos_x - 5, rect.top() - 12),
            QPointF(pos_x + 5, rect.top() - 12),
            QPointF(pos_x, rect.top() - 5),
        ])
        painter.drawPolygon(triangle)

        # Início/fim: círculos destacados.
        painter.setBrush(pal.highlight())
        for x in (x1, x2):
            painter.drawEllipse(QRectF(
                x - self._handle_radius,
                self.height() / 2 + 1 - self._handle_radius,
                self._handle_radius * 2,
                self._handle_radius * 2,
            ))

    def mousePressEvent(self, event):
        x = event.position().x()
        xs = self._x_for_value(self._start)
        xe = self._x_for_value(self._end)

        # Só move início/fim quando o clique realmente atinge a alça.
        if abs(x - xs) <= self._hit_radius and abs(x - xs) <= abs(x - xe):
            self._drag = 'start'
        elif abs(x - xe) <= self._hit_radius:
            self._drag = 'end'
        else:
            self._drag = 'position'

        self._move_active(x)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag:
            self._move_active(event.position().x())
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag:
            drag = self._drag
            self._move_active(event.position().x())
            self._drag = None
            if drag in ('start', 'end'):
                self.handleReleased.emit(self._start, self._end)
            else:
                self.positionReleased.emit(self._position)
            event.accept()

    def _move_active(self, x):
        value = self._value_for_x(x)
        if self._drag == 'start':
            self._start = min(value, self._end - self._minimum_span)
            self._start = max(self._minimum, self._start)
            self.update()
            self.valuesChanged.emit(self._start, self._end)
            self.handleMoved.emit('start', self._start)
        elif self._drag == 'end':
            self._end = max(value, self._start + self._minimum_span)
            self._end = min(self._maximum, self._end)
            self.update()
            self.valuesChanged.emit(self._start, self._end)
            self.handleMoved.emit('end', self._end)
        elif self._drag == 'position':
            self._position = max(self._minimum, min(value, self._maximum))
            self.update()
            self.positionChanged.emit(self._position)
