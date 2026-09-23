from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QTimer, Qt
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


def _find_first_label(
    root: QWidget,
    *options: str,
) -> QLabel | None:
    wanted = {_norm(item) for item in options if item}

    for label in root.findChildren(QLabel):
        if _norm(label.text()) in wanted:
            return label

    return None


def _card_ancestor(
    child: QWidget | None,
    root: QWidget,
) -> QWidget | None:
    current = child

    while current is not None and current is not root:
        parent = current.parentWidget()

        if parent is root:
            return current

        layout = current.layout()

        if isinstance(current, (QFrame, QGroupBox)) and layout is not None:
            texts = _all_texts(current)

            if len(texts) >= 2:
                return current

        current = parent

    return None


def _top_level_child_cards(root: QWidget) -> list[QWidget]:
    result: list[QWidget] = []

    for child in root.findChildren(QWidget):
        if child.parentWidget() is root:
            result.append(child)

    return result


def _find_card_by_heading(
    root: QWidget,
    *headings: str,
) -> QWidget | None:
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


def _set_point_size(
    widget: QWidget,
    size: float,
    bold: bool | None = None,
) -> None:
    font = widget.font()
    font.setPointSizeF(float(size))

    if bold is not None:
        font.setBold(bool(bold))

    widget.setFont(font)


def _enlarge_home_fonts(page: QWidget) -> None:
    # Títulos dos cards e seções.
    for label in page.findChildren(QLabel):
        text = _norm(label.text())
        size = _font_point_size(label)

        if not text:
            continue

        if text in {
            "monitoramento",
            "central pronta para monitorar",
            "ações rápidas",
            "agendamento automático",
            "top 10 veículos",
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
        }:
            if size < 15:
                _set_point_size(label, 15, bold=True)
            continue

        # Subtítulos e textos informativos pequenos.
        if size < 9.8:
            _set_point_size(label, 10.8)
        elif size < 11:
            _set_point_size(label, 11.2)

    for button in page.findChildren(QAbstractButton):
        size = _font_point_size(button)
        text = _norm(button.text())

        if not text:
            continue

        if size < 11.5:
            _set_point_size(button, 11.8, bold=True)

    # Ajuste do texto de busca no topo da Home, se estiver dentro da página.
    for candidate in page.findChildren(QWidget):
        if hasattr(candidate, "placeholderText"):
            try:
                font = candidate.font()
                size = float(font.pointSizeF() or font.pointSize() or 10.0)
                if size < 11:
                    font.setPointSizeF(11.0)
                    candidate.setFont(font)
            except Exception:
                pass


def _replace_monitoring_title(page: QWidget) -> None:
    label = _find_first_label(
        page,
        "central pronta para monitorar",
        "monitoramento",
    )

    if label is None:
        return

    label.setText("Monitoramento")
    _set_point_size(label, 18, bold=True)


def _hide_summary_card(page: QWidget) -> None:
    card = _find_card_by_heading(
        page,
        "resumo do dia",
    )

    if card is None:
        return

    card.hide()
    card.setVisible(False)

    parent = card.parentWidget()
    layout = parent.layout() if parent else None

    if isinstance(layout, (QGridLayout, QVBoxLayout)):
        try:
            layout.invalidate()
        except Exception:
            pass


def _expand_schedule_card(page: QWidget) -> None:
    schedule = _find_card_by_heading(
        page,
        "agendamento automático",
    )

    if schedule is None:
        return

    schedule.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Preferred,
    )

    parent = schedule.parentWidget()
    if parent is None:
        return

    layout = parent.layout()

    if isinstance(layout, QGridLayout):
        index = layout.indexOf(schedule)

        if index >= 0:
            row, col, row_span, col_span = layout.getItemPosition(index)

            # Faz o card ocupar a largura da linha inteira.
            total_columns = max(
                2,
                layout.columnCount(),
            )

            layout.addWidget(
                schedule,
                row,
                0,
                row_span,
                total_columns,
            )

            for column in range(total_columns):
                try:
                    layout.setColumnStretch(column, 1)
                except Exception:
                    pass

        layout.invalidate()


def _hide_monitor_placeholder(page: QWidget) -> None:
    card = _find_card_by_heading(
        page,
        "monitoramento",
        "central pronta para monitorar",
    )

    if card is None:
        return

    keep_tokens = {
        "monitoramento",
        "central pronta para monitorar",
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

        if widget.parentWidget() is None:
            continue

        if widget.parentWidget() is not card and widget.parentWidget().parentWidget() is not card:
            continue

        texts = _all_texts(widget)

        if any(text in keep_tokens for text in texts):
            continue

        # Ignora botões e controles reais.
        if widget.findChildren(QAbstractButton):
            continue

        geometry = widget.geometry()
        area = max(0, geometry.width()) * max(0, geometry.height())

        # Procuramos a maior área ilustrativa vazia.
        if area >= 30000:
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

    # Como reforço, aumentamos a largura dos blocos informativos restantes.
    for widget in card.findChildren(QWidget):
        texts = _all_texts(widget)

        if any(text in keep_tokens for text in texts):
            widget.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )


def _tune_status_box(page: QWidget) -> None:
    status_label = _find_first_label(
        page,
        "status: pronto",
    )

    if status_label is None:
        return

    _set_point_size(status_label, 14, bold=True)

    parent = status_label.parentWidget()
    if parent is not None:
        for label in parent.findChildren(QLabel):
            text = _norm(label.text())
            if text and text != "status: pronto":
                if _font_point_size(label) < 11:
                    _set_point_size(label, 11.2)


def _apply_home_dashboard(window: QWidget) -> None:
    pages = getattr(window, "pages", None)

    if not isinstance(pages, dict):
        return

    page = pages.get(Section.HOME)

    if page is None:
        return

    _replace_monitoring_title(page)
    _enlarge_home_fonts(page)
    _hide_summary_card(page)
    _expand_schedule_card(page)
    _hide_monitor_placeholder(page)
    _tune_status_box(page)

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

    # Reaplicações leves para pegar widgets criados um pouco depois.
    for delay in (0, 150, 600):
        QTimer.singleShot(
            delay,
            lambda w=window: _apply_home_dashboard(w),
        )
