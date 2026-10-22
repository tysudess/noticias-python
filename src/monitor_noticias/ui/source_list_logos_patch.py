from __future__ import annotations

import logging
import threading
import weakref
from urllib.parse import urlsplit

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap

from monitor_noticias.networking.source_sites import (
    build_favicon_request_url,
    normalize_site_url,
    resolve_source_site_url,
)

log = logging.getLogger(__name__)
_TIMEOUT = (2.5, 4.0)
_MAX_BYTES = 256 * 1024


def _source_site(source) -> str:
    for attr in ("url", "homepage", "website", "site_url", "source_url", "base_url"):
        value = normalize_site_url(str(getattr(source, attr, "") or ""))
        if value:
            return value
    # Reuse the name-to-domain fallback catalogue shared with the News page.
    class _SourceProxy:
        pass
    proxy = _SourceProxy()
    proxy.source = str(getattr(source, "name", "") or "")
    proxy.sourceUrl = ""
    proxy.link = ""
    return resolve_source_site_url(proxy)


class _Signals(QObject):
    done = Signal(str, bytes)


class _Task(QRunnable):
    def __init__(self, domain: str, url: str, cache):
        super().__init__()
        self.domain, self.url, self.cache = domain, url, cache
        self.signals = _Signals()

    def run(self):
        response = None
        try:
            proxies, verify, permitted = self.cache.proxy_snapshot()
            if not permitted:
                self.signals.done.emit(self.domain, b"")
                return
            response = requests.get(
                build_favicon_request_url(self.url),
                timeout=_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 CentralInteligenteDeMidia/1.0"},
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                stream=True,
            )
            if not response.ok or not str(response.headers.get("content-type", "")).lower().startswith("image/"):
                self.signals.done.emit(self.domain, b"")
                return
            length = int(response.headers.get("content-length", "0") or 0)
            if length > _MAX_BYTES:
                self.signals.done.emit(self.domain, b"")
                return
            data = bytearray()
            for chunk in response.iter_content(8192):
                if chunk:
                    if len(data) + len(chunk) > _MAX_BYTES:
                        data.clear()
                        break
                    data.extend(chunk)
            self.signals.done.emit(self.domain, bytes(data))
        except Exception as exc:
            log.debug("Favicon da fonte %s indisponível: %s", self.domain, exc)
            self.signals.done.emit(self.domain, b"")
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass


class _Cache(QObject):
    changed = Signal(str)

    def __init__(self, proxy_settings, parent=None):
        super().__init__(parent)
        self.proxy_settings = proxy_settings
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.pixmaps = {}
        self.pending = set()
        self.finished = set()
        self.tasks = {}
        self.lock = threading.Lock()
        self.loaded = False
        self.failed = False
        self.proxies = None
        self.verify = True

    def proxy_snapshot(self):
        if self.proxy_settings is None:
            return None, True, True
        with self.lock:
            if not self.loaded:
                try:
                    config = self.proxy_settings.load()
                    self.proxies = self.proxy_settings.requests_proxies(config)
                    self.verify = self.proxy_settings.requests_verify(config)
                except Exception:
                    self.failed = True
                    log.debug("Proxy Geral indisponível para logos das fontes.", exc_info=True)
                self.loaded = True
            return self.proxies, self.verify, not self.failed

    def icon_for(self, source):
        site = _source_site(source)
        host = (urlsplit(site).hostname or "").lower()
        if not host:
            return None
        if host in self.pixmaps:
            return self.pixmaps[host]
        if host not in self.pending and host not in self.finished:
            self.pending.add(host)
            task = _Task(host, site, self)
            task.setAutoDelete(False)
            self.tasks[host] = task
            task.signals.done.connect(self.on_done, Qt.ConnectionType.QueuedConnection)
            self.pool.start(task)
        return None

    @Slot(str, bytes)
    def on_done(self, host, data):
        self.pending.discard(host)
        self.tasks.pop(host, None)
        self.finished.add(host)
        if data:
            image = QImage.fromData(data)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    self.pixmaps[host] = pixmap
        self.changed.emit(host)


_PATCHED = False


def install_source_list_logos_patch():
    global _PATCHED
    if _PATCHED:
        return
    from monitor_noticias.ui.source_page import SourceDelegate, SourceListModel

    original_paint = SourceDelegate.paint

    def paint_with_site_logo(self, painter, option, index):
        original_paint(self, painter, option, index)
        source = index.data(SourceListModel.SourceRole)
        if source is None:
            return
        cache = getattr(self, "_central_source_logo_cache", None)
        if cache is None:
            page = self.parent()
            controller = getattr(page, "controller", None)
            cache = _Cache(getattr(controller, "proxy", None), parent=self)
            self._central_source_logo_cache = cache
            delegate_ref = weakref.ref(self)

            def refresh(_host, ref=delegate_ref):
                delegate = ref()
                if delegate is not None:
                    page = delegate.parent()
                    view = getattr(page, "list_view", None)
                    if view is not None:
                        view.viewport().update()

            cache.changed.connect(refresh)
        pixmap = cache.icon_for(source)
        if pixmap is None:
            return
        card = option.rect.adjusted(2, 3, -4, -3)
        badge = QRect(card.left() + 56, card.top() + 12, 54, 38)
        target = badge.adjusted(6, 4, -6, -4)
        scaled = pixmap.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        dest = QRect(target.center().x() - scaled.width() // 2,
                     target.center().y() - scaled.height() // 2,
                     scaled.width(), scaled.height())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor("#E9F4FF"))
        painter.setPen(QPen(QColor("#E9F4FF"), 1))
        painter.drawRoundedRect(badge, 8, 8)
        painter.drawPixmap(dest, scaled)
        painter.restore()

    paint_with_site_logo._central_source_list_logo_patch = True
    SourceDelegate.paint = paint_with_site_logo
    _PATCHED = True
