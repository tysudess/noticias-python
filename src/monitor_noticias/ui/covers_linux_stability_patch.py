from __future__ import annotations

import faulthandler
import logging
from pathlib import Path
import sys
import time
from typing import Callable

import requests

from PySide6.QtCore import QRect, Qt, QTimer, qInstallMessageHandler
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.capas_tool.app import (
    web_resolver as web_resolver_module,
)


log = logging.getLogger(
    "monitor_noticias.covers.linux_stability"
)

_INSTALLED = False
_FAULT_HANDLE = None
_QT_LOG_HANDLE = None
_PREVIOUS_QT_HANDLER = None


def _diagnostic_path(name: str) -> Path:
    path = AppPaths.discover().logs / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _append_diagnostic(message: str) -> None:
    try:
        with _diagnostic_path("covers_webengine.log").open(
            "a",
            encoding="utf-8",
            errors="ignore",
        ) as handle:
            handle.write(
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
            )
    except Exception:
        pass


def _install_native_crash_diagnostics() -> None:
    """Mantém rastros úteis inclusive quando Chromium/Qt termina nativamente."""

    global _FAULT_HANDLE, _QT_LOG_HANDLE, _PREVIOUS_QT_HANDLER

    if _FAULT_HANDLE is None:
        try:
            _FAULT_HANDLE = _diagnostic_path(
                "covers_native_crash.log"
            ).open(
                "a",
                encoding="utf-8",
                buffering=1,
            )
            faulthandler.enable(
                file=_FAULT_HANDLE,
                all_threads=True,
            )
        except Exception:
            _FAULT_HANDLE = None

    if _QT_LOG_HANDLE is None:
        try:
            _QT_LOG_HANDLE = _diagnostic_path(
                "covers_qt_messages.log"
            ).open(
                "a",
                encoding="utf-8",
                buffering=1,
            )

            def qt_handler(msg_type, context, message):
                text = str(message or "")
                lower = text.lower()

                if any(
                    token in lower
                    for token in (
                        "webengine",
                        "chromium",
                        "render",
                        "gpu",
                        "sandbox",
                        "proxy",
                        "certificate",
                        "ssl",
                    )
                ):
                    try:
                        category = getattr(
                            context,
                            "category",
                            "",
                        )
                        _QT_LOG_HANDLE.write(
                            f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"type={int(msg_type)} category={category} | {text}\n"
                        )
                    except Exception:
                        pass

                previous = _PREVIOUS_QT_HANDLER
                if previous is not None:
                    try:
                        previous(msg_type, context, message)
                    except Exception:
                        pass
                else:
                    # qInstallMessageHandler substitui o handler padrão. Sem
                    # esta cópia, mensagens Qt que antes iam para
                    # inicializacao.log desapareceriam justamente durante o
                    # diagnóstico do crash.
                    try:
                        sys.stderr.write(text + "\n")
                        sys.stderr.flush()
                    except Exception:
                        pass

            _PREVIOUS_QT_HANDLER = qInstallMessageHandler(
                qt_handler
            )
        except Exception:
            _QT_LOG_HANDLE = None


def _install_profile_lifetime_patch(browser_cls) -> None:
    """Garante que o profile sobreviva ao último page.deleteLater().

    O código base prendia QWebEngineProfile ao objeto _AttachedBrowser. Em
    vários resolvers o browser era deleteLater() logo após view.deleteLater(),
    permitindo que o profile fosse destruído antes de a página Chromium sair
    da fila de eventos. No Linux esse padrão pode terminar o processo nativo.
    """

    original_init = browser_cls.__init__

    if getattr(
        original_init,
        "_central_linux_covers_v98",
        False,
    ):
        return

    def patched_init(self, owner, user_agent):
        original_init(self, owner, user_agent)

        app = QApplication.instance()
        profile = getattr(self, "profile", None)
        interceptor = getattr(self, "interceptor", None)

        if app is not None and profile is not None:
            try:
                profile.setParent(app)
            except Exception:
                pass

            if interceptor is not None:
                try:
                    interceptor.setParent(profile)
                except Exception:
                    pass

            def retire_profile(*_args, p=profile):
                # view/page usam deleteLater(). Damos dois ciclos de margem
                # antes de liberar o contexto Chromium.
                try:
                    QTimer.singleShot(
                        1500,
                        p.deleteLater,
                    )
                except Exception:
                    pass

            try:
                self.destroyed.connect(retire_profile)
            except Exception:
                pass

        _append_diagnostic(
            "browser criado; profile=%s ua=%s"
            % (
                hex(id(profile)) if profile is not None else "none",
                str(user_agent or "")[:80],
            )
        )

    patched_init._central_linux_covers_v98 = True
    browser_cls.__init__ = patched_init


def _safe_linux_destroy_page(self) -> None:
    """Para a página sem fabricar outra QWebEnginePage durante teardown."""

    page = getattr(self, "page", None)
    view = getattr(self, "view", None)

    self.page = None
    self.view = None

    if page is not None:
        try:
            page.triggerAction(
                QWebEnginePage.WebAction.Stop
            )
        except Exception:
            pass

    if view is not None:
        try:
            view.hide()
        except Exception:
            pass

        try:
            view.deleteLater()
        except Exception:
            pass

    _append_diagnostic(
        "browser page encerrada; page=%s view=%s"
        % (
            hex(id(page)) if page is not None else "none",
            hex(id(view)) if view is not None else "none",
        )
    )


def _safe_linux_new_page(
    self,
    captured_callback: Callable[[str], None],
):
    """Cria uma superfície Chromium própria, fora do QMainWindow destacado.

    A aba Capas é integrada retirando o centralWidget de um QMainWindow motor.
    Vincular QWebEngineView àquela janela escondida deixava a superfície nativa
    presa a um host que já não continha a UI. V98 usa uma janela offscreen
    independente e mantém explicitamente profile/page/view em ordem segura.
    """

    self.destroy_page()

    view = QWebEngineView(None)
    view.setAttribute(
        Qt.WidgetAttribute.WA_DontShowOnScreen,
        True,
    )
    view.setGeometry(
        QRect(0, 0, 1200, 1600)
    )

    page = web_resolver_module.CapturePage(
        self.profile,
        view,
    )
    page.captured.connect(captured_callback)
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

    def render_terminated(status, code):
        message = (
            "renderProcessTerminated status=%s code=%s profile=%s"
            % (status, code, hex(id(self.profile)))
        )
        log.error(message)
        _append_diagnostic(message)

    try:
        page.renderProcessTerminated.connect(
            render_terminated
        )
    except Exception:
        pass

    self.view = view
    self.page = page

    # show() mantém layout/lazy-load ativos. WA_DontShowOnScreen impede que a
    # janela seja composta na área visível do usuário.
    view.show()

    _append_diagnostic(
        "page criada; profile=%s page=%s view=%s"
        % (
            hex(id(self.profile)),
            hex(id(page)),
            hex(id(view)),
        )
    )

    return page


def _install_corporate_requests_tls_patch() -> None:
    """Aplica a exceção TLS já autorizada também ao HTTP da aba Capas.

    O código de autenticação já usava ProxySettings.requests_verify(), mas o
    caminho requests das Capas não. Resultado: no proxy proxy-7dn.mb:6060 uma
    falha de certificado podia forçar desnecessariamente o fallback Chromium.
    A política continua exatamente restrita ao host/porta definidos em
    ProxySettings; qualquer outro proxy mantém verify=True.
    """

    from monitor_noticias.capas_tool.app import network as network_module

    original_text = network_module._requests_get_text_via_central_proxy

    if not getattr(
        original_text,
        "_central_linux_tls_v98",
        False,
    ):
        def patched_text(
            url: str,
            *,
            headers: dict | None,
            connect_timeout: int,
            read_timeout: int,
            config,
        ) -> str:
            proxies = network_module._central_requests_proxies(
                config
            )
            settings = network_module._get_central_proxy_settings()
            verify = settings.requests_verify(config)

            with requests.Session() as session:
                session.trust_env = False
                response = session.get(
                    url,
                    timeout=(connect_timeout, read_timeout),
                    headers=headers or {},
                    allow_redirects=True,
                    proxies=proxies,
                    verify=verify,
                )

                if not 200 <= response.status_code < 300:
                    raise RuntimeError(
                        f"HTTP {response.status_code}"
                    )

                return (response.text or "").strip()

        patched_text._central_linux_tls_v98 = True
        network_module._requests_get_text_via_central_proxy = patched_text

    original_download = network_module.download_image

    if getattr(
        original_download,
        "_central_linux_tls_v98",
        False,
    ):
        return

    def patched_download(
        url,
        dest,
        referer="",
        cookie_header="",
        user_agent=network_module.IMAGE_UA,
    ):
        headers = {
            "User-Agent": user_agent or network_module.IMAGE_UA,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }

        if referer:
            headers["Referer"] = referer
        if cookie_header:
            headers["Cookie"] = cookie_header

        config = network_module.refresh_central_proxy()
        proxies = None
        verify = True

        if config.enabled:
            proxies = network_module._central_requests_proxies(
                config
            )
            verify = (
                network_module
                ._get_central_proxy_settings()
                .requests_verify(config)
            )

        with requests.Session() as session:
            session.trust_env = not config.enabled

            try:
                response_context = session.get(
                    url,
                    timeout=(7, 18),
                    headers=headers,
                    stream=True,
                    allow_redirects=True,
                    proxies=proxies,
                    verify=verify,
                )
            except Exception as exc:
                detail = network_module._sanitize_proxy_error(
                    exc,
                    config,
                )
                prefix = (
                    "Proxy geral do Central: "
                    if config.enabled
                    else ""
                )
                raise RuntimeError(prefix + detail) from exc

            with response_context as response:
                response.raise_for_status()
                ctype = (
                    response.headers.get("Content-Type") or ""
                ).lower()

                if "html" in ctype:
                    raise RuntimeError(
                        "O endereço retornou HTML em vez da imagem da página."
                    )

                dest = Path(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                total = 0

                with dest.open("wb") as file_handle:
                    for chunk in response.iter_content(32 * 1024):
                        if not chunk:
                            continue
                        file_handle.write(chunk)
                        total += len(chunk)
                        if total > 60 * 1024 * 1024:
                            raise RuntimeError(
                                "imagem maior que 60 MB"
                            )

        if dest.stat().st_size < 8192:
            raise RuntimeError(
                "arquivo de imagem vazio/placeholder"
            )

        return dest

    patched_download._central_linux_tls_v98 = True
    network_module.download_image = patched_download


def install_covers_linux_stability_patch() -> None:
    """V98: lifecycle Chromium + diagnóstico nativo + TLS corporativo Linux."""

    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    _install_native_crash_diagnostics()
    _install_corporate_requests_tls_patch()

    browser_cls = web_resolver_module._AttachedBrowser

    _install_profile_lifetime_patch(browser_cls)

    if not getattr(
        browser_cls.destroy_page,
        "_central_linux_covers_v98",
        False,
    ):
        destroy = _safe_linux_destroy_page
        destroy._central_linux_covers_v98 = True
        browser_cls.destroy_page = destroy

    if not getattr(
        browser_cls.new_page,
        "_central_linux_covers_v98",
        False,
    ):
        create = _safe_linux_new_page
        create._central_linux_covers_v98 = True
        browser_cls.new_page = create

    resolver_cls = getattr(
        web_resolver_module,
        "ParallelCentralClippingResolver",
        None,
    )

    if resolver_cls is not None:
        resolver_cls.MAX_CONCURRENT_NEWSPAPERS = 1

    _append_diagnostic(
        "V98 instalada: Chromium serial, teardown seguro, TLS corporativo restrito."
    )
    _INSTALLED = True
