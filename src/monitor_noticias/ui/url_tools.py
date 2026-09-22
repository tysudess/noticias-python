from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

import requests
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.google_news_resolver import (
    GoogleNewsUrlResolver,
    is_google_news,
)
from monitor_noticias.networking.http_client import HttpClient
from monitor_noticias.networking.proxy import ProxySettings


_SUCCESS_CACHE: dict[
    str,
    str,
] = {}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language":
        "pt-BR,pt;q=0.9,"
        "en-US;q=0.8,en;q=0.7",
}


@lru_cache(
    maxsize=1
)
def _proxy_settings() -> ProxySettings:
    paths = (
        AppPaths.discover()
    )

    prefs = (
        SharedPreferences(
            paths.data
            / "prefs"
            / "monitor_prefs.properties"
        )
    )

    return ProxySettings(
        prefs,
        data_dir=paths.data,
    )


@lru_cache(
    maxsize=1
)
def _resolver() -> GoogleNewsUrlResolver:
    settings = (
        _proxy_settings()
    )

    http = (
        HttpClient
        .from_proxy_settings(
            settings
        )
    )

    return GoogleNewsUrlResolver(
        http
    )


def _safe_redirect_resolution(
    url: str,
) -> str | None:
    """Último fallback: segue somente redirects HTTP reais.

    Não caça links arbitrários dentro do HTML, portanto não existe o risco de
    devolver analytics.js, anúncios ou recursos estáticos como URL da matéria.
    """

    settings = (
        _proxy_settings()
    )

    try:
        config = (
            settings.load()
        )

        with requests.Session() as session:
            # Proxy Geral ativo = não herdar outro proxy do ambiente Windows.
            session.trust_env = (
                not config.enabled
            )

            response = (
                session.get(
                    url,
                    headers=_HEADERS,
                    timeout=(
                        8,
                        15,
                    ),
                    allow_redirects=True,
                    proxies=(
                        settings.requests_proxies(
                            config
                        )
                        if config.enabled
                        else None
                    ),
                )
            )

            final_url = str(
                response.url
                or ""
            ).strip()

            if (
                final_url.startswith(
                    (
                        "http://",
                        "https://",
                    )
                )
                and not is_google_news(
                    final_url
                )
            ):
                return final_url

    except Exception:
        pass

    return None


def resolve_article_url(
    url: str,
) -> str:
    """Retorna a URL real do veículo para links vindos do Google News.

    V36:
    - usa GoogleNewsUrlResolver robusto;
    - respeita o Proxy Geral/DPAPI;
    - não memoriza falhas;
    - tenta redirect HTTP real como fallback;
    - nunca procura hrefs genéricos no HTML.
    """

    url = str(
        url or ""
    ).strip()

    if not url:
        return url

    if not is_google_news(
        url
    ):
        return url

    cached = (
        _SUCCESS_CACHE.get(
            url
        )
    )

    if cached:
        return cached

    try:
        resolved = (
            _resolver()
            .resolve(
                url
            )
        )
    except Exception:
        resolved = url

    if (
        resolved
        and not is_google_news(
            resolved
        )
    ):
        _SUCCESS_CACHE[url] = (
            resolved
        )
        return resolved

    redirected = (
        _safe_redirect_resolution(
            url
        )
    )

    if (
        redirected
        and not is_google_news(
            redirected
        )
    ):
        _SUCCESS_CACHE[url] = (
            redirected
        )
        return redirected

    # Não grava a falha em cache.
    return url


def copy_article_url(
    url: str,
) -> str:
    resolved = (
        resolve_article_url(
            url
        )
    )

    QApplication.clipboard().setText(
        resolved
    )

    return resolved


def open_article_url(
    url: str,
) -> None:
    resolved = (
        resolve_article_url(
            url
        )
    )

    if resolved:
        QDesktopServices.openUrl(
            QUrl(
                resolved
            )
        )


def open_whatsapp(
    title: str,
    url: str,
) -> None:
    resolved = (
        resolve_article_url(
            url
        )
    )

    text = quote(
        f"{title}\n{resolved}"
    )

    QDesktopServices.openUrl(
        QUrl(
            "https://wa.me/?text="
            + text
        )
    )
