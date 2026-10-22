from __future__ import annotations

import logging
import threading
import weakref
from urllib.parse import urlsplit

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtCore import QRect


log = logging.getLogger(__name__)

FAVICON_TIMEOUT = (2.5, 4.0)
MAX_FAVICON_BYTES = 256 * 1024

from monitor_noticias.networking.source_sites import (
    build_favicon_request_url,
    resolve_source_site_url,
)


class _FetchSignals(QObject):
    completed = Signal(str, bytes)


class _FaviconTask(QRunnable):
    def __init__(self, domain_key: str, site_url: str, owner: "NewsSiteIconCache") -> None:
        super().__init__()
        self.domain_key = domain_key
        self.site_url = site_url
        self.owner = owner
        self.signals = _FetchSignals()

    def run(self) -> None:
        url = build_favicon_request_url(self.site_url)
        if not url:
            self.signals.completed.emit(self.domain_key, b"")
            return

        proxies, verify, permitted = self.owner._proxy_snapshot()
        if not permitted:
            self.signals.completed.emit(self.domain_key, b"")
            return

        response = None
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 CentralInteligenteDeMidia/1.0"},
                timeout=FAVICON_TIMEOUT,
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                stream=True,
            )
            if not response.ok:
                self.signals.completed.emit(self.domain_key, b"")
                return

            content_type = str(response.headers.get("content-type", "")).lower()
            if not content_type.startswith("image/"):
                self.signals.completed.emit(self.domain_key, b"")
                return

            try:
                declared_size = int(response.headers.get("content-length", "0") or 0)
            except (TypeError, ValueError):
                declared_size = 0
            if declared_size > MAX_FAVICON_BYTES:
                self.signals.completed.emit(self.domain_key, b"")
                return

            data = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                if len(data) + len(chunk) > MAX_FAVICON_BYTES:
                    data.clear()
                    break
                data.extend(chunk)
            self.signals.completed.emit(self.domain_key, bytes(data))
        except Exception as exc:
            # Ícones são opcionais; falha aqui não deve atrasar nem invalidar a busca.
            log.debug("Não foi possível carregar o favicon de %s: %s", self.domain_key, exc)
            self.signals.completed.emit(self.domain_key, b"")
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass


class NewsSiteIconCache(QObject):
    icon_ready = Signal(str)

    def __init__(self, proxy_settings=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proxy_settings = proxy_settings
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(3)
        self._pixmaps: dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        self._finished: set[str] = set()
        self._tasks: dict[str, _FaviconTask] = {}
        self._proxy_lock = threading.Lock()
        self._proxy_loaded = False
        self._proxy_load_failed = False
        self._proxies = None
        self._verify = True

    def _proxy_snapshot(self):
        # A leitura de credenciais acontece na thread de rede, nunca durante o paint.
        if self._proxy_settings is None:
            return None, True, True
        with self._proxy_lock:
            if not self._proxy_loaded:
                try:
                    config = self._proxy_settings.load()
                    self._proxies = self._proxy_settings.requests_proxies(config)
                    self._verify = self._proxy_settings.requests_verify(config)
                except Exception:
                    self._proxy_load_failed = True
                    log.debug("Proxy Geral indisponível para os ícones dos veículos.", exc_info=True)
                self._proxy_loaded = True
            return self._proxies, self._verify, not self._proxy_load_failed

    def icon_for(self, news) -> QPixmap | None:
        site_url = resolve_source_site_url(news)
        if not site_url:
            return None
        parsed = urlsplit(site_url)
        domain_key = (parsed.hostname or "").lower()
        if not domain_key:
            return None

        pixmap = self._pixmaps.get(domain_key)
        if pixmap is not None:
            return pixmap
        if domain_key not in self._pending and domain_key not in self._finished:
            self._pending.add(domain_key)
            task = _FaviconTask(domain_key, site_url, self)
            # Mantém o QRunnable vivo até a resposta enfileirada ser tratada na UI.
            task.setAutoDelete(False)
            self._tasks[domain_key] = task
            task.signals.completed.connect(
                self._on_loaded,
                Qt.ConnectionType.QueuedConnection,
            )
            self._pool.start(task)
        return None

    @Slot(str, bytes)
    def _on_loaded(self, domain_key: str, image_bytes: bytes) -> None:
        self._pending.discard(domain_key)
        self._tasks.pop(domain_key, None)
        self._finished.add(domain_key)
        if image_bytes:
            image = QImage.fromData(image_bytes)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    self._pixmaps[domain_key] = pixmap
        self.icon_ready.emit(domain_key)


_PATCHED = False


def install_news_site_icons_patch() -> None:
    """Substitui visualmente as iniciais pelo favicon sem bloquear o desenho da lista."""
    global _PATCHED
    if _PATCHED:
        return

    from monitor_noticias.ui.news_page import NewsDelegate, NewsModel

    original_paint = NewsDelegate.paint

    def paint_with_official_site_icon(self, painter, option, index):
        original_paint(self, painter, option, index)
        news = index.data(NewsModel.NewsRole)
        if news is None:
            return

        cache = getattr(self, "_central_news_site_icon_cache", None)
        if cache is None:
            parent = self.parent()
            controller = getattr(parent, "controller", None)
            proxy_settings = getattr(controller, "proxy", None)
            cache = NewsSiteIconCache(proxy_settings=proxy_settings, parent=self)
            self._central_news_site_icon_cache = cache
            delegate_ref = weakref.ref(self)

            def refresh_view(_domain, _delegate_ref=delegate_ref):
                delegate = _delegate_ref()
                if delegate is None:
                    return
                page = delegate.parent()
                list_view = getattr(page, "list_view", None)
                if list_view is not None:
                    list_view.viewport().update()

            cache.icon_ready.connect(refresh_view)

        pixmap = cache.icon_for(news)
        if pixmap is None:
            return

        card = option.rect.adjusted(2, 3, -4, -3)
        avatar = QRect(card.left() + 14, card.top() + 16, 40, 40)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#DCE9F6"), 1))
        painter.drawRoundedRect(avatar, 8, 8)

        target = avatar.adjusted(4, 4, -4, -4)
        scaled = pixmap.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        destination = QRect(
            target.center().x() - scaled.width() // 2,
            target.center().y() - scaled.height() // 2,
            scaled.width(),
            scaled.height(),
        )
        painter.drawPixmap(destination, scaled)
        painter.restore()

    paint_with_official_site_icon._central_official_site_icon_patch = True
    NewsDelegate.paint = paint_with_official_site_icon
    _PATCHED = True
