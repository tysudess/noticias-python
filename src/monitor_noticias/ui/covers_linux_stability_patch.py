from __future__ import annotations

import logging
import sys
from typing import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtWebEngineCore import (
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import (
    QWebEngineView,
)
from PySide6.QtWidgets import QWidget

from monitor_noticias.capas_tool.app import (
    web_resolver as web_resolver_module,
)


log = logging.getLogger(
    "monitor_noticias.covers.linux_stability"
)

_INSTALLED = False


def _safe_linux_new_page(
    self,
    captured_callback: Callable[[str], None],
):
    """Cria Chromium anexado sem janela negativa/visível no Ubuntu.

    Mantém a página renderizando para lazy-load/canvas, mas evita uma
    QWebEngineView top-level gigante fora das coordenadas da tela. Essa
    combinação era especialmente sensível no QtWebEngine Linux.
    """

    self.destroy_page()

    parent_widget = (
        self.owner
        if isinstance(self.owner, QWidget)
        else None
    )

    view = QWebEngineView(
        parent_widget
    )

    # Continua "mostrada" para que Chromium faça layout/lazy-load, porém o Qt
    # não a envia para a superfície visível do compositor.
    view.setAttribute(
        Qt.WidgetAttribute.WA_DontShowOnScreen,
        True,
    )
    view.setGeometry(
        QRect(
            0,
            0,
            1200,
            1600,
        )
    )

    page = web_resolver_module.CapturePage(
        self.profile,
        view,
    )
    page.captured.connect(
        captured_callback
    )
    view.setPage(page)

    settings = page.settings()
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.JavascriptEnabled,
        True,
    )
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.AutoLoadImages,
        True,
    )
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
        True,
    )
    settings.setAttribute(
        QWebEngineSettings.WebAttribute.LocalStorageEnabled,
        True,
    )

    # O Chromium da aba Capas não precisa de WebGL nem canvas acelerado.
    # Canvas 2D continua disponível por software para a captura da capa.
    try:
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled,
            False,
        )
    except Exception:
        pass

    try:
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled,
            False,
        )
    except Exception:
        pass

    try:
        page.renderProcessTerminated.connect(
            lambda status, code: log.error(
                "QtWebEngine da aba Capas encerrou: status=%s código=%s",
                status,
                code,
            )
        )
    except Exception:
        pass

    self.view = view
    self.page = page

    view.show()

    return page


def install_covers_linux_stability_patch() -> None:
    """Reduz risco de crash nativo do QtWebEngine somente no Linux."""

    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    browser_cls = (
        web_resolver_module._AttachedBrowser
    )

    if not getattr(
        browser_cls.new_page,
        "_central_linux_covers_v97",
        False,
    ):
        safe = _safe_linux_new_page
        safe._central_linux_covers_v97 = True
        browser_cls.new_page = safe

    # A rotina Android-portada chegava a abrir até quatro navegadores Chromium
    # ao mesmo tempo. No Ubuntu Portable usamos uma fila: é mais estável e não
    # altera o conteúdo final das capas.
    resolver_cls = getattr(
        web_resolver_module,
        "ParallelCentralClippingResolver",
        None,
    )

    if resolver_cls is not None:
        resolver_cls.MAX_CONCURRENT_NEWSPAPERS = 1

    _INSTALLED = True
