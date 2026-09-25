from __future__ import annotations

from PySide6.QtCore import (
    QEvent,
    QObject,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QTabBar,
    QTableView,
    QTextEdit,
    QTreeView,
    QWidget,
)


_INSTALLED = False
_POLISHER = None

_NAV_TEXTS = {
    "início",
    "inicio",
    "notícias",
    "noticias",
    "vídeos",
    "videos",
    "demandas",
    "fontes",
    "histórico",
    "historico",
    "termos",
    "parar buscas",
    "extrator de notícias",
    "extrator de noticias",
    "capas",
    "editor de pdf",
    "extrator de vídeos",
    "extrator de videos",
    "editor de vídeo",
    "editor de video",
    "gravador de tela",
    "configurações",
    "configuracoes",
}


GLOBAL_STYLESHEET = """
QWidget {
    color: #123264;
    selection-background-color: #2d8cff;
    selection-color: #ffffff;
}

QMainWindow, QDialog, QWidget#centralwidget {
    background: #eef4fb;
}

QToolTip {
    color: #123264;
    background: #ffffff;
    border: 1px solid #d7e4f3;
    border-radius: 10px;
    padding: 6px 10px;
}

QLabel {
    color: #123264;
}

QLabel[title="true"] {
    font-weight: 800;
    color: #08285d;
}

QFrame {
    border-radius: 18px;
}

QGroupBox {
    background: rgba(255,255,255,0.92);
    border: 1px solid #d7e4f3;
    border-radius: 20px;
    margin-top: 14px;
    padding: 18px 16px 16px 16px;
    font-weight: 700;
    color: #0d2f67;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px 0 6px;
}

QLineEdit,
QPlainTextEdit,
QTextEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox,
QAbstractSpinBox {
    background: rgba(255,255,255,0.98);
    color: #143566;
    border: 1px solid #d0deef;
    border-radius: 14px;
    padding: 10px 12px;
    selection-background-color: #2d8cff;
    selection-color: #ffffff;
}

QLineEdit:focus,
QPlainTextEdit:focus,
QTextEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QAbstractSpinBox:focus {
    border: 1px solid #4f9dff;
    background: #ffffff;
}

QLineEdit:disabled,
QPlainTextEdit:disabled,
QTextEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled,
QAbstractSpinBox:disabled {
    color: #7d93b6;
    background: #eef3f9;
}

QPushButton,
QToolButton {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #3397ff,
        stop:1 #1f7df0
    );
    color: #ffffff;
    border: 1px solid #1f77e8;
    border-radius: 14px;
    padding: 10px 16px;
    font-weight: 800;
    min-height: 20px;
}

QPushButton:hover,
QToolButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #49a4ff,
        stop:1 #2b87f5
    );
    border: 1px solid #247fe9;
}

QPushButton:pressed,
QToolButton:pressed {
    background: #176fe1;
    padding-top: 11px;
    padding-bottom: 9px;
}

QPushButton:disabled,
QToolButton:disabled {
    background: #dce7f4;
    color: #89a0c4;
    border: 1px solid #d2dfef;
}

QPushButton[secondary="true"],
QToolButton[secondary="true"] {
    background: rgba(255,255,255,0.98);
    color: #1653a5;
    border: 1px solid #cfe0f3;
}

QPushButton[secondary="true"]:hover,
QToolButton[secondary="true"]:hover {
    background: #f6fbff;
    border: 1px solid #b7d1f0;
}

QPushButton[nav="true"],
QToolButton[nav="true"] {
    background: rgba(255,255,255,0.08);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 14px;
    text-align: left;
    padding: 11px 14px;
    font-weight: 700;
}

QPushButton[nav="true"]:hover,
QToolButton[nav="true"]:hover {
    background: rgba(64, 160, 255, 0.22);
    border: 1px solid rgba(88, 180, 255, 0.35);
}

QPushButton[nav="true"][active="true"],
QToolButton[nav="true"][active="true"] {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(28,140,255,0.95),
        stop:1 rgba(15,104,224,0.95)
    );
    border: 1px solid rgba(104, 190, 255, 0.28);
}

QTabWidget::pane {
    border: 1px solid #d7e4f3;
    border-radius: 16px;
    top: -1px;
    background: rgba(255,255,255,0.90);
}

QTabBar::tab {
    background: rgba(255,255,255,0.84);
    color: #2a4d7d;
    border: 1px solid #d6e2ef;
    border-bottom: none;
    padding: 10px 18px;
    min-height: 18px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    margin-right: 6px;
    font-weight: 700;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #0c3a7a;
    border-color: #bfd6ef;
}

QTabBar::tab:hover:!selected {
    background: #f5faff;
}

QScrollArea, QListView, QTableView, QTreeView {
    background: rgba(255,255,255,0.88);
    alternate-background-color: #f7fbff;
    border: 1px solid #d8e4f1;
    border-radius: 16px;
    outline: none;
}

QHeaderView::section {
    background: #eef5fd;
    color: #173b6c;
    border: none;
    border-bottom: 1px solid #d7e3f2;
    padding: 10px 10px;
    font-weight: 800;
}

QMenu {
    background: #ffffff;
    border: 1px solid #d7e4f3;
    border-radius: 12px;
    padding: 8px;
}

QMenu::item {
    padding: 8px 14px;
    border-radius: 8px;
}

QMenu::item:selected {
    background: #edf6ff;
    color: #0f4f9d;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 8px 2px 8px 2px;
}

QScrollBar::handle:vertical {
    background: #c5d8ee;
    min-height: 32px;
    border-radius: 6px;
}

QScrollBar::handle:vertical:hover {
    background: #a8c4e5;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    border: none;
    height: 0px;
    width: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px 8px 2px 8px;
}

QScrollBar::handle:horizontal {
    background: #c5d8ee;
    min-width: 32px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal:hover {
    background: #a8c4e5;
}

QSplitter::handle {
    background: #d9e7f6;
}

QMessageBox {
    background: #eef4fb;
}
"""


class _VisualPolisher(QObject):
    def eventFilter(self, obj, event):
        if event.type() in {QEvent.Type.Show, QEvent.Type.Polish}:
            try:
                self._polish_widget(obj)
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def _polish_widget(self, obj) -> None:
        if not isinstance(obj, QWidget):
            return

        if isinstance(obj, QLabel):
            self._polish_label(obj)
        elif isinstance(obj, QAbstractButton):
            self._polish_button(obj)
        elif isinstance(obj, (QFrame, QGroupBox)):
            self._polish_card(obj)
        elif isinstance(obj, (QLineEdit, QTextEdit, QPlainTextEdit)):
            self._polish_text_input(obj)
        elif isinstance(obj, (QComboBox, QSpinBox, QDoubleSpinBox)):
            self._polish_text_input(obj)
        elif isinstance(obj, (QListView, QTableView, QTreeView, QScrollArea)):
            self._polish_card(obj)

    def _set_shadow(self, widget: QWidget, blur: float = 22.0, offset_y: float = 4.0, alpha: int = 42) -> None:
        effect = widget.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            return
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(float(blur))
        shadow.setOffset(0.0, float(offset_y))
        shadow.setColor(QColor(31, 79, 151, alpha))
        widget.setGraphicsEffect(shadow)

    def _polish_label(self, label: QLabel) -> None:
        text = " ".join(label.text().strip().lower().split())
        font = label.font()
        size = font.pointSizeF() or float(font.pointSize() or 10)

        if text in {
            "início", "inicio", "notícias", "noticias", "videos", "vídeos",
            "fontes", "demandas", "capas", "editor de pdf", "extrator de vídeos",
            "extrator de videos", "editor de vídeo", "editor de video", "histórico",
            "historico", "configurações", "configuracoes", "monitoramento",
            "ações rápidas", "acoes rápidas", "ações rapidas", "acoes rapidas",
            "agendamento automático", "agendamento automatico", "top 10 veículos",
            "top 10 veiculos", "últimas atividades", "ultimas atividades", "dicas",
        }:
            if size < 15.5:
                font.setPointSizeF(15.8)
            font.setBold(True)
            label.setProperty("title", True)
            label.setFont(font)
            return

        if size < 10:
            font.setPointSizeF(10.6)
            label.setFont(font)

    def _looks_like_nav_button(self, button: QAbstractButton) -> bool:
        text = " ".join(button.text().strip().lower().split())
        if text not in _NAV_TEXTS:
            return False
        parent = button.parentWidget()
        if parent is None:
            return True
        width = max(button.width(), button.minimumWidth(), parent.width())
        return width <= 260 or button.x() < 260

    def _polish_button(self, button: QAbstractButton) -> None:
        text = button.text().strip()
        low = " ".join(text.lower().split())
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        font = button.font()
        size = font.pointSizeF() or float(font.pointSize() or 10)
        if size < 10.8:
            font.setPointSizeF(10.9)
        font.setBold(True)
        button.setFont(font)

        if self._looks_like_nav_button(button):
            button.setProperty("nav", True)
            if button.minimumHeight() < 38:
                button.setMinimumHeight(40)
            button.style().unpolish(button)
            button.style().polish(button)
            return

        if button.minimumHeight() < 38:
            button.setMinimumHeight(40)

        if button.minimumWidth() and button.minimumWidth() < 110:
            button.setMinimumWidth(110)

        if any(token in low for token in ("abrir", "ver ", "voltar", "desmarcar", "copiar", "config", "log", "pasta", "histor")) and not any(token in low for token in ("buscar", "iniciar", "gerar", "atualizar", "salvar", "aplicar")):
            button.setProperty("secondary", True)
            button.style().unpolish(button)
            button.style().polish(button)

        self._set_shadow(button, blur=18.0, offset_y=3.0, alpha=34)

    def _polish_card(self, widget: QWidget) -> None:
        area = max(widget.width(), widget.minimumWidth()) * max(widget.height(), widget.minimumHeight())
        if area < 12000 and not isinstance(widget, QGroupBox):
            return
        widget.setAutoFillBackground(False)
        self._set_shadow(widget, blur=26.0, offset_y=4.0, alpha=30)

    def _polish_text_input(self, widget: QWidget) -> None:
        font = widget.font()
        size = font.pointSizeF() or float(font.pointSize() or 10)
        if size < 10.9:
            font.setPointSizeF(10.9)
            widget.setFont(font)


def _set_app_font(app: QApplication) -> None:
    font = QFont()
    font.setFamilies(["Segoe UI", "Inter", "Arial", "Ubuntu", "Sans Serif"])
    font.setPointSizeF(10.7)
    app.setFont(font)


def _walk_and_polish(window: QWidget) -> None:
    if _POLISHER is None:
        return
    _POLISHER._polish_widget(window)
    for child in window.findChildren(QWidget):
        try:
            _POLISHER._polish_widget(child)
        except Exception:
            pass


def install_visual_refinement_patch(app: QApplication, window: QWidget) -> None:
    global _INSTALLED, _POLISHER
    if _INSTALLED:
        return

    _INSTALLED = True
    _set_app_font(app)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    _POLISHER = _VisualPolisher(app)
    app.installEventFilter(_POLISHER)

    for delay in (0, 120, 600, 1200):
        QTimer.singleShot(delay, lambda w=window: _walk_and_polish(w))
