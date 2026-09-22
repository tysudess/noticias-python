from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urljoin
import re

from monitor_noticias.capas_tool.app import network as network_module
from monitor_noticias.capas_tool.app import ui as covers_ui
from monitor_noticias.capas_tool.app import web_resolver as web_resolver_module
from monitor_noticias.capas_tool.app.web_resolver_patch import RobustFrontPageResolver
from monitor_noticias.capas_tool.app.workers import Worker


_INSTALLED = False


class _FrontPagesImageParser(HTMLParser):
    """Extrai candidatos de imagem do HTML sem depender do Chromium.

    Isto é importante em rede corporativa porque requests usa explicitamente
    o Proxy Geral do Central, inclusive usuário/senha, enquanto o processo
    Chromium pode ter sido iniciado antes da troca de proxy.
    """

    def __init__(self, source_url: str, slug: str, newspaper_name: str):
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.slug = slug
        self.newspaper_name = newspaper_name.upper()
        self.candidates: list[tuple[int, str]] = []

    @staticmethod
    def _clean(value: str) -> str:
        value = unescape(str(value or ""))
        value = value.replace("\\/", "/").replace("\\u0026", "&")
        return value.strip()

    def _push(self, raw: str, score: int, context: str = "") -> None:
        raw = self._clean(raw)

        if not raw:
            return

        # srcset pode ter mais de uma URL.
        pieces = raw.split(",")

        for piece in pieces:
            value = piece.strip().split()[0] if piece.strip() else ""
            if not value:
                continue

            url = urljoin(self.source_url, value)
            low = url.lower()
            ctx = str(context or "").lower()

            if not url.startswith(("http://", "https://")):
                continue

            if not any(ext in low for ext in (".webp", ".jpg", ".jpeg", ".png")):
                continue

            if any(token in low for token in ("logo", "icon", "avatar", "favicon")):
                continue

            if (
                self.newspaper_name == "THE WASHINGTON POST"
                and "sports" in low
            ):
                continue

            local_score = int(score)

            if f"/{self.slug}-" in low:
                local_score += 900

            if self.slug in low:
                local_score += 450

            if "/g/" in low:
                local_score += 350

            if "frontpages.com" in low:
                local_score += 120

            if ".webp" in low:
                local_score += 80

            expected_words = [
                x for x in re.split(r"[^a-z0-9]+", self.slug.lower())
                if x and x not in {"the"}
            ]

            if expected_words and all(word in ctx for word in expected_words):
                local_score += 500

            self.candidates.append((local_score, url))

    def handle_starttag(self, tag: str, attrs) -> None:
        data = {
            str(k or "").lower(): str(v or "")
            for k, v in attrs
        }

        tag = str(tag or "").lower()

        if tag == "meta":
            key = (
                data.get("property")
                or data.get("name")
                or ""
            ).lower()

            if key in {
                "og:image",
                "og:image:url",
                "twitter:image",
                "twitter:image:src",
            }:
                self._push(
                    data.get("content", ""),
                    650,
                    key,
                )
            return

        if tag == "link":
            rel = data.get("rel", "").lower()
            if "image_src" in rel:
                self._push(
                    data.get("href", ""),
                    600,
                    rel,
                )
            return

        if tag not in {"img", "source", "a"}:
            return

        context = " ".join(
            [
                data.get("alt", ""),
                data.get("title", ""),
                data.get("aria-label", ""),
                data.get("data-title", ""),
                data.get("data-caption", ""),
            ]
        )

        attrs_to_check = (
            "src",
            "href",
            "srcset",
            "data-src",
            "data-srcset",
            "data-lazy-src",
            "data-original",
            "data-image",
            "data-url",
            "data-full",
        )

        for attr in attrs_to_check:
            value = data.get(attr, "")
            if value:
                self._push(
                    value,
                    300 if tag == "img" else 180,
                    context,
                )

    def best(self) -> str:
        if not self.candidates:
            return ""

        # Remove duplicadas mantendo a maior pontuação.
        best_by_url: dict[str, int] = {}

        for score, url in self.candidates:
            best_by_url[url] = max(
                score,
                best_by_url.get(url, -10_000),
            )

        ranked = sorted(
            (
                (score, url)
                for url, score in best_by_url.items()
            ),
            reverse=True,
        )

        if not ranked:
            return ""

        top_score, top_url = ranked[0]

        # Para não confundir banners/og:image genéricos com capa,
        # exigimos algum sinal forte do jornal/estrutura de FrontPages.
        if top_score < 700:
            return ""

        return top_url


def _direct_frontpages_url(newspaper_name: str) -> tuple[str, str]:
    """Busca a capa via requests + Proxy Geral antes de abrir Chromium."""

    name = str(newspaper_name or "").upper().strip()

    if name == "THE WASHINGTON POST":
        source = "https://www.frontpages.com/the-washington-post/"
        slug = "the-washington-post"
    elif name == "VALOR ECONÔMICO":
        source = "https://www.frontpages.com/valor-economico/"
        slug = "valor-economico"
    else:
        return "", ""

    # Relê o proxy a cada busca. Assim uma mudança feita na aba Configurações
    # é usada imediatamente por Capas, sem reiniciar o Central.
    network_module.refresh_central_proxy()

    html = network_module.get_text_windows(
        source,
        headers={
            "User-Agent": web_resolver_module.ANDROID_FRONT_UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        connect_timeout=8,
        read_timeout=25,
    )

    parser = _FrontPagesImageParser(
        source,
        slug,
        name,
    )
    parser.feed(html)

    return parser.best(), source


def _install_browser_proxy_auth_patch() -> None:
    browser_cls = web_resolver_module._AttachedBrowser

    original_init = browser_cls.__init__

    if getattr(
        original_init,
        "_central_proxy_auth_patch",
        False,
    ):
        return

    def patched_init(self, owner, user_agent):
        # O profile WebEngine precisa nascer DEPOIS de sincronizar o proxy.
        try:
            network_module.refresh_central_proxy()
        except Exception:
            pass

        original_init(
            self,
            owner,
            user_agent,
        )

    patched_init._central_proxy_auth_patch = True
    browser_cls.__init__ = patched_init

    original_new_page = browser_cls.new_page

    def patched_new_page(
        self,
        captured_callback,
    ):
        # Sincroniza novamente porque o usuário pode ter alterado o Proxy Geral
        # depois que o resolver foi criado.
        try:
            network_module.refresh_central_proxy()
        except Exception:
            pass

        page = original_new_page(
            self,
            captured_callback,
        )

        def authenticate_proxy(
            _request_url,
            authenticator,
            _proxy_host,
        ):
            try:
                config = (
                    network_module.central_proxy_config()
                )

                if (
                    config.enabled
                    and config.ready
                ):
                    authenticator.setUser(
                        config.username
                    )
                    authenticator.setPassword(
                        config.password
                    )
            except Exception:
                pass

        # QWebEngine possui um canal específico para desafio 407 do proxy.
        # O QNetworkProxy.applicationProxy continua configurado em network.py,
        # e este callback reforça as credenciais quando Chromium pedir.
        try:
            page.proxyAuthenticationRequired.connect(
                authenticate_proxy
            )
        except Exception:
            pass

        return page

    patched_new_page._central_proxy_auth_patch = True
    browser_cls.new_page = patched_new_page


def _install_robust_resolver_patch() -> None:
    # O projeto já contém RobustFrontPageResolver, mas ele não estava sendo
    # ativado pela UI. Tornamos essa implementação a Resolver oficial.
    web_resolver_module.Resolver = (
        RobustFrontPageResolver
    )
    covers_ui.Resolver = (
        RobustFrontPageResolver
    )


def _install_direct_frontpages_patch() -> None:
    cls = covers_ui.MainWindow

    original = cls._start_single_web_resolver

    if getattr(
        original,
        "_central_frontpages_patch",
        False,
    ):
        return

    def patched(
        self,
        entry,
        generation,
        one_done,
        pressreader_only=False,
    ):
        # PressReader continua no resolver Chromium, pois requer DOM/lazy load.
        if (
            pressreader_only
            or entry.name not in {
                "VALOR ECONÔMICO",
                "THE WASHINGTON POST",
            }
        ):
            return original(
                self,
                entry,
                generation,
                one_done,
                pressreader_only,
            )

        entry.status = (
            f"{entry.name}: buscando FrontPages pelo Proxy Geral…"
        )
        self._refresh_list()

        worker = Worker(
            _direct_frontpages_url,
            entry.name,
        )

        def direct_ready(
            result,
            en=entry,
            g=generation,
            done=one_done,
        ):
            if g != self.refresh_generation:
                return

            url = ""
            referer = ""

            try:
                url, referer = result
            except Exception:
                pass

            if url:
                resolver = SimpleNamespace(
                    last_referer=referer,
                    last_cookie_header="",
                )

                self._web_resolved(
                    en,
                    resolver,
                    url,
                    None,
                    g,
                    done,
                )
                return

            # HTML não expôs a imagem: continua no Chromium robusto.
            en.status = (
                f"{en.name}: HTML não expôs a capa • "
                "tentando navegador interno com proxy autenticado…"
            )
            self._refresh_list()

            original(
                self,
                en,
                g,
                done,
                False,
            )

        def direct_error(
            message,
            en=entry,
            g=generation,
            done=one_done,
        ):
            if g != self.refresh_generation:
                return

            en.status = (
                f"{en.name}: busca HTTP não resolveu ({message}) • "
                "tentando navegador interno com proxy autenticado…"
            )
            self._refresh_list()

            original(
                self,
                en,
                g,
                done,
                False,
            )

        worker.signals.finished.connect(
            direct_ready
        )
        worker.signals.error.connect(
            direct_error
        )

        self._start_worker(
            worker
        )

    patched._central_frontpages_patch = True
    cls._start_single_web_resolver = patched


def _install_valor_404_message_patch() -> None:
    cls = covers_ui.MainWindow
    original = cls._valor_email_error

    if getattr(
        original,
        "_central_valor_404_patch",
        False,
    ):
        return

    def patched(
        self,
        entry,
        message,
        generation,
        one_done,
    ):
        text = str(message or "")

        if "HTTP 404" in text.upper():
            if generation != self.refresh_generation:
                return

            # 404 nesta chamada significa que a implantação atual do Apps
            # Script não oferece valor_manifest/valor_pdf. Não é falha de
            # autenticação do Proxy Geral; seguimos direto para FrontPages.
            entry.status = (
                "Valor: ponte Gmail sem endpoint de PDF nesta implantação "
                "• usando FrontPages pelo Proxy Geral…"
            )
            self._refresh_list()

            self._start_single_web_resolver(
                entry,
                generation,
                one_done,
            )
            return

        return original(
            self,
            entry,
            message,
            generation,
            one_done,
        )

    patched._central_valor_404_patch = True
    cls._valor_email_error = patched


def install_covers_web_proxy_patch() -> None:
    """Corrige Valor/Washington Post atrás do Proxy Geral do Central."""

    global _INSTALLED

    if _INSTALLED:
        return

    _install_browser_proxy_auth_patch()
    _install_robust_resolver_patch()
    _install_direct_frontpages_patch()
    _install_valor_404_message_patch()

    _INSTALLED = True
