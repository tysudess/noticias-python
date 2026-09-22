from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urljoin, urlsplit, urlunsplit
import re

from monitor_noticias.capas_tool.app import network as network_module
from monitor_noticias.capas_tool.app import ui as covers_ui
from monitor_noticias.capas_tool.app import web_resolver as web_resolver_module
from monitor_noticias.capas_tool.app.web_resolver_patch import (
    RobustFrontPageResolver,
)
from monitor_noticias.capas_tool.app.workers import Worker


_INSTALLED = False


def _normalize_frontpages_image_url(
    url: str,
) -> str:
    """Normaliza URLs de capa do FrontPages.

    Corrige principalmente o formato observado no Central:
      ...arquivo.webp.jpg

    Isso não é uma URL válida da imagem original e termina em HTTP 404.
    """

    raw = str(
        url or ""
    ).strip()

    if not raw:
        return ""

    try:
        parts = urlsplit(raw)
        path = parts.path or ""

        path = re.sub(
            r"(?i)\.webp\.(?:jpe?g|png)$",
            ".webp",
            path,
        )

        path = re.sub(
            r"(?i)\.(?:jpe?g|png)\.webp$",
            ".webp",
            path,
        )

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                path,
                parts.query,
                parts.fragment,
            )
        )

    except Exception:
        return re.sub(
            r"(?i)\.webp\.(?:jpe?g|png)(?=$|[?#])",
            ".webp",
            raw,
        )


def _frontpages_variants(
    url: str,
) -> list[str]:
    """Monta alternativas seguras de extensão para uma mesma capa."""

    original = str(
        url or ""
    ).strip()

    normalized = (
        _normalize_frontpages_image_url(
            original
        )
    )

    out: list[str] = []

    def add(
        value: str,
    ) -> None:
        value = str(
            value or ""
        ).strip()

        if (
            value
            and value not in out
        ):
            out.append(value)

    add(normalized)

    if (
        original
        and original != normalized
    ):
        add(original)

    try:
        parts = urlsplit(
            normalized
        )
        path = parts.path or ""

        match = re.search(
            r"(?i)\.(webp|jpe?g|png)$",
            path,
        )

        if match:
            stem = path[
                :match.start()
            ]

            for extension in (
                ".webp",
                ".jpg",
                ".jpeg",
                ".png",
            ):
                add(
                    urlunsplit(
                        (
                            parts.scheme,
                            parts.netloc,
                            stem
                            + extension,
                            parts.query,
                            parts.fragment,
                        )
                    )
                )

    except Exception:
        pass

    return out


class _FrontPagesImageParser(
    HTMLParser
):
    """Extrai a capa atual do HTML do FrontPages pelo Proxy Geral."""

    def __init__(
        self,
        source_url: str,
        slug: str,
        newspaper_name: str,
    ):
        super().__init__(
            convert_charrefs=True
        )

        self.source_url = source_url
        self.slug = slug
        self.newspaper_name = (
            newspaper_name.upper()
        )

        self.candidates: list[
            tuple[int, str]
        ] = []

    @staticmethod
    def _clean(
        value: str,
    ) -> str:
        value = unescape(
            str(value or "")
        )

        value = (
            value
            .replace(
                "\\/",
                "/",
            )
            .replace(
                "\\u0026",
                "&",
            )
        )

        return value.strip()

    def _push(
        self,
        raw: str,
        score: int,
        context: str = "",
    ) -> None:
        raw = self._clean(
            raw
        )

        if not raw:
            return

        for piece in raw.split(
            ","
        ):
            value = (
                piece
                .strip()
                .split()[0]
                if piece.strip()
                else ""
            )

            if not value:
                continue

            url = urljoin(
                self.source_url,
                value,
            )

            url = (
                _normalize_frontpages_image_url(
                    url
                )
            )

            low = url.lower()
            ctx = str(
                context or ""
            ).lower()

            if not url.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                continue

            if not any(
                ext in low
                for ext in (
                    ".webp",
                    ".jpg",
                    ".jpeg",
                    ".png",
                )
            ):
                continue

            if any(
                token in low
                for token in (
                    "logo",
                    "icon",
                    "avatar",
                    "favicon",
                )
            ):
                continue

            if (
                self.newspaper_name
                == "THE WASHINGTON POST"
                and "sports" in low
            ):
                continue

            local_score = int(
                score
            )

            if (
                f"/{self.slug}-"
                in low
            ):
                local_score += 900

            if self.slug in low:
                local_score += 450

            if "/g/" in low:
                local_score += 350

            if (
                "frontpages.com"
                in low
            ):
                local_score += 120

            if ".webp" in low:
                local_score += 80

            words = [
                item
                for item
                in re.split(
                    r"[^a-z0-9]+",
                    self.slug.lower(),
                )
                if item
                and item != "the"
            ]

            if (
                words
                and all(
                    word in ctx
                    for word in words
                )
            ):
                local_score += 500

            self.candidates.append(
                (
                    local_score,
                    url,
                )
            )

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        data = {
            str(k or "").lower():
                str(v or "")
            for k, v
            in attrs
        }

        tag = str(
            tag or ""
        ).lower()

        if tag == "meta":
            key = (
                data.get(
                    "property"
                )
                or data.get(
                    "name"
                )
                or ""
            ).lower()

            if key in {
                "og:image",
                "og:image:url",
                "twitter:image",
                "twitter:image:src",
            }:
                self._push(
                    data.get(
                        "content",
                        "",
                    ),
                    650,
                    key,
                )

            return

        if tag == "link":
            rel = (
                data.get(
                    "rel",
                    "",
                )
                .lower()
            )

            if (
                "image_src"
                in rel
            ):
                self._push(
                    data.get(
                        "href",
                        "",
                    ),
                    600,
                    rel,
                )

            return

        if tag not in {
            "img",
            "source",
            "a",
        }:
            return

        context = " ".join(
            [
                data.get(
                    "alt",
                    "",
                ),
                data.get(
                    "title",
                    "",
                ),
                data.get(
                    "aria-label",
                    "",
                ),
                data.get(
                    "data-title",
                    "",
                ),
                data.get(
                    "data-caption",
                    "",
                ),
            ]
        )

        for attr in (
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
        ):
            value = data.get(
                attr,
                "",
            )

            if value:
                self._push(
                    value,
                    (
                        300
                        if tag == "img"
                        else 180
                    ),
                    context,
                )

    def best(
        self,
    ) -> str:
        if not self.candidates:
            return ""

        by_url: dict[
            str,
            int,
        ] = {}

        for score, url in (
            self.candidates
        ):
            by_url[url] = max(
                score,
                by_url.get(
                    url,
                    -10_000,
                ),
            )

        ranked = sorted(
            (
                (
                    score,
                    url,
                )
                for url, score
                in by_url.items()
            ),
            reverse=True,
        )

        if not ranked:
            return ""

        score, url = (
            ranked[0]
        )

        if score < 700:
            return ""

        return (
            _normalize_frontpages_image_url(
                url
            )
        )


def _direct_frontpages_url(
    newspaper_name: str,
) -> tuple[str, str]:
    """Localiza a imagem atual usando requests + Proxy Geral."""

    name = str(
        newspaper_name or ""
    ).upper().strip()

    if (
        name
        == "THE WASHINGTON POST"
    ):
        source = (
            "https://www.frontpages.com/"
            "the-washington-post/"
        )
        slug = (
            "the-washington-post"
        )

    elif (
        name
        == "VALOR ECONÔMICO"
    ):
        source = (
            "https://www.frontpages.com/"
            "valor-economico/"
        )
        slug = (
            "valor-economico"
        )

    else:
        return "", ""

    network_module.refresh_central_proxy()

    html = (
        network_module
        .get_text_windows(
            source,
            headers={
                "User-Agent":
                    web_resolver_module
                    .ANDROID_FRONT_UA,
                "Accept":
                    "text/html,"
                    "application/xhtml+xml,"
                    "*/*;q=0.8",
                "Accept-Language":
                    "pt-BR,pt;q=0.9,"
                    "en-US;q=0.8,"
                    "en;q=0.7",
            },
            connect_timeout=8,
            read_timeout=25,
        )
    )

    parser = (
        _FrontPagesImageParser(
            source,
            slug,
            name,
        )
    )

    parser.feed(
        html
    )

    return (
        parser.best(),
        source,
    )


def _install_download_retry_patch() -> None:
    """Corrige `.webp.jpg` e testa a extensão real antes de falhar."""

    original = (
        network_module
        .download_image
    )

    if getattr(
        original,
        "_central_frontpages_v35",
        False,
    ):
        return

    def patched(
        url,
        dest,
        referer="",
        cookie_header="",
        user_agent=network_module.IMAGE_UA,
    ):
        raw = str(
            url or ""
        ).strip()

        if (
            "frontpages.com/"
            not in raw.lower()
        ):
            return original(
                raw,
                dest,
                referer,
                cookie_header=
                    cookie_header,
                user_agent=
                    user_agent,
            )

        errors: list[str] = []

        for candidate in (
            _frontpages_variants(
                raw
            )
        ):
            try:
                return original(
                    candidate,
                    dest,
                    referer,
                    cookie_header=
                        cookie_header,
                    user_agent=
                        user_agent,
                )

            except Exception as exc:
                message = str(
                    exc or ""
                )

                errors.append(
                    message
                )

                low = (
                    message.lower()
                )

                # 407 é problema real de autenticação do Proxy Geral.
                # Não mascaramos tentando extensões diferentes.
                if (
                    "407" in low
                    or "proxy authentication"
                    in low
                    or "autenticacao necessaria"
                    in low
                    or "autenticação necessária"
                    in low
                ):
                    raise RuntimeError(
                        "Proxy Geral recusou a autenticação "
                        "ao acessar o FrontPages: "
                        + message
                    ) from exc

        raise RuntimeError(
            "FrontPages não encontrou a imagem "
            "em nenhuma extensão válida"
            + (
                f" ({errors[-1]})"
                if errors
                else ""
            )
        )

    patched._central_frontpages_v35 = True

    network_module.download_image = (
        patched
    )

    # ui.py importou a função diretamente.
    covers_ui.download_image = (
        patched
    )


def _install_browser_proxy_auth_patch() -> None:
    browser_cls = (
        web_resolver_module
        ._AttachedBrowser
    )

    original_init = (
        browser_cls.__init__
    )

    if getattr(
        original_init,
        "_central_proxy_auth_patch",
        False,
    ):
        return

    def patched_init(
        self,
        owner,
        user_agent,
    ):
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

    browser_cls.__init__ = (
        patched_init
    )

    original_new_page = (
        browser_cls.new_page
    )

    def patched_new_page(
        self,
        captured_callback,
    ):
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
                    network_module
                    .central_proxy_config()
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

        try:
            page.proxyAuthenticationRequired.connect(
                authenticate_proxy
            )
        except Exception:
            pass

        return page

    patched_new_page._central_proxy_auth_patch = True

    browser_cls.new_page = (
        patched_new_page
    )


def _install_robust_resolver_patch() -> None:
    web_resolver_module.Resolver = (
        RobustFrontPageResolver
    )

    covers_ui.Resolver = (
        RobustFrontPageResolver
    )


def _install_direct_frontpages_patch() -> None:
    cls = covers_ui.MainWindow
    original = (
        cls._start_single_web_resolver
    )

    if getattr(
        original,
        "_central_frontpages_v35",
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
        # IMPORTANTE:
        # Este patch NÃO muda a sequência do Valor.
        # A busca inicial continua sendo Gmail em _start_web_branch().
        # Só chegamos aqui depois do fallback web ser acionado.
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
            f"{entry.name}: fallback web • "
            "localizando capa no FrontPages pelo Proxy Geral…"
        )

        self._refresh_list()

        worker = Worker(
            _direct_frontpages_url,
            entry.name,
        )

        def ready(
            result,
            en=entry,
            g=generation,
            done=one_done,
        ):
            if (
                g
                != self.refresh_generation
            ):
                return

            try:
                url, referer = (
                    result
                )
            except Exception:
                url, referer = (
                    "",
                    "",
                )

            url = (
                _normalize_frontpages_image_url(
                    url
                )
            )

            if url:
                resolver = (
                    SimpleNamespace(
                        last_referer=
                            referer,
                        last_cookie_header=
                            "",
                    )
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

            en.status = (
                f"{en.name}: FrontPages não expôs a imagem "
                "• tentando navegador interno…"
            )

            self._refresh_list()

            original(
                self,
                en,
                g,
                done,
                False,
            )

        def error(
            message,
            en=entry,
            g=generation,
            done=one_done,
        ):
            if (
                g
                != self.refresh_generation
            ):
                return

            text = str(
                message or ""
            )

            if (
                "407" in text
                or "autenticação"
                in text.lower()
                or "authentication"
                in text.lower()
            ):
                en.status = (
                    f"{en.name}: Proxy Geral recusou a conexão "
                    f"({text})"
                )
                self._refresh_list()
                done()
                return

            en.status = (
                f"{en.name}: HTTP pelo Proxy Geral não resolveu "
                f"({text}) • tentando navegador interno…"
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
            ready
        )
        worker.signals.error.connect(
            error
        )

        self._start_worker(
            worker
        )

    patched._central_frontpages_v35 = True
    cls._start_single_web_resolver = (
        patched
    )


def _install_valor_gmail_first_patch() -> None:
    """Mantém Gmail como fonte prioritária e melhora o diagnóstico."""

    cls = covers_ui.MainWindow
    original_error = (
        cls._valor_email_error
    )

    if getattr(
        original_error,
        "_central_valor_gmail_v35",
        False,
    ):
        return

    def patched_error(
        self,
        entry,
        message,
        generation,
        one_done,
    ):
        if (
            generation
            != self.refresh_generation
        ):
            return

        text = str(
            message or ""
        )
        upper = text.upper()

        # Um 407 ao consultar o Gmail/Apps Script é proxy, não ausência de PDF.
        if (
            "407" in upper
            or "PROXY AUTHENTICATION"
            in upper
            or "AUTENTICAÇÃO NECESSÁRIA"
            in upper
            or "AUTENTICACAO NECESSARIA"
            in upper
        ):
            entry.status = (
                "Valor: Gmail não pôde ser consultado "
                "porque o Proxy Geral recusou a autenticação • "
                f"{text}"
            )
            self._refresh_list()
            one_done()
            return

        # HTTP 404 da ponte significa que o endpoint valor_manifest/valor_pdf
        # não está presente nessa implantação do Apps Script.
        # Só então seguimos para o fallback web.
        if (
            "HTTP 404"
            in upper
        ):
            entry.status = (
                "Valor: Gmail consultado primeiro • "
                "ponte não possui endpoint PDF nesta implantação "
                "• usando fallback web pelo Proxy Geral…"
            )
            self._refresh_list()

            self._start_single_web_resolver(
                entry,
                generation,
                one_done,
            )
            return

        # Para qualquer outro erro, preserva o comportamento original:
        # Gmail falha -> fallback web.
        return original_error(
            self,
            entry,
            text,
            generation,
            one_done,
        )

    patched_error._central_valor_gmail_v35 = True

    cls._valor_email_error = (
        patched_error
    )


def install_covers_web_proxy_patch() -> None:
    """V35 — Valor Gmail primeiro + FrontPages normalizado + Proxy Geral."""

    global _INSTALLED

    if _INSTALLED:
        return

    _install_download_retry_patch()
    _install_browser_proxy_auth_patch()
    _install_robust_resolver_patch()
    _install_direct_frontpages_patch()
    _install_valor_gmail_first_patch()

    _INSTALLED = True
