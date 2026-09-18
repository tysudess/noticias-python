from __future__ import annotations

import json
import re
from urllib.parse import quote, urlparse

import requests
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication


_CACHE: dict[str, str] = {}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.6",
}


def _is_google_news(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host == "news.google.com" or host.endswith(".news.google.com")


def _article_id(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")
    return path[-1] if path else ""


def _decode_google_news(url: str) -> str | None:
    article_id = _article_id(url)
    if not article_id:
        return None

    # 1) Obtém assinatura e timestamp da página do Google News.
    try:
        response = requests.get(
            f"https://news.google.com/rss/articles/{article_id}",
            headers=_HEADERS,
            timeout=(5, 10),
        )
        response.raise_for_status()
        page = response.text or ""
    except Exception:
        return None

    sg_match = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
    ts_match = re.search(r'data-n-a-ts=["\']([^"\']+)', page)

    if not sg_match or not ts_match:
        # Alguns links respondem melhor sem /rss/.
        try:
            response = requests.get(
                f"https://news.google.com/articles/{article_id}",
                headers=_HEADERS,
                timeout=(5, 10),
            )
            response.raise_for_status()
            page = response.text or ""
            sg_match = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
            ts_match = re.search(r'data-n-a-ts=["\']([^"\']+)', page)
        except Exception:
            return None

    if not sg_match or not ts_match:
        return None

    signature = sg_match.group(1)
    timestamp = ts_match.group(1)

    request_body = (
        '["garturlreq",'
        '[["X","X",["X","X"],null,null,1,1,"BR:pt-419",null,1,'
        'null,null,null,null,null,0,1],'
        '"pt-BR","BR",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{article_id}",{timestamp},"{signature}"]'
    )

    articles_req = ["Fbv4je", request_body]
    payload = "f.req=" + quote(
        json.dumps([[articles_req]], separators=(",", ":"))
    )

    try:
        response = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            params={"rpcids": "Fbv4je"},
            headers={
                **_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Referer": "https://news.google.com/",
            },
            data=payload,
            timeout=(5, 12),
        )
        response.raise_for_status()
        text = response.text or ""
    except Exception:
        return None

    # Formato atual mais comum.
    marker = '[\\"garturlres\\",\\"'
    if marker in text:
        candidate = text.split(marker, 1)[1].split('\\",', 1)[0]
        candidate = candidate.replace(r"\/", "/")
        try:
            candidate = bytes(candidate, "utf-8").decode("unicode_escape")
        except Exception:
            pass

        if candidate.startswith(("http://", "https://")):
            host = (urlparse(candidate).hostname or "").lower()
            if "google." not in host and "gstatic." not in host:
                return candidate

    # Formato JSON aninhado usado por algumas respostas.
    try:
        chunks = [x for x in text.split("\n\n") if x.strip()]
        for chunk in chunks:
            if chunk.startswith(")]}'"):
                chunk = chunk[4:].lstrip()
            parsed = json.loads(chunk)

            stack = [parsed]
            while stack:
                value = stack.pop()

                if isinstance(value, list):
                    stack.extend(value)
                elif isinstance(value, dict):
                    stack.extend(value.values())
                elif isinstance(value, str):
                    if value.startswith(("http://", "https://")):
                        host = (urlparse(value).hostname or "").lower()
                        if "google." not in host and "gstatic." not in host:
                            return value

                    if value.startswith(("[", "{")):
                        try:
                            stack.append(json.loads(value))
                        except Exception:
                            pass
    except Exception:
        pass

    return None


def resolve_article_url(url: str) -> str:
    """Resolve Google News para o link direto do veículo.

    Se o Google não permitir resolver o token, conserva o link original.
    Nunca procura hrefs arbitrários da página, evitando copiar analytics.js.
    """
    if not url:
        return url

    cached = _CACHE.get(url)
    if cached:
        return cached

    if not _is_google_news(url):
        _CACHE[url] = url
        return url

    resolved = _decode_google_news(url) or url
    _CACHE[url] = resolved
    return resolved


def copy_article_url(url: str) -> str:
    resolved = resolve_article_url(url)
    QApplication.clipboard().setText(resolved)
    return resolved


def open_article_url(url: str) -> None:
    resolved = resolve_article_url(url)
    if resolved:
        QDesktopServices.openUrl(QUrl(resolved))


def open_whatsapp(title: str, url: str) -> None:
    resolved = resolve_article_url(url)
    text = quote(f"{title}\n{resolved}")
    QDesktopServices.openUrl(QUrl("https://wa.me/?text=" + text))
