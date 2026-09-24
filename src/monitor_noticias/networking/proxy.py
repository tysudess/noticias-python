from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import requests

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.platform.credentials import (
    CredentialStoreUnavailable,
    create_proxy_secret_store,
    credential_backend_label,
)


log = logging.getLogger(__name__)

DEFAULT_PROXY_HOST = "proxy-7dn.mb"
LEGACY_PROXY_HOST = "proxy-7db.mb"
DEFAULT_PROXY_PORT = 6060
PROXY_TEST_URL = "https://www.google.com/generate_204"
PROXY_TEST_USER_AGENT = "Mozilla/5.0 MonitorDeNoticias/4.0.2"


class SecretStore(Protocol):
    def exists(self) -> bool: ...
    def save(self, text: str) -> None: ...
    def load(self) -> str: ...
    def delete(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    enabled: bool = False
    host: str = DEFAULT_PROXY_HOST
    port: int = DEFAULT_PROXY_PORT
    username: str = ""
    password: str = field(default="", repr=False)

    @property
    def ready(self) -> bool:
        return (
            self.enabled
            and bool(self.host.strip())
            and 1 <= self.port <= 65535
            and bool(self.username)
            and bool(self.password)
        )

    @property
    def status_label(self) -> str:
        if not self.enabled:
            return "Proxy desativado"
        return "Proxy pronto" if self.ready else "Proxy requer configuração"


class ProxySettings:
    """Proxy Geral com credenciais protegidas por plataforma."""

    def __init__(
        self,
        prefs: SharedPreferences,
        *,
        secret_store: SecretStore | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.prefs = prefs

        if secret_store is None:
            if data_dir is None:
                raise ValueError(
                    "data_dir é obrigatório quando secret_store "
                    "não é fornecido."
                )

            secret_store = create_proxy_secret_store(
                Path(data_dir)
            )

        self.secret_store = secret_store

    @property
    def secure_backend_label(self) -> str:
        return credential_backend_label()

    def migrate_host(self) -> None:
        saved = (
            self.prefs.get_string(
                "desktop_proxy_host",
                "",
            )
            or ""
        ).strip()

        if (
            not saved
            or saved.lower() == LEGACY_PROXY_HOST.lower()
        ):
            self.prefs.update(
                desktop_proxy_host=DEFAULT_PROXY_HOST
            )

    def _migrate_legacy_plaintext_password(self) -> None:
        legacy = (
            self.prefs.get_string(
                "desktop_proxy_password",
                "",
            )
            or ""
        )

        if not legacy:
            return

        try:
            self.secret_store.save(legacy)
            log.info(
                "Senha legada do proxy migrada para "
                "armazenamento seguro (%s).",
                self.secure_backend_label,
            )
        except Exception:
            log.exception(
                "Não foi possível migrar a senha legada "
                "para o cofre seguro; o plaintext será descartado."
            )
        finally:
            self.prefs.update(
                desktop_proxy_password=None
            )

    def _load_password(self) -> str:
        try:
            if not self.secret_store.exists():
                return ""
            return self.secret_store.load()

        except CredentialStoreUnavailable as exc:
            log.warning(
                "Cofre seguro de credenciais indisponível: %s",
                exc,
            )
            return ""

        except Exception:
            log.exception(
                "Falha inesperada ao carregar a senha do Proxy Geral."
            )
            return ""

    def load(self) -> ProxyConfig:
        self.migrate_host()
        self._migrate_legacy_plaintext_password()

        host = (
            self.prefs.get_string(
                "desktop_proxy_host",
                DEFAULT_PROXY_HOST,
            )
            or ""
        ).strip() or DEFAULT_PROXY_HOST

        port = self.prefs.get_int(
            "desktop_proxy_port",
            DEFAULT_PROXY_PORT,
        )
        port = max(1, min(65535, port))

        return ProxyConfig(
            enabled=self.prefs.get_boolean(
                "desktop_proxy_enabled",
                False,
            ),
            host=host,
            port=port,
            username=(
                self.prefs.get_string(
                    "desktop_proxy_username",
                    "",
                )
                or ""
            ),
            password=self._load_password(),
        )

    def save(
        self,
        *,
        enabled: bool,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> ProxyConfig:
        clean_host = host.strip() or DEFAULT_PROXY_HOST
        clean_port = max(1, min(65535, int(port)))
        clean_user = username.strip()

        if password:
            self.secret_store.save(password)
        else:
            self.secret_store.delete()

        self.prefs.update(
            desktop_proxy_enabled=enabled,
            desktop_proxy_host=clean_host,
            desktop_proxy_port=clean_port,
            desktop_proxy_username=clean_user,
            desktop_proxy_password=None,
        )

        return self.load()

    def requests_proxies(
        self,
        config: ProxyConfig | None = None,
    ) -> dict[str, str] | None:
        cfg = config or self.load()

        if not cfg.enabled:
            return None

        if cfg.username and cfg.password:
            user = quote(cfg.username, safe="")
            password = quote(cfg.password, safe="")
            authority = (
                f"{user}:{password}@{cfg.host}:{cfg.port}"
            )
        else:
            authority = f"{cfg.host}:{cfg.port}"

        url = f"http://{authority}"

        return {
            "http": url,
            "https": url,
        }

    def test_connection(
        self,
        *,
        session: requests.Session | None = None,
    ) -> tuple[bool, str]:
        cfg = self.load()

        if not cfg.enabled:
            return False, "Ative o proxy antes de testar."

        if not cfg.ready:
            return False, "Informe usuário e senha do proxy."

        client = session or requests.Session()

        try:
            response = client.get(
                PROXY_TEST_URL,
                headers={
                    "User-Agent": PROXY_TEST_USER_AGENT
                },
                timeout=12,
                allow_redirects=True,
                proxies=self.requests_proxies(cfg),
            )

            if 200 <= response.status_code <= 399:
                return (
                    True,
                    "Conexão pelo proxy realizada com sucesso.",
                )

            return (
                False,
                f"Proxy respondeu HTTP {response.status_code}.",
            )

        except requests.exceptions.SSLError:
            return (
                False,
                (
                    "O proxy respondeu, mas o certificado HTTPS "
                    "corporativo não é confiável no sistema. "
                    "A Central já tenta usar os certificados nativos "
                    "do Windows/Ubuntu. Se esta mensagem continuar, "
                    "instale a CA raiz da organização no repositório "
                    "de certificados confiáveis do sistema."
                ),
            )

        except Exception as exc:
            detail = str(exc) or exc.__class__.__name__

            if cfg.password:
                detail = (
                    detail
                    .replace(cfg.password, "***")
                    .replace(
                        quote(
                            cfg.password,
                            safe="",
                        ),
                        "***",
                    )
                )

            return False, f"Falha no proxy: {detail}"
