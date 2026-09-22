from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import (
    ProxyConfig,
    ProxySettings,
)

from .config import ACCESS_KEY


ANDROID_FEED_UA = "PrincipaisCapas/0.7.0 Android"
IMAGE_UA = "Mozilla/5.0 (Android) PrincipaisCapas/0.7.5.0"

# ---------------------------------------------------------------------
# PROXY GERAL DO CENTRAL
# ---------------------------------------------------------------------

_central_proxy_settings: ProxySettings | None = None
_central_proxy_config: ProxyConfig | None = None


def _get_central_proxy_settings() -> ProxySettings:
    """Abre exatamente a mesma configuração de proxy usada pelo Central.

    A senha continua sendo lida pelo ProxySettings/DPAPI; este módulo não cria
    uma segunda configuração e não grava credenciais.
    """
    global _central_proxy_settings

    if _central_proxy_settings is None:
        paths = AppPaths.discover()

        prefs = SharedPreferences(
            paths.data
            / "prefs"
            / "monitor_prefs.properties"
        )

        _central_proxy_settings = ProxySettings(
            prefs,
            data_dir=paths.data,
        )

    return _central_proxy_settings


def _apply_qt_application_proxy(
    config: ProxyConfig,
) -> None:
    """Aplica o proxy geral também ao Qt WebEngine/Chromium.

    O módulo Capas usa QWebEngineView para:
    - Apps Script fallback;
    - links "Ver página";
    - FrontPages / Washington Post / Valor.

    Qt WebEngine usa QNetworkProxy.applicationProxy(), portanto precisamos
    alimentar o Chromium com o MESMO proxy/usuário/senha do Central.
    """
    try:
        from PySide6.QtNetwork import QNetworkProxy

        if config.enabled:
            proxy = QNetworkProxy(
                QNetworkProxy.ProxyType.HttpProxy,
                config.host,
                int(config.port),
                config.username,
                config.password,
            )
        else:
            # Proxy geral desligado = conexão direta para o WebEngine.
            proxy = QNetworkProxy(
                QNetworkProxy.ProxyType.NoProxy
            )

        QNetworkProxy.setApplicationProxy(
            proxy
        )

    except Exception:
        # Requests continua funcionando mesmo se QtNetwork não estiver
        # disponível em algum teste/ambiente reduzido.
        pass


def refresh_central_proxy() -> ProxyConfig:
    """Relê a configuração atual e sincroniza requests + Qt WebEngine."""
    global _central_proxy_config

    settings = (
        _get_central_proxy_settings()
    )

    config = settings.load()
    _central_proxy_config = config

    _apply_qt_application_proxy(
        config
    )

    return config


def central_proxy_config() -> ProxyConfig:
    """Configuração atual do proxy geral, sempre relida do disco."""
    return refresh_central_proxy()


def _central_requests_proxies(
    config: ProxyConfig,
) -> dict[str, str] | None:
    if not config.enabled:
        return None

    if not config.ready:
        raise RuntimeError(
            "Proxy geral está ativo, mas usuário/senha "
            "não estão completos em Configurações."
        )

    return (
        _get_central_proxy_settings()
        .requests_proxies(config)
    )


def _sanitize_proxy_error(
    exc: Exception,
    config: ProxyConfig | None,
) -> str:
    detail = (
        str(exc)
        or exc.__class__.__name__
    )

    if config is None:
        return detail

    # Nunca deixa a senha do proxy aparecer no status/log da interface.
    if config.password:
        detail = detail.replace(
            config.password,
            "***",
        )
        detail = detail.replace(
            quote(
                config.password,
                safe="",
            ),
            "***",
        )

    return detail


def _requests_get_text_via_central_proxy(
    url: str,
    *,
    headers: dict | None,
    connect_timeout: int,
    read_timeout: int,
    config: ProxyConfig,
) -> str:
    proxies = (
        _central_requests_proxies(
            config
        )
    )

    with requests.Session() as session:
        # CRÍTICO:
        # não herdar HTTP_PROXY/HTTPS_PROXY do Windows/ambiente quando o
        # Proxy Geral do Central está ativo. Na versão anterior isso fazia a
        # requisição cair no proxy corporativo sem as credenciais do Central,
        # gerando 407 AutenticacaoNecessaria.
        session.trust_env = False

        response = session.get(
            url,
            timeout=(
                connect_timeout,
                read_timeout,
            ),
            headers=headers or {},
            allow_redirects=True,
            proxies=proxies,
        )

        if (
            response.status_code < 200
            or response.status_code >= 300
        ):
            raise RuntimeError(
                f"HTTP {response.status_code}"
            )

        return (
            response.text
            or ""
        ).strip()


# Sincroniza o WebEngine assim que o módulo Capas é carregado.
# Qualquer chamada posterior relê as preferências para refletir mudanças.
try:
    refresh_central_proxy()
except Exception:
    pass


# ---------------------------------------------------------------------
# REDE DO PRINCIPAIS CAPAS
# ---------------------------------------------------------------------


def _valid_webapp_url(
    url: str,
) -> bool:
    u = (
        url
        or ""
    ).strip().lower()

    return (
        u.startswith(
            "https://script.google.com/macros/s/"
        )
        and "/exec" in u
    )


def _powershell_get_text(
    url: str,
    headers: dict | None = None,
    timeout_sec: int = 22,
) -> str:
    """Fallback Windows nativo.

    IMPORTANTE:
    só é usado quando o Proxy Geral do Central está DESATIVADO.
    Com o proxy geral ativo usamos requests + credenciais explícitas.
    """
    if os.name != "nt":
        raise RuntimeError(
            "PowerShell disponível apenas no Windows"
        )

    env = os.environ.copy()
    env["PC_HTTP_URL"] = url
    env["PC_HTTP_UA"] = str(
        (headers or {}).get(
            "User-Agent"
        )
        or ANDROID_FEED_UA
    )

    script = (
        "$ProgressPreference='SilentlyContinue';"
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$h=@{'User-Agent'=$env:PC_HTTP_UA;"
        "'Accept'='application/json,text/plain,*/*'};"
        f"$r=Invoke-WebRequest -UseBasicParsing "
        f"-Uri $env:PC_HTTP_URL "
        f"-TimeoutSec {int(timeout_sec)} "
        "-Headers $h;"
        "[Console]::Out.Write($r.Content)"
    )

    flags = getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0,
    )

    cp = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout_sec + 8,
        creationflags=flags,
    )

    if cp.returncode != 0:
        err = (
            cp.stderr
            or cp.stdout
            or "falha no PowerShell"
        ).strip().replace(
            "\r",
            " ",
        ).replace(
            "\n",
            " ",
        )

        raise RuntimeError(
            err[:280]
        )

    body = (
        cp.stdout
        or ""
    ).strip()

    if not body:
        raise RuntimeError(
            "PowerShell retornou resposta vazia"
        )

    return body


def get_text_windows(
    url: str,
    headers: dict | None = None,
    connect_timeout: int = 5,
    read_timeout: int = 18,
) -> str:
    """Rede robusta para o Portable.

    Se o Proxy Geral estiver ATIVO:
      1) usa SOMENTE o proxy do Central;
      2) usa usuário/senha salvos por DPAPI;
      3) ignora proxy do ambiente/Windows;
      4) não faz fallback silencioso para conexão direta.

    Se o Proxy Geral estiver DESATIVADO:
      mantém o comportamento legado:
      PowerShell/Windows -> requests ambiente -> requests direto.
    """
    config: ProxyConfig | None = None

    try:
        config = refresh_central_proxy()
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível ler o Proxy Geral do Central: "
            + str(exc)
        ) from exc

    if config.enabled:
        try:
            return (
                _requests_get_text_via_central_proxy(
                    url,
                    headers=headers,
                    connect_timeout=connect_timeout,
                    read_timeout=read_timeout,
                    config=config,
                )
            )

        except Exception as exc:
            detail = (
                _sanitize_proxy_error(
                    exc,
                    config,
                )
            )

            raise RuntimeError(
                "Proxy geral do Central: "
                + detail
            ) from exc

    errors: list[str] = []

    if os.name == "nt":
        try:
            return _powershell_get_text(
                url,
                headers=headers,
                timeout_sec=max(
                    12,
                    read_timeout,
                ),
            )

        except Exception as exc:
            errors.append(
                "Windows: "
                + str(exc)
            )

    for trust_env, label in (
        (True, "proxy/sistema"),
        (False, "direto"),
    ):
        try:
            with requests.Session() as session:
                session.trust_env = (
                    trust_env
                )

                response = session.get(
                    url,
                    timeout=(
                        connect_timeout,
                        read_timeout,
                    ),
                    headers=headers or {},
                    allow_redirects=True,
                )

                if (
                    response.status_code < 200
                    or response.status_code >= 300
                ):
                    raise RuntimeError(
                        f"HTTP {response.status_code}"
                    )

                return (
                    response.text
                    or ""
                ).strip()

        except Exception as exc:
            errors.append(
                label
                + ": "
                + str(exc)
            )

    raise RuntimeError(
        " | ".join(
            errors[-3:]
        )
    )


def fetch_matters(
    apps_script_url: str,
    target_date: date,
) -> tuple[
    dict[str, list[str]],
    dict,
]:
    """Port do ClippingFeedClient.fetchMatterUrls do Android."""
    base = (
        apps_script_url
        or ""
    ).strip()

    if not base:
        raise RuntimeError(
            "Gmail automático não configurado"
        )

    if not _valid_webapp_url(base):
        raise RuntimeError(
            "URL inválida do Apps Script"
        )

    params = {
        "key": ACCESS_KEY,
        "action": "matters",
        "date": target_date.isoformat(),
    }

    url = (
        base
        + (
            "&"
            if "?" in base
            else "?"
        )
        + urlencode(params)
    )

    try:
        body = get_text_windows(
            url,
            headers={
                "User-Agent":
                    ANDROID_FEED_UA,
                "Accept":
                    "application/json,text/plain,*/*",
            },
            connect_timeout=5,
            read_timeout=18,
        )

    except Exception as exc:
        raise RuntimeError(
            f"Ponte Gmail: {exc}"
        ) from exc

    low = body[:120].lower()

    if (
        low.startswith("<!doctype")
        or low.startswith("<html")
    ):
        raise RuntimeError(
            "A ponte abriu HTML. Atualize a implantação "
            "do Apps Script e mantenha acesso como Qualquer pessoa."
        )

    try:
        root = json.loads(body)

    except Exception as exc:
        raise RuntimeError(
            "Resposta inválida da ponte Gmail"
        ) from exc

    if not root.get("ok"):
        raise RuntimeError(
            root.get("error")
            or "Falha na ponte Gmail"
        )

    out: dict[
        str,
        list[str],
    ] = {}

    for item in (
        root.get("matters")
        or []
    ):
        name = str(
            item.get("name")
            or ""
        ).strip()

        matter_url = str(
            item.get("matterUrl")
            or ""
        ).strip()

        if not name or not matter_url:
            continue

        arr = out.setdefault(
            name,
            [],
        )

        if matter_url not in arr:
            arr.append(
                matter_url
            )

    if not out:
        threads = int(
            root.get("threads")
            or 0
        )
        messages = int(
            root.get(
                "messagesScanned"
            )
            or 0
        )
        raw_links = int(
            root.get(
                "rawLeiaMaisFound"
            )
            or 0
        )
        dated = int(
            root.get(
                "datedItemsMatched"
            )
            or 0
        )

        if (
            threads == 0
            or messages == 0
        ):
            raise RuntimeError(
                "A ponte está ativa, mas não encontrou "
                "e-mails de capas aceitos "
                "(ex.: 'Monitoramento: Capa(s) de Jornais' "
                "ou 'CAPA DE JORNAIS 1 APP') "
                "para a data selecionada"
            )

        if raw_links == 0:
            raise RuntimeError(
                "Os e-mails foram encontrados, "
                "mas nenhum link 'Leia mais' foi localizado"
            )

        if dated == 0:
            raise RuntimeError(
                "Há links 'Leia mais', "
                "mas nenhum corresponde à data selecionada"
            )

        raise RuntimeError(
            "Nenhuma capa compatível foi classificada "
            "no Gmail para a data selecionada"
        )

    return out, root


def download_image(
    url: str,
    dest: Path,
    referer: str = "",
    cookie_header: str = "",
    user_agent: str = IMAGE_UA,
) -> Path:
    """Baixa a imagem usando o Proxy Geral quando estiver ativo."""
    headers = {
        "User-Agent":
            user_agent
            or IMAGE_UA,
        "Accept":
            "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }

    if referer:
        headers["Referer"] = (
            referer
        )

    if cookie_header:
        headers["Cookie"] = (
            cookie_header
        )

    config = refresh_central_proxy()
    proxies = None

    if config.enabled:
        proxies = (
            _central_requests_proxies(
                config
            )
        )

    with requests.Session() as session:
        # Ativo = ignora proxy herdado do Windows e usa exatamente o Central.
        # Desativado = preserva a rede normal do usuário.
        session.trust_env = (
            not config.enabled
        )

        try:
            response_context = session.get(
                url,
                timeout=(7, 18),
                headers=headers,
                stream=True,
                allow_redirects=True,
                proxies=proxies,
            )

        except Exception as exc:
            detail = (
                _sanitize_proxy_error(
                    exc,
                    config,
                )
            )

            prefix = (
                "Proxy geral do Central: "
                if config.enabled
                else ""
            )

            raise RuntimeError(
                prefix
                + detail
            ) from exc

        with response_context as response:
            response.raise_for_status()

            ctype = (
                response.headers.get(
                    "Content-Type"
                )
                or ""
            ).lower()

            if "html" in ctype:
                raise RuntimeError(
                    "O endereço retornou HTML "
                    "em vez da imagem da página."
                )

            dest.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            total = 0

            with open(
                dest,
                "wb",
            ) as file_handle:
                for chunk in (
                    response.iter_content(
                        32 * 1024
                    )
                ):
                    if not chunk:
                        continue

                    file_handle.write(
                        chunk
                    )
                    total += len(chunk)

                    if (
                        total
                        > 60
                        * 1024
                        * 1024
                    ):
                        raise RuntimeError(
                            "imagem maior que 60 MB"
                        )

    if dest.stat().st_size < 8192:
        raise RuntimeError(
            "arquivo de imagem vazio/placeholder"
        )

    return dest


def safe_slug(
    name: str,
) -> str:
    import unicodedata

    value = (
        unicodedata.normalize(
            "NFD",
            name,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode()
        .lower()
    )

    value = re.sub(
        r"[^a-z0-9]+",
        "-",
        value,
    ).strip("-")

    return (
        value
        or "capa"
    )
