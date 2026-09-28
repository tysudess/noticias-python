from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


@dataclass(frozen=True, slots=True)
class DigitalNewspaperProvider:
    id: str
    name: str
    edition_url: str
    domains: tuple[str, ...]
    edition_kind: str
    download_strategy: str
    replica_available: bool = True
    official_pdf_documented: bool = False
    browser_supported: bool = True
    date_selection: str = "viewer"
    note: str = ""

    @property
    def can_try_download(self) -> bool:
        return bool(
            self.browser_supported
            and self.download_strategy != "app_only"
        )

    def output_filename(self, target_date: date) -> str:
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            self.id.lower(),
        ).strip("-")
        return f"{slug}-{target_date.isoformat()}.pdf"

    def domain_allowed(self, domain: str) -> bool:
        host = str(domain or "").strip().lower().lstrip(".")
        if not host:
            return False
        return any(
            host == allowed
            or host.endswith("." + allowed)
            for allowed in self.domains
        )


class CorreioBrazilienseProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="correio-braziliense",
            name="Correio Braziliense",
            edition_url="https://www.correiobraziliense.com.br/",
            domains=("correiobraziliense.com.br",),
            edition_kind="Edição diária / íntegra do impresso",
            download_strategy="official_pdf",
            official_pdf_documented=True,
            note=(
                "A assinatura digital anuncia a íntegra do jornal impresso em PDF. "
                "A V77 procura o download autorizado dentro da sessão do assinante."
            ),
        )


class EstadoMinasProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="estado-de-minas",
            name="Estado de Minas",
            edition_url="https://digital.em.com.br/",
            domains=("em.com.br", "digital.em.com.br"),
            edition_kind="Edição diária em PDF",
            download_strategy="official_pdf",
            official_pdf_documented=True,
            note=(
                "O FAQ do Estado de Minas orienta a leitura do jornal em PDF em "
                "digital.em.com.br, mediante login de assinante."
            ),
        )


class GazetaPovoProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="gazeta-revista",
            name="Gazeta do Povo / Gazeta Revista",
            edition_url="https://www.gazetadopovo.com.br/gazeta-revista/",
            domains=(
                "gazetadopovo.com.br",
                "wwws.gazetadopovo.com.br",
            ),
            edition_kind="Revista semanal em PDF",
            download_strategy="official_pdf",
            official_pdf_documented=True,
            date_selection="weekly",
            note=(
                "A Gazeta Revista é disponibilizada aos assinantes para download em PDF. "
                "Não representa uma réplica diária do antigo jornal impresso."
            ),
        )


class FolhaProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="folha",
            name="Folha de S.Paulo",
            edition_url="https://edicaodigital.folha.uol.com.br/",
            domains=(
                "folha.uol.com.br",
                "www1.folha.uol.com.br",
                "edicaodigital.folha.uol.com.br",
            ),
            edition_kind="Edição Folha / réplica impressa",
            download_strategy="authorized_export",
            note=(
                "A réplica impressa é confirmada. PDF integral não é presumido: "
                "a V77 usa somente download/exportação oferecida pelo visualizador."
            ),
        )


class EstadaoProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="estadao",
            name="Estadão",
            edition_url="https://www.estadao.com.br/",
            domains=("estadao.com.br", "www.estadao.com.br"),
            edition_kind="Estadão Digital / réplica",
            download_strategy="authorized_export",
            note=(
                "A integração abre a sessão oficial do assinante e só usa recursos de "
                "download ou impressão disponibilizados pelo próprio serviço."
            ),
        )


class GloboProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="o-globo",
            name="O Globo",
            edition_url="https://oglobo.globo.com/",
            domains=("oglobo.globo.com", "globo.com"),
            edition_kind="Jornal digitalizado",
            download_strategy="authorized_export",
            note=(
                "A assinatura inclui edição digitalizada. A V77 não assume que exista "
                "PDF integral; procura apenas exportação autorizada na sessão."
            ),
        )


class ValorProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="valor-economico",
            name="Valor Econômico",
            edition_url="https://valor.globo.com/",
            domains=("valor.globo.com", "globo.com"),
            edition_kind="Jornal impresso digitalizado",
            download_strategy="authorized_export",
            note=(
                "O plano digital inclui a edição do impresso digitalizada. O PDF integral "
                "só será usado se o visualizador oferecer essa opção ao assinante."
            ),
        )


class ATardeProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="a-tarde",
            name="A Tarde",
            edition_url="https://atarde.com.br/",
            domains=("atarde.com.br",),
            edition_kind="Edição digital",
            download_strategy="authorized_export",
            note=(
                "A edição digital pode ser lida no computador. A V77 preserva o login "
                "oficial e não tenta extrair recursos protegidos do visualizador."
            ),
        )


class GZHProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="gzh-zero-hora",
            name="Gaúcha / Zero Hora / GZH",
            edition_url="https://gauchazh.clicrbs.com.br/",
            domains=(
                "gauchazh.clicrbs.com.br",
                "gzh.rs",
                "clicrbs.com.br",
            ),
            edition_kind="Réplica completa de Zero Hora",
            download_strategy="authorized_export",
            note=(
                "A réplica completa está disponível a assinantes no site GZH. "
                "O download só é acionado se aparecer como recurso autorizado."
            ),
        )


class NYTimesProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="new-york-times",
            name="The New York Times",
            edition_url="https://nytimes.pressreader.com/the-new-york-times",
            domains=(
                "nytimes.pressreader.com",
                "pressreader.com",
                "newspaperdirect.com",
                "nytimes.com",
            ),
            edition_kind="Replica Edition / PressReader",
            download_strategy="authorized_export",
            note=(
                "A Replica Edition é operada pelo PressReader. A V77 pode manter a "
                "sessão e usar apenas impressão/download oferecidos pela plataforma."
            ),
        )


class WashingtonPostProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="washington-post",
            name="The Washington Post",
            edition_url="https://www.washingtonpost.com/",
            domains=("washingtonpost.com",),
            edition_kind="Print Edition no aplicativo oficial",
            download_strategy="app_only",
            browser_supported=True,
            note=(
                "A documentação atual concentra a Print Edition no aplicativo. "
                "A V77 abre a conta web, mas não tenta extrair o pacote offline do app."
            ),
        )


DIGITAL_NEWSPAPER_PROVIDERS: tuple[DigitalNewspaperProvider, ...] = (
    CorreioBrazilienseProvider(),
    EstadoMinasProvider(),
    GazetaPovoProvider(),
    FolhaProvider(),
    EstadaoProvider(),
    GloboProvider(),
    ValorProvider(),
    ATardeProvider(),
    GZHProvider(),
    NYTimesProvider(),
    WashingtonPostProvider(),
)

_PROVIDER_BY_ID = {
    provider.id: provider
    for provider in DIGITAL_NEWSPAPER_PROVIDERS
}


def get_provider(provider_id: str) -> DigitalNewspaperProvider:
    key = str(provider_id or "").strip()
    try:
        return _PROVIDER_BY_ID[key]
    except KeyError as exc:
        raise KeyError(
            f"Provedor de jornal digital desconhecido: {key}"
        ) from exc
