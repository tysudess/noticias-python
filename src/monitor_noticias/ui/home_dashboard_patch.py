from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.sections import Section


_INSTALLED = False


def _norm(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _all_texts(widget: QWidget) -> list[str]:
    texts: list[str] = []

    for label in widget.findChildren(QLabel):
        value = _norm(label.text())
        if value:
            texts.append(value)

    for button in widget.findChildren(QAbstractButton):
        value = _norm(button.text())
        if value:
            texts.append(value)

    return texts


def _find_first_label(root: QWidget, *options: str) -> QLabel | None:
    wanted = {_norm(item) for item in options if item}

    for label in root.findChildren(QLabel):
        if _norm(label.text()) in wanted:
            return label

    return None


def _card_ancestor(child: QWidget | None, root: QWidget) -> QWidget | None:
    current = child

    while current is not None and current is not root:
        parent = current.parentWidget()

        if parent is root:
            return current

        if isinstance(current, (QFrame, QGroupBox)) and current.layout() is not None:
            texts = _all_texts(current)
            if len(texts) >= 2:
                return current

        current = parent

    return None


def _top_level_child_cards(root: QWidget) -> list[QWidget]:
    return [child for child in root.findChildren(QWidget) if child.parentWidget() is root]


def _find_card_by_heading(root: QWidget, *headings: str) -> QWidget | None:
    label = _find_first_label(root, *headings)
    if label is not None:
        card = _card_ancestor(label, root)
        if card is not None:
            return card

    wanted = {_norm(item) for item in headings if item}
    for candidate in _top_level_child_cards(root):
        texts = _all_texts(candidate)
        if any(text in wanted for text in texts):
            return candidate
    return None


def _font_point_size(widget: QWidget) -> float:
    font = widget.font()
    size = float(font.pointSizeF())
    if size <= 0:
        size = float(font.pointSize())
    if size <= 0:
        size = 10.0
    return size


def _set_point_size(widget: QWidget, size: float, bold: bool | None = None) -> None:
    font = widget.font()
    font.setPointSizeF(float(size))
    if bold is not None:
        font.setBold(bool(bold))
    widget.setFont(font)


def _enlarge_home_fonts(page: QWidget) -> None:
    title_tokens = {
        "monitoramento",
        "ações rápidas",
        "acoes rápidas",
        "ações rapidas",
        "acoes rapidas",
        "agendamento automático",
        "agendamento automatico",
        "top 10 veículos",
        "top 10 veiculos",
        "últimas atividades",
        "ultimas atividades",
        "dicas",
        "notícias 24h",
        "videos armazenados",
        "vídeos armazenados",
        "videos hoje",
        "vídeos hoje",
        "demandas",
        "fontes",
        "status: pronto",
    }

    for label in page.findChildren(QLabel):
        text = _norm(label.text())
        size = _font_point_size(label)
        if not text:
            continue

        if text in title_tokens:
            if size < 15.8:
                _set_point_size(label, 16.2, bold=True)
            continue

        if text == "início" or text == "inicio":
            _set_point_size(label, 24, bold=True)
            continue

        if size < 10.0:
            _set_point_size(label, 10.9)
        elif size < 11.0:
            _set_point_size(label, 11.4)

    for button in page.findChildren(QAbstractButton):
        size = _font_point_size(button)
        text = _norm(button.text())
        if not text:
            continue
        if size < 11.6:
            _set_point_size(button, 12.0, bold=True)
        if button.minimumHeight() < 42:
            button.setMinimumHeight(42)


def _replace_monitoring_title(page: QWidget) -> None:
    label = _find_first_label(page, "central pronta para monitorar", "monitoramento")
    if label is None:
        return
    label.setText("Monitoramento")
    _set_point_size(label, 18.5, bold=True)


def _hide_card(page: QWidget, *headings: str) -> QWidget | None:
    card = _find_card_by_heading(page, *headings)
    if card is None:
        return None

    card.hide()
    card.setVisible(False)

    parent = card.parentWidget()
    layout = parent.layout() if parent else None
    if isinstance(layout, (QGridLayout, QVBoxLayout)):
        try:
            layout.invalidate()
        except Exception:
            pass

    return card


def _expand_card_across_grid(card: QWidget | None) -> None:
    if card is None:
        return
    parent = card.parentWidget()
    if parent is None:
        return
    layout = parent.layout()
    if isinstance(layout, QGridLayout):
        index = layout.indexOf(card)
        if index >= 0:
            row, _col, row_span, _col_span = layout.getItemPosition(index)
            total_columns = max(2, layout.columnCount())
            layout.addWidget(card, row, 0, row_span, total_columns)
            for column in range(total_columns):
                try:
                    layout.setColumnStretch(column, 1)
                except Exception:
                    pass
        layout.invalidate()

    card.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )


def _expand_schedule_card(page: QWidget) -> None:
    schedule = _find_card_by_heading(page, "agendamento automático", "agendamento automatico")
    _expand_card_across_grid(schedule)


def _hide_monitor_placeholder(page: QWidget) -> None:
    card = _find_card_by_heading(page, "monitoramento", "central pronta para monitorar")
    if card is None:
        return

    keep_tokens = {
        "monitoramento",
        "status: pronto",
        "status",
        "pronto",
        "busca atual",
        "nenhuma busca em andamento.",
        "nenhuma busca em andamento",
        "monitoramento ativo e funcionando normalmente.",
        "monitoramento ativo e funcionando normalmente",
    }

    best_candidate: QWidget | None = None
    best_area = 0

    for widget in card.findChildren(QWidget):
        if widget is card:
            continue
        parent = widget.parentWidget()
        if parent is None:
            continue
        if parent is not card and parent.parentWidget() is not card:
            continue
        texts = _all_texts(widget)
        if any(text in keep_tokens for text in texts):
            continue
        if widget.findChildren(QAbstractButton):
            continue
        geometry = widget.geometry()
        area = max(0, geometry.width()) * max(0, geometry.height())
        if area >= 25000 and area > best_area:
            best_candidate = widget
            best_area = area

    if best_candidate is not None:
        best_candidate.hide()
        best_candidate.setVisible(False)
        parent = best_candidate.parentWidget()
        layout = parent.layout() if parent else None
        if layout is not None:
            try:
                layout.invalidate()
            except Exception:
                pass

    for widget in card.findChildren(QWidget):
        texts = _all_texts(widget)
        if any(text in keep_tokens for text in texts):
            widget.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )


def _tune_status_box(page: QWidget) -> None:
    status_label = _find_first_label(page, "status: pronto")
    if status_label is None:
        return

    _set_point_size(status_label, 14.4, bold=True)
    parent = status_label.parentWidget()
    if parent is not None:
        for label in parent.findChildren(QLabel):
            text = _norm(label.text())
            if text and text != "status: pronto" and _font_point_size(label) < 11.2:
                _set_point_size(label, 11.3)


def _reflow_bottom_cards(page: QWidget) -> None:
    activities = _find_card_by_heading(page, "últimas atividades", "ultimas atividades")
    top10 = _find_card_by_heading(page, "top 10 veículos", "top 10 veiculos")
    tips = _find_card_by_heading(page, "dicas")

    _hide_card(page, "dicas")

    if activities is None:
        return

    parent = activities.parentWidget()
    if parent is None:
        return
    layout = parent.layout()
    if not isinstance(layout, QGridLayout):
        activities.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        return

    index_activities = layout.indexOf(activities)
    if index_activities < 0:
        return

    row_a, col_a, row_span_a, _col_span_a = layout.getItemPosition(index_activities)
    total_columns = max(2, layout.columnCount())

    if top10 is not None:
        index_top = layout.indexOf(top10)
        if index_top >= 0:
            row_t, col_t, row_span_t, col_span_t = layout.getItemPosition(index_top)
            if row_t == row_a:
                start_col = min(col_a, col_t)
                if start_col == col_t:
                    span = max(1, total_columns - col_t - col_span_t)
                    layout.addWidget(activities, row_a, col_t + col_span_t, row_span_a, span)
                    activities.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Preferred,
                    )
                    layout.invalidate()
                    return

    # fallback: deixa atividades ocupar a linha toda
    layout.addWidget(activities, row_a, 0, row_span_a, total_columns)
    activities.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )
    layout.invalidate()


def _apply_home_dashboard(window: QWidget) -> None:
    pages = getattr(window, "pages", None)
    if not isinstance(pages, dict):
        return

    page = pages.get(Section.HOME)
    if page is None:
        return

    _replace_monitoring_title(page)
    _enlarge_home_fonts(page)
    _hide_card(page, "resumo do dia")
    _expand_schedule_card(page)
    _hide_monitor_placeholder(page)
    _tune_status_box(page)
    _reflow_bottom_cards(page)

    try:
        page.updateGeometry()
        page.update()
    except Exception:
        pass


def install_home_dashboard_patch(window: QWidget) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    for delay in (0, 150, 600, 1200):
        QTimer.singleShot(delay, lambda w=window: _apply_home_dashboard(w))
