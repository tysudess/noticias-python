from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import requests

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.extractor import ExtractorEngine, YtDlpUpdater
from monitor_noticias.networking.proxy import ProxyConfig, ProxySettings
from monitor_noticias.ui import extractor_page as extractor_page_module


_INSTALLED = False


def _settings_for(app_root: Path) -> ProxySettings:
    root = Path(app_root)

    prefs = SharedPreferences(
        root
        / "data"
        / "prefs"
        / "monitor_prefs.properties"
    )

    return ProxySettings(
        prefs,
        data_dir=root / "data",
    )


def _proxy_url_for(
    app_root: Path,
) -> tuple[ProxyConfig, str]:
    """Retorna a configuração atual e a URL autenticada do Proxy Geral."""

    settings = _settings_for(
        Path(app_root)
    )

    config = settings.load()

    if not config.enabled:
        return config, ""

    if not config.ready:
        raise RuntimeError(
            "O Proxy Geral está ativado, mas usuário/senha "
            "não estão completos em Configurações."
        )

    proxies = settings.requests_proxies(
        config
    )

    url = (
        (proxies or {}).get("https")
        or (proxies or {}).get("http")
        or ""
    )

    if not url:
        raise RuntimeError(
            "Não foi possível montar a URL do Proxy Geral."
        )

    return config, url


def _safe_proxy_error(
    exc: Exception,
    config: ProxyConfig | None,
) -> str:
    detail = (
        str(exc)
        or exc.__class__.__name__
    )

    if config is None:
        return detail

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


def _install_engine_download_patch() -> None:
    original_download = ExtractorEngine.download

    if getattr(
        original_download,
        "_central_proxy_patch",
        False,
    ):
        return

    def patched_download(
        self,
        url,
        quality,
        proxy="",
        update=lambda _p, _m: None,
    ):
        config = None

        try:
            config, central_proxy = (
                _proxy_url_for(
                    self.app_root
                )
            )

            if config.enabled:
                proxy = central_proxy

                update(
                    0,
                    "Rede: Proxy Geral do Central ativo.",
                )
            else:
                # A interface do Extrator não possui proxy próprio.
                # Se o Proxy Geral estiver desligado, usamos conexão direta.
                proxy = ""

                update(
                    0,
                    "Rede: conexão direta.",
                )

        except Exception as exc:
            raise RuntimeError(
                "Proxy Geral do Central: "
                + _safe_proxy_error(
                    exc,
                    config,
                )
            ) from exc

        return original_download(
            self,
            url,
            quality,
            proxy,
            update,
        )

    patched_download._central_proxy_patch = True
    ExtractorEngine.download = patched_download


def _install_updater_patch() -> None:
    original_update = YtDlpUpdater.update

    if getattr(
        original_update,
        "_central_proxy_patch",
        False,
    ):
        return

    def patched_update(
        self,
        progress=lambda _message: None,
    ):
        from monitor_noticias.extractor.updater import (
            UpdateResult,
        )

        target = self.target
        temp = target.with_name(
            "yt-dlp.update.tmp.exe"
        )
        backup = target.with_name(
            "yt-dlp.backup.exe"
        )

        config = None

        try:
            config, proxy_url = (
                _proxy_url_for(
                    self.engine.app_root
                )
            )

            if config.enabled:
                progress(
                    "Rede: Proxy Geral do Central ativo."
                )
            else:
                progress(
                    "Rede: conexão direta."
                )

            proxies = (
                {
                    "http": proxy_url,
                    "https": proxy_url,
                }
                if proxy_url
                else None
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            progress(
                "Baixando atualização do yt-dlp..."
            )

            with requests.Session() as session:
                # Não herda HTTP_PROXY/HTTPS_PROXY do Windows/terminal.
                # A rede é definida exclusivamente pelo Proxy Geral do Central.
                session.trust_env = False

                with session.get(
                    self.URL,
                    headers={
                        "User-Agent": self.UA,
                    },
                    stream=True,
                    timeout=(30, 60),
                    allow_redirects=True,
                    proxies=proxies,
                ) as response:
                    response.raise_for_status()

                    with temp.open(
                        "wb"
                    ) as output:
                        for chunk in (
                            response.iter_content(
                                256 * 1024
                            )
                        ):
                            if chunk:
                                output.write(
                                    chunk
                                )

            if (
                not temp.exists()
                or temp.stat().st_size
                <= 1_000_000
            ):
                raise RuntimeError(
                    "Arquivo de atualização inválido."
                )

            progress(
                "Validando novo yt-dlp..."
            )

            version = self._validate(
                temp
            )

            if not version:
                raise RuntimeError(
                    "O novo yt-dlp não respondeu à validação."
                )

            progress(
                "Aplicando atualização validada..."
            )

            backup.unlink(
                missing_ok=True
            )

            if target.exists():
                os.replace(
                    target,
                    backup,
                )

            os.replace(
                temp,
                target,
            )

            installed_version = (
                self._validate(
                    target
                )
            )

            if not installed_version:
                raise RuntimeError(
                    "Falha ao validar o yt-dlp "
                    "após a substituição."
                )

            backup.unlink(
                missing_ok=True
            )

            return UpdateResult(
                True,
                "yt-dlp atualizado e validado: "
                + installed_version,
            )

        except Exception as exc:
            temp.unlink(
                missing_ok=True
            )

            current_is_valid = (
                bool(
                    self._validate(
                        target
                    )
                )
                if target.exists()
                else False
            )

            if (
                not current_is_valid
                and backup.exists()
            ):
                try:
                    target.unlink(
                        missing_ok=True
                    )
                    os.replace(
                        backup,
                        target,
                    )
                except Exception:
                    pass

            restored = (
                target.exists()
                and bool(
                    self._validate(
                        target
                    )
                )
            )

            if restored:
                suffix = (
                    "O executável anterior foi "
                    "restaurado e preservado."
                )
            elif backup.exists():
                suffix = (
                    "O backup anterior foi preservado "
                    f"em {backup.name} para recuperação."
                )
            else:
                suffix = (
                    "Não foi possível confirmar a "
                    "restauração automática do executável anterior."
                )

            detail = _safe_proxy_error(
                exc,
                config,
            )

            return UpdateResult(
                False,
                "Atualização não aplicada. "
                + suffix
                + " "
                + detail,
            )

        finally:
            temp.unlink(
                missing_ok=True
            )

    patched_update._central_proxy_patch = True
    YtDlpUpdater.update = patched_update


def _install_globoplay_login_patch() -> None:
    page_class = (
        extractor_page_module.ExtractorPage
    )

    original = (
        page_class.open_globoplay_login
    )

    if getattr(
        original,
        "_central_proxy_patch",
        False,
    ):
        return

    def patched_open_globoplay_login(
        self,
    ):
        config = None

        old_proxy = os.environ.get(
            "MONITOR_GLOBOPLAY_PROXY"
        )

        had_old_proxy = (
            "MONITOR_GLOBOPLAY_PROXY"
            in os.environ
        )

        try:
            config, proxy_url = (
                _proxy_url_for(
                    self.app_root
                )
            )

            if config.enabled:
                os.environ[
                    "MONITOR_GLOBOPLAY_PROXY"
                ] = proxy_url

                if hasattr(
                    self,
                    "settings_status",
                ):
                    self.settings_status.setText(
                        "Abrindo Globoplay pelo "
                        "Proxy Geral do Central..."
                    )
            else:
                os.environ.pop(
                    "MONITOR_GLOBOPLAY_PROXY",
                    None,
                )

                if hasattr(
                    self,
                    "settings_status",
                ):
                    self.settings_status.setText(
                        "Abrindo Globoplay em "
                        "conexão direta..."
                    )

            # O helper já suporta MONITOR_GLOBOPLAY_PROXY.
            # subprocess.Popen herda esta variável no momento da abertura.
            return original(
                self
            )

        except Exception as exc:
            if hasattr(
                self,
                "settings_status",
            ):
                self.settings_status.setText(
                    "Proxy Geral do Central: "
                    + _safe_proxy_error(
                        exc,
                        config,
                    )
                )
            return None

        finally:
            # Não deixa credenciais do proxy persistidas no ambiente
            # global do processo principal.
            if had_old_proxy:
                os.environ[
                    "MONITOR_GLOBOPLAY_PROXY"
                ] = old_proxy or ""
            else:
                os.environ.pop(
                    "MONITOR_GLOBOPLAY_PROXY",
                    None,
                )

    patched_open_globoplay_login._central_proxy_patch = True
    page_class.open_globoplay_login = (
        patched_open_globoplay_login
    )


def _install_status_patch() -> None:
    page_class = (
        extractor_page_module.ExtractorPage
    )

    original = (
        page_class._refresh_binary_status
    )

    if getattr(
        original,
        "_central_proxy_patch",
        False,
    ):
        return

    def patched_refresh(
        self,
    ):
        original(
            self
        )

        label = getattr(
            self,
            "binary_status",
            None,
        )

        if label is None:
            return

        try:
            config, _ = _proxy_url_for(
                self.app_root
            )

            if config.enabled:
                network = (
                    "Proxy Geral=ATIVO"
                    if config.ready
                    else "Proxy Geral=INCOMPLETO"
                )
            else:
                network = (
                    "Proxy Geral=DESATIVADO"
                )

        except Exception:
            network = (
                "Proxy Geral=ERRO"
            )

        current = label.text()

        if "Proxy Geral=" not in current:
            label.setText(
                current
                + " • "
                + network
            )

    patched_refresh._central_proxy_patch = True
    page_class._refresh_binary_status = (
        patched_refresh
    )


def install_extractor_proxy_patch() -> None:
    """Conecta o Extrator de Vídeos ao Proxy Geral do Central."""

    global _INSTALLED

    if _INSTALLED:
        return

    _install_engine_download_patch()
    _install_updater_patch()
    _install_globoplay_login_patch()
    _install_status_patch()

    _INSTALLED = True
