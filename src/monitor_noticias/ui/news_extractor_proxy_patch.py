from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import ProxySettings
from monitor_noticias.ui.news_extractor_page import NewsExtractorPage


_PATCHED = False


@contextmanager
def _temporary_environment(values: dict[str, str]):
    """Aplica variáveis somente durante a criação do QProcess.

    NewsExtractorPage.extract() chama QProcessEnvironment.systemEnvironment()
    de forma síncrona. Portanto basta expor as variáveis durante essa chamada;
    depois restauramos o ambiente do Central imediatamente.
    """

    previous: dict[str, str | None] = {}

    try:
        for key, value in values.items():
            previous[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _proxy_environment(app_root: Path) -> dict[str, str]:
    data_dir = Path(app_root) / "data"

    prefs = SharedPreferences(
        data_dir
        / "prefs"
        / "monitor_prefs.properties"
    )

    settings = ProxySettings(
        prefs,
        data_dir=data_dir,
    )

    config = settings.load()

    return {
        "CENTRAL_PROXY_ENABLED":
            "1" if config.enabled else "0",
        "CENTRAL_PROXY_HOST":
            config.host or "",
        "CENTRAL_PROXY_PORT":
            str(config.port or 0),
        "CENTRAL_PROXY_USERNAME":
            config.username or "",
        "CENTRAL_PROXY_PASSWORD":
            config.password or "",
    }


def install_news_extractor_proxy_patch() -> None:
    """Liga o Extrator de Matérias ao Proxy Geral do Central.

    O Extrator integrado é um Electron separado iniciado via QProcess.
    Antes desta correção, esse processo não recebia o Proxy Geral e o
    monitor-main.js ainda forçava ATIVADO=false.

    A senha continua protegida pelo DPAPI do Central. Ela é lida somente
    no momento da extração e passada ao processo-filho por variável de
    ambiente; não é gravada no config.json/config-proxy.json.
    """

    global _PATCHED

    if _PATCHED:
        return

    original_extract = NewsExtractorPage.extract

    def patched_extract(self: NewsExtractorPage) -> None:
        try:
            env = _proxy_environment(
                Path(self.app_root)
            )
        except Exception as exc:
            self.status.setText(
                "Não foi possível ler o Proxy Geral do Central: "
                f"{exc}"
            )
            return

        enabled = (
            env.get(
                "CENTRAL_PROXY_ENABLED"
            )
            == "1"
        )

        if enabled:
            if not (
                env.get("CENTRAL_PROXY_HOST")
                and env.get("CENTRAL_PROXY_PORT")
                and env.get("CENTRAL_PROXY_USERNAME")
                and env.get("CENTRAL_PROXY_PASSWORD")
            ):
                self.status.setText(
                    "O Proxy Geral está ativado, mas a configuração "
                    "está incompleta. Corrija em Configurações."
                )
                return

            self.status.setText(
                "Preparando extração pelo Proxy Geral do Central..."
            )

        with _temporary_environment(env):
            original_extract(self)

    NewsExtractorPage.extract = patched_extract
    _PATCHED = True
