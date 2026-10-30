from __future__ import annotations

"""V127 — contorno dourado uniforme dos cards e das abas da Central Windows."""

import re

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QPushButton,
    QTabBar,
    QTabWidget,
    QWidget,
)

GOLD_BORDER = "#C6A15B"
_RULES_MARKER = "CENTRAL GOLD OUTLINES V127"
_WIDGET_MARKER_PROPERTY = "_central_gold_outline_v127"

# Os nomes representam painéis/cartões existentes nas páginas reais da Central.
# As cores de preenchimento, os textos, os espaçamentos e os raios continuam
# definidos pelos estilos que cada página já possui.
_CARD_OBJECT_NAMES = frozenset({
    "card", "topCard", "statusCard", "metricCard", "successCard", "dangerCard",
    "heroCard", "homeCard", "quickCard", "tipCard", "readyCard", "scheduleBox",
    "rankRow", "newsBanner", "newsCard", "customPeriod", "videoTop",
    "videoProgressCard", "videoCustom", "videoSuccess", "videoItem",
    "demandHero", "demandCard", "demandStatus", "demandItem", "demandResults",
    "extractorHero", "extractorCard", "extractorStatusCard", "extractorStack",
    "pdfSideTools", "pdfMainCard", "pdfExportCard", "pdfPreview", "pdfThumbs",
    "header", "settingsHero", "settingsCard", "settingsService", "extractCard",
    "statusCardNative", "termCard", "termList", "sourcesTop", "sourcesControl",
    "sourceStateCard", "sourceListView", "historyTop", "historyListView",
    "sidebarStatusCard", "sidebarNavItem", "monitorPanel", "statusPanel",
})

# Regras appendadas ao stylesheet de cada página. Isso é importante porque
# diversas telas possuem QSS próprio e prevalecem sobre o stylesheet da janela.
GOLD_BORDER_QSS = f"""
/* {_RULES_MARKER}: somente contornos; não altera layout nem preenchimentos. */
QFrame#card, QFrame#topCard, QFrame#statusCard,
QFrame#metricCard, QFrame#successCard, QFrame#dangerCard,
QFrame#heroCard, QFrame#homeCard, QFrame#quickCard, QFrame#tipCard,
QFrame#readyCard, QFrame#scheduleBox, QFrame#rankRow,
QFrame#newsBanner, QFrame#newsCard, QFrame#customPeriod,
QFrame#videoTop, QFrame#videoProgressCard, QFrame#videoCustom,
QFrame#videoSuccess, QFrame#videoItem,
QFrame#demandHero, QFrame#demandCard, QFrame#demandStatus,
QFrame#demandItem, QFrame#demandResults,
QFrame#extractorHero, QFrame#extractorCard, QFrame#extractorStatusCard,
QStackedWidget#extractorStack,
QFrame#pdfSideTools, QFrame#pdfMainCard, QFrame#pdfExportCard,
QLabel#pdfPreview, QListWidget#pdfThumbs,
QFrame#header, QFrame#settingsHero, QFrame#settingsCard,
QFrame#settingsService, QFrame#extractCard, QFrame#statusCardNative,
QFrame#termCard, QListWidget#termList,
QFrame#sourcesTop, QFrame#sourcesControl, QFrame#sourceStateCard,
QListView#sourceListView, QFrame#historyTop, QListView#historyListView,
QFrame#sidebarStatusCard, QFrame#sidebarNavItem,
QFrame#monitorPanel, QFrame#statusPanel {{
    border: 1px solid {GOLD_BORDER};
}}

QFrame#sidebarNavItem:hover,
QFrame#sidebarNavItem[active="true"] {{
    border: 1px solid {GOLD_BORDER};
}}

QTabWidget::pane {{
    border: 1px solid {GOLD_BORDER};
}}
QTabBar::tab, QTabBar#extractorTabs::tab {{
    border: 1px solid {GOLD_BORDER};
    border-bottom: 1px solid {GOLD_BORDER};
}}
QTabBar::tab:selected, QTabBar#extractorTabs::tab:selected {{
    border: 1px solid {GOLD_BORDER};
}}
QGroupBox {{
    border: 1px solid {GOLD_BORDER};
}}
QPushButton#sourceTabButton, QPushButton#historyTab {{
    border: 1px solid {GOLD_BORDER};
}}
"""

_CARD_NAME_TOKENS = (
    "card", "panel", "hero", "banner", "service", "rankrow", "demanditem",
    "videoitem", "sidebarstatus", "sidebarnavitem", "sourcestop", "historytop",
)
_TAB_BUTTON_NAMES = frozenset({"sourceTabButton", "historyTab"})


def rewrite_inline_border_stylesheet(stylesheet: str) -> str:
    """Faz a cor dourada prevalecer em QSS inline sem reescrever outras propriedades."""
    value = str(stylesheet or "")
    if not value.strip() or "{" in value or "}" in value:
        return value

    border_pattern = re.compile(r"(?i)(\bborder\s*:\s*)([^;]+)(;)")
    if border_pattern.search(value):
        value = border_pattern.sub(
            lambda match: f"{match.group(1)}1px solid {GOLD_BORDER}{match.group(3)}",
            value,
        )
    else:
        value = value.rstrip()
        if value and not value.endswith(";"):
            value += ";"
        value += f" border: 1px solid {GOLD_BORDER};"
    return value


def _is_card_frame(widget: QWidget) -> bool:
    if not isinstance(widget, QFrame):
        return False
    name = widget.objectName().strip()
    if name in _CARD_OBJECT_NAMES:
        return True
    if name:
        lowered = name.casefold()
        if any(token in lowered for token in _CARD_NAME_TOKENS):
            return True

    # Alguns cards do Editor de Vídeo são criados sem objectName e recebem
    # seu QSS diretamente. Nesse caso, use o próprio stylesheet como indício.
    own_stylesheet = (widget.styleSheet() or "").casefold()
    return bool(
        own_stylesheet
        and "background" in own_stylesheet
        and "border" in own_stylesheet
        and "border:0" not in own_stylesheet.replace(" ", "")
        and "border:none" not in own_stylesheet.replace(" ", "")
    )


def _append_page_rules(widget: QWidget) -> None:
    current = widget.styleSheet() or ""
    if _RULES_MARKER in current:
        return

    # O stylesheet raiz da janela e os stylesheets locais de cada página
    # contêm seletores nomeados; anexamos a regra ao nível certo para vencer
    # as bordas anteriores em azul/cinza/verde/vermelho.
    is_window = isinstance(widget, QMainWindow)
    has_card_or_tab_rules = any(token in current for token in (
        "QFrame#", "QTabBar", "QTabWidget::pane", "QGroupBox",
    ))
    if not (is_window or has_card_or_tab_rules):
        return

    widget.setStyleSheet(current.rstrip() + "\n" + GOLD_BORDER_QSS)


def _force_widget_border(widget: QWidget) -> None:
    name = widget.objectName().strip()
    is_tab_button = isinstance(widget, QPushButton) and name in _TAB_BUTTON_NAMES
    is_tab_bar = isinstance(widget, QTabBar)
    is_card_frame = _is_card_frame(widget)

    if not (is_tab_button or is_tab_bar or is_card_frame):
        return
    if widget.property(_WIDGET_MARKER_PROPERTY):
        return

    current = widget.styleSheet() or ""
    # Widgets com QSS inline (por exemplo, os painéis do editor de vídeo)
    # precisam ter apenas a declaração da borda atualizada. Nos restantes,
    # adicionamos uma regra específica para o widget, preservando seu estilo.
    if current.strip() and "{" not in current and "}" not in current:
        updated = rewrite_inline_border_stylesheet(current)
    elif is_tab_bar:
        updated = current.rstrip() + f"\nQTabBar::tab {{ border: 1px solid {GOLD_BORDER}; border-bottom: 1px solid {GOLD_BORDER}; }}\nQTabBar::tab:selected {{ border-color: {GOLD_BORDER}; }}"
    else:
        widget_class = "QPushButton" if is_tab_button else "QFrame"
        selector = f"{widget_class}#{name}" if name else widget_class
        updated = current.rstrip() + f"\n{selector} {{ border: 1px solid {GOLD_BORDER}; }}"

    # Marque antes de setStyleSheet: o Qt pode emitir StyleChange de forma
    # síncrona e o event filter não deve tentar estilizar o mesmo widget de novo.
    widget.setProperty(_WIDGET_MARKER_PROPERTY, True)
    widget.setStyleSheet(updated)


def _walk(root: QWidget) -> None:
    _append_page_rules(root)
    _force_widget_border(root)
    for child in root.findChildren(QWidget):
        _append_page_rules(child)
        _force_widget_border(child)


class _GoldBorderFilter(QObject):
    def eventFilter(self, obj, event):
        if isinstance(obj, QWidget) and event.type() in {
            QEvent.Type.Show,
            QEvent.Type.Polish,
            QEvent.Type.StyleChange,
        }:
            try:
                _append_page_rules(obj)
                _force_widget_border(obj)
            except RuntimeError:
                # O Qt pode destruir um widget durante uma atualização de tela.
                pass
        return super().eventFilter(obj, event)


_FILTER: _GoldBorderFilter | None = None
_INSTALLED = False


def install_gold_borders_patch(app: QApplication, window: QWidget) -> None:
    """Aplica bordas douradas aos cards e abas atuais e aos criados depois."""
    global _FILTER, _INSTALLED
    if _INSTALLED:
        _walk(window)
        return

    _FILTER = _GoldBorderFilter(app)
    app.installEventFilter(_FILTER)
    _walk(window)
    _INSTALLED = True
