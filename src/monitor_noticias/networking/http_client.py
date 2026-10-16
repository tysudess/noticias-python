from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from threading import local
from time import monotonic
from typing import Any, Callable, TYPE_CHECKING, Iterator
import re

import requests

if TYPE_CHECKING:
    from .proxy import ProxySettings


@dataclass(slots=True)
class HttpResult:
    status: int
    text: str
    headers: dict[str, str]


class HttpClient:
    """Cliente HTTP compartilhado, com cache GET opcional e limitado por escopo.

    O cache só fica ativo enquanto um chamador abre ``request_cache_scope``.
    Ele é local à thread, desaparece ao sair do escopo e só armazena respostas
    HTML pequenas, sem Set-Cookie. A busca de vídeos usa o escopo para evitar
    baixar novamente a mesma página quando coletores diferentes consultam a
    mesma URL durante uma única execução.
    """

    CACHE_MAX_ENTRIES = 96
    CACHE_MAX_BYTES = 24 * 1024 * 1024
    CACHE_MAX_ENTRY_BYTES = 4 * 1024 * 1024
    HTML_CONTENT_TYPE_RE = re.compile(r"text/html|application/xhtml\+xml", re.I)

    def __init__(
        self,
        session: requests.Session | None = None,
        proxies: dict[str, str] | None = None,
        proxy_provider: Callable[[], dict[str, str] | None] | None = None,
    ):
        self.session = session or requests.Session()
        self.proxies = proxies
        self.proxy_provider = proxy_provider
        self._local = local()

    @classmethod
    def from_proxy_settings(
        cls,
        proxy_settings: "ProxySettings",
        *,
        session: requests.Session | None = None,
    ) -> "HttpClient":
        return cls(session=session, proxy_provider=proxy_settings.requests_proxies)

    def _proxies(self) -> dict[str, str] | None:
        return self.proxy_provider() if self.proxy_provider is not None else self.proxies

    @staticmethod
    def _cache_key(url: str, headers: dict[str, str], max_body_bytes: int | None):
        normalized_headers = tuple(
            sorted((str(key).lower().strip(), str(value).strip()) for key, value in headers.items())
        )
        return (str(url), normalized_headers, max_body_bytes)

    @contextmanager
    def request_cache_scope(
        self,
        *,
        max_entries: int | None = None,
        max_bytes: int | None = None,
        max_entry_bytes: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Habilita cache temporário e estatísticas apenas para a thread atual."""
        previous = getattr(self._local, "request_cache_state", None)
        state: dict[str, Any] = {
            "cache": OrderedDict(),
            "max_entries": max(1, int(max_entries or self.CACHE_MAX_ENTRIES)),
            "max_bytes": max(1, int(max_bytes or self.CACHE_MAX_BYTES)),
            "max_entry_bytes": max(1, int(max_entry_bytes or self.CACHE_MAX_ENTRY_BYTES)),
            "cached_bytes": 0,
            "network_gets": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_reused_bytes": 0,
            "bytes_received": 0,
            "elapsed_ms": 0,
            "errors": 0,
        }
        self._local.request_cache_state = state
        try:
            yield state
        finally:
            self._local.request_cache_state = previous

    def get_text(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        connect_timeout: float,
        read_timeout: float,
        max_body_bytes: int | None = None,
    ) -> str:
        request_headers = headers or {}
        state = getattr(self._local, "request_cache_state", None)
        cache = state["cache"] if state is not None else None
        key = self._cache_key(url, request_headers, max_body_bytes) if state is not None else None

        if key is not None and key in cache:
            text, size = cache.pop(key)
            cache[key] = (text, size)  # LRU: reuse moves the entry to the end.
            state["cache_hits"] += 1
            state["cache_reused_bytes"] += size
            return text

        if state is not None:
            if key is not None:
                state["cache_misses"] += 1
            state["network_gets"] += 1
        started = monotonic() if state is not None else 0.0

        try:
            response = self.session.get(
                url,
                headers=request_headers,
                timeout=(connect_timeout, read_timeout),
                allow_redirects=True,
                proxies=self._proxies(),
            )
            response.raise_for_status()
            data = response.content
            if max_body_bytes is not None:
                data = data[:max_body_bytes]
            text = data.decode(response.encoding or "utf-8", errors="replace")
        except Exception:
            if state is not None:
                state["elapsed_ms"] += int((monotonic() - started) * 1000)
                state["errors"] += 1
            raise

        if state is not None:
            state["elapsed_ms"] += int((monotonic() - started) * 1000)
            state["bytes_received"] += len(data)
            content_type = str(response.headers.get("content-type", ""))
            has_cookie = any(str(name).lower() == "set-cookie" for name in response.headers)
            size = len(data)

            if (
                key is not None
                and self.HTML_CONTENT_TYPE_RE.search(content_type)
                and not has_cookie
                and size <= state["max_entry_bytes"]
                and size <= state["max_bytes"]
            ):
                old = cache.pop(key, None)
                if old:
                    state["cached_bytes"] -= old[1]
                while cache and (
                    len(cache) >= state["max_entries"]
                    or state["cached_bytes"] + size > state["max_bytes"]
                ):
                    _, (_, removed_size) = cache.popitem(last=False)
                    state["cached_bytes"] -= removed_size
                cache[key] = (text, size)
                state["cached_bytes"] += size

        return text

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str],
        connect_timeout: float,
        read_timeout: float,
    ) -> dict[str, Any]:
        response = self.session.post(
            url,
            json=payload,
            headers=headers,
            timeout=(connect_timeout, read_timeout),
            allow_redirects=True,
            proxies=self._proxies(),
        )
        response.raise_for_status()
        if not response.text:
            raise ValueError("empty response")
        return response.json()

    def post_form_text(
        self,
        url: str,
        data: dict[str, str],
        *,
        headers: dict[str, str],
        connect_timeout: float,
        read_timeout: float,
    ) -> str:
        response = self.session.post(
            url,
            data=data,
            headers=headers,
            timeout=(connect_timeout, read_timeout),
            allow_redirects=True,
            proxies=self._proxies(),
        )
        response.raise_for_status()
        return response.text
