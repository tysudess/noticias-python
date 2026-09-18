from __future__ import annotations

import base64
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
        "Chrome/131 Safari/537.36"
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


def _old_style_decode(article_id: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(article_id + "===")
    except Exception:
        return None

    match = re.search(rb"https?://[^\x00\s]+", raw)
    if not match:
        return None

    try:
        decoded = match.group(0).decode("utf-8", errors="ignore")
    except Exception:
        return None

    return decoded if decoded.startswith(("http://", "https://")) else None


def _walk_find_url(value) -> str | None:
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            host = (urlparse(value).hostname or "").lower()
            if host and "google." not in host and "gstatic." not in host:
                return value

        stripped = value.strip()
        if stripped.startswith(("[", "{")):
            try:
                nested = json.loads(stripped)
            except Exception:
                nested = None
            if nested is not None:
                found = _walk_find_url(nested)
                if found:
                    return found

    elif isinstance(value, list):
        for item in value:
            found = _walk_find_url(item)
            if found:
                return found

    elif isinstance(value, dict):
        for item in value.values():
            found = _walk_find_url(item)
            if found:
                return found

    return None


def _decode_with_batchexecute(article_id: str) -> str | None:
    session = requests.Session()

    page_urls = (
        f"https://news.google.com/rss/articles/{article_id}",
        f"https://news.google.com/articles/{article_id}",
    )

    signature = ""
    timestamp = ""

    for page_url in page_urls:
        try:
            response = session.get(
                page_url,
                headers=_HEADERS,
                timeout=(6, 12),
                allow_redirects=True,
            )
            response.raise_for_status()
            page = response.text or ""

            sg = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
            ts = re.search(r'data-n-a-ts=["\']([^"\']+)', page)

            if sg and ts:
                signature = sg.group(1)
                timestamp = ts.group(1)
                break
        except Exception:
            continue

    if not signature or not timestamp:
        return None

    inner = (
        '["garturlreq",'
        '[["X","X",["X","X"],null,null,1,1,"BR:pt-419",null,1,'
        'null,null,null,null,null,0,1],'
        '"pt-BR","BR",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{article_id}",{timestamp},"{signature}"]'
    )

    request_item = ["Fbv4je", inner, None, "generic"]
    payload = {"f.req": json.dumps([[request_item]], separators=(",", ":"))}

    try:
        response = session.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            params={"rpcids": "Fbv4je"},
            headers={
                **_HEADERS,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Referer": "https://news.google.com/",
            },
            data=payload,
            timeout=(6, 14),
        )
        response.raise_for_status()
    except Exception:
        return None

    text = response.text or ""

    for block in text.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(")]}'"):
            continue

        try:
            parsed = json.loads(block)
        except Exception:
            continue

        found = _walk_find_url(parsed)
        if found:
            return found

    for pattern in (
        r'\[\\"garturlres\\",\\"(https?:[^"\\]+)',
        r'\["garturlres","(https?://[^"]+)',
    ):
        match = re.search(pattern, text)
        if not match:
            continue

        candidate = match.group(1).replace(r"\/", "/")

        try:
            candidate = bytes(candidate, "utf-8").decode("unicode_escape")
        except Exception:
            pass

        host = (urlparse(candidate).hostname or "").lower()
        if host and "google." not in host and "gstatic." not in host:
            return candidate

    return None


def resolve_article_url(url: str) -> str:
    if not url:
        return url

    cached = _CACHE.get(url)
    if cached:
        return cached

    if not _is_google_news(url):
        _CACHE[url] = url
        return url

    article_id = _article_id(url)

    direct = _old_style_decode(article_id)
    if not direct:
        direct = _decode_with_batchexecute(article_id)

    resolved = direct or url
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
