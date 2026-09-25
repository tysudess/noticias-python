from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import (
    QComboBox,
    QListWidget,
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from monitor_noticias.ui.sections import Section


_SOURCE_NAME = "Tribuna da Bahia"
_MARKERS = {
    "bahia",
    "a tarde",
    "bahia notícias",
    "bahia noticias",
    "correio",
    "correio da bahia",
    "aratu",
}


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _texts_from_widget(widget: QWidget) -> list[str]:
    texts: list[str] = []

    if isinstance(widget, QComboBox):
        for index in range(widget.count()):
            texts.append(_norm(widget.itemText(index)))

    elif isinstance(widget, QListWidget):
        for index in range(widget.count()):
            item = widget.item(index)
            if item is not None:
                texts.append(_norm(item.text()))

    elif isinstance(widget, QTreeWidget):
        for index in range(widget.topLevelItemCount()):
            item = widget.topLevelItem(index)
            if item is not None:
                texts.append(_norm(item.text(0)))

    elif isinstance(widget, QTableWidget):
        rows = widget.rowCount()
        cols = widget.columnCount()
        for row in range(rows):
            for col in range(min(cols, 2)):
                item = widget.item(row, col)
                if item is not None:
                    texts.append(_norm(item.text()))

    model = getattr(widget, "model", None)
    if callable(model):
        try:
            model_obj = model()
        except Exception:
            model_obj = None
        if model_obj is not None:
            rows = getattr(model_obj, "rowCount", lambda: 0)()
            for row in range(rows):
                try:
                    index = model_obj.index(row, 0)
                    value = model_obj.data(index)
                    if value:
                        texts.append(_norm(value))
                except Exception:
                    pass

    return texts


def _looks_like_bahia_collection(texts: list[str]) -> bool:
    joined = " | ".join(texts)
    return any(marker in joined for marker in _MARKERS)


def _contains_source(texts: list[str]) -> bool:
    source_norm = _norm(_SOURCE_NAME)
    return any(source_norm == text for text in texts)


def _add_to_widget(widget: QWidget) -> bool:
    texts = _texts_from_widget(widget)
    if not texts or not _looks_like_bahia_collection(texts) or _contains_source(texts):
        return False

    try:
        if isinstance(widget, QComboBox):
            widget.addItem(_SOURCE_NAME)
            return True

        if isinstance(widget, QListWidget):
            widget.addItem(_SOURCE_NAME)
            return True

        if isinstance(widget, QTreeWidget):
            widget.addTopLevelItem(QTreeWidgetItem([_SOURCE_NAME]))
            return True

        if isinstance(widget, QTableWidget):
            row = widget.rowCount()
            widget.insertRow(row)
            from PySide6.QtWidgets import QTableWidgetItem
            widget.setItem(row, 0, QTableWidgetItem(_SOURCE_NAME))
            return True

        model_fn = getattr(widget, "model", None)
        if callable(model_fn):
            model = model_fn()
            append_row = getattr(model, "appendRow", None)
            if callable(append_row):
                append_row(QStandardItem(_SOURCE_NAME))
                return True
    except Exception:
        return False

    return False


def _apply(window: QWidget) -> None:
    pages = getattr(window, "pages", None)
    if not isinstance(pages, dict):
        return

    page = pages.get(Section.SOURCES)
    if page is None:
        return

    # Tenta coleções comuns da aba Fontes.
    added = False
    for widget_type in (QComboBox, QListWidget, QTreeWidget, QTableWidget):
        for widget in page.findChildren(widget_type):
            added = _add_to_widget(widget) or added

    # Fallback: tenta qualquer widget com model().
    if not added:
        for widget in page.findChildren(QWidget):
            if hasattr(widget, "model"):
                added = _add_to_widget(widget) or added

    try:
        page.updateGeometry()
        page.update()
    except Exception:
        pass


def install_sources_bahia_patch(window: QWidget) -> None:
    for delay in (0, 300, 900, 1500):
        QTimer.singleShot(delay, lambda w=window: _apply(w))
