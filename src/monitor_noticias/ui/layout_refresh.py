from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractButton, QFrame, QLabel, QProgressBar, QPushButton, QRadioButton,
    QTableWidget, QWidget,
)


def _prop(widget: QWidget | None, name: str, value) -> None:
    if widget is None:
        return
    widget.setProperty(name, value)


def _secondary(button: QAbstractButton | None) -> None:
    if button is not None:
        _prop(button, "secondary", True)


def _decorate_home(page) -> None:
    for key, value in getattr(page, "metric_labels", {}).items():
        value.setObjectName("metricValue")
        parent = value.parentWidget()
        if isinstance(parent, QFrame):
            parent.setObjectName("metricCard")

    for name in ("home_buscar_demandas", "home_buscar_vídeos", "home_termos_de_busca"):
        button = page.findChild(QPushButton, name)
        if button:
            _secondary(button)


def _decorate_news(page, window) -> None:
    """A nova NewsPage já possui seu próprio layout completo.

    Não tentar reutilizar a decoração da implementação antiga baseada em BasePage/root,
    pois a NewsPage dedicada monta seu layout diretamente no QWidget.
    """
    return


def _decorate_videos(page) -> None:
    _secondary(getattr(page, "stop", None))
    table = getattr(page, "table", None)
    if isinstance(table, QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)


def _decorate_demands(page) -> None:
    _secondary(getattr(page, "all", None))
    status = getattr(page, "status", None)
    if isinstance(status, QLabel):
        status.setStyleSheet(
            "background:#ECFBF4;border:1px solid #B8EBD4;border-radius:12px;"
            "padding:16px;color:#086C50;font-weight:700;"
        )
    table = getattr(page, "table", None)
    if isinstance(table, QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)


def _decorate_settings(page) -> None:
    _secondary(getattr(page, "test_proxy", None))
    proxy = getattr(page, "proxy_frame", None)
    if isinstance(proxy, QFrame):
        proxy.setObjectName("card")


def _decorate_extractor(page) -> None:
    button = getattr(page, "download_button", None)
    if isinstance(button, QPushButton):
        _prop(button, "gold", True)
        button.setMinimumHeight(54)

    for attr in (
        "open_videos_button", "cancel_button", "clear_history_button",
        "delete_session_button", "login_button", "update_button",
    ):
        _secondary(getattr(page, attr, None))

    progress = getattr(page, "progress", None)
    if isinstance(progress, QProgressBar):
        progress.setTextVisible(True)

    for radio in page.findChildren(QRadioButton):
        radio.setMinimumHeight(34)


def _decorate_pdf(page) -> None:
    for button in page.findChildren(QPushButton):
        text = button.text().lower()
        if any(x in text for x in ("voltar", "limpar", "selecionar", "trocar", "abrir")):
            _secondary(button)
        if "gerar pdf" in text:
            _prop(button, "green", True)
            button.setMinimumHeight(46)


def _decorate_video_editor(page) -> None:
    for button in page.findChildren(QPushButton):
        text = button.text().lower()
        if any(x in text for x in ("voltar", "abrir", "limpar")):
            _secondary(button)


def apply_reference_layout(window) -> None:
    """Aplica ajustes visuais complementares sem alterar regras de negócio."""
    pages = getattr(window, "pages", {})

    for section, page in pages.items():
        name = getattr(section, "name", "")
        if name == "HOME":
            _decorate_home(page)
        elif name == "NEWS":
            _decorate_news(page, window)
        elif name == "VIDEOS":
            _decorate_videos(page)
        elif name == "DEMANDS":
            _decorate_demands(page)
        elif name == "SETTINGS":
            _decorate_settings(page)
        elif name == "EXTRACTOR":
            _decorate_extractor(page)
        elif name == "PDF_EDITOR":
            _decorate_pdf(page)
        elif name == "VIDEO_EDITOR":
            _decorate_video_editor(page)

    for table in window.findChildren(QTableWidget):
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
