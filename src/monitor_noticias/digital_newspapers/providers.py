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
    direct_pdf_template: str = ""
    page_pdf_templates: tuple[str, ...] = ()
    pagewise_min_pages: int = 8
    pagewise_max_pages: int = 120
    pagewise_stop_after_misses: int = 4

    @property
    def can_try_download(self) -> bool:
        return bool(
            self.browser_supported
            and self.download_strategy != "app_only"
        )

    @property
    def supports_direct_pdf(self) -> bool:
        return bool(self.direct_pdf_template.strip())

    @property
    def supports_pagewise_pdf(self) -> bool:
        return bool(self.page_pdf_templates)

    def direct_pdf_url(self, target_date: date) -> str:
        template = self.direct_pdf_template.strip()
        if not template:
            return ""

        return template.format(
            year=f"{target_date.year:04d}",
            month=f"{target_date.month:02d}",
            day=f"{target_date.day:02d}",
            iso=target_date.isoformat(),
            br=target_date.strftime("%d-%m-%Y"),
        )

    def page_pdf_urls(
        self,
        target_date: date,
        page: int,
    ) -> tuple[str, ...]:
        out: list[str] = []
        for template in self.page_pdf_templates:
            text = str(template or "").strip()
            if not text:
                continue
            out.append(
                text.format(
                    year=f"{target_date.year:04d}",
                    month=f"{target_date.month:02d}",
                    day=f"{target_date.day:02d}",
                    iso=target_date.isoformat(),
                    br=target_date.strftime("%d-%m-%Y"),
                    page=int(page),
                )
            )
        return tuple(out)

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
            edition_url="https://flip.correiobraziliense.com.br/",
            domains=(
                "correiobraziliense.com.br",
                "flip.correiobraziliense.com.br",
                "edicao.correiobraziliense.com.br",
            ),
            edition_kind="Edição diária / íntegra do impresso",
            download_strategy="official_pdf",
            official_pdf_documented=True,
            date_selection="direct_url",
            direct_pdf_template=(
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/all.pdf"
            ),
            page_pdf_templates=(
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/{page}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/{page:02d}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/{page:03d}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/pag{page}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/pag{page:02d}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/page{page}.pdf",
                "https://edicao.correiobraziliense.com.br/"
                "correiobraziliense/{year}/{month}/{day}/page{page:02d}.pdf",
            ),
            pagewise_min_pages=8,
            pagewise_max_pages=80,
            pagewise_stop_after_misses=5,
            note=(
                "A edição certificada possui PDF integral. A V79 primeiro tenta "
                "reconstituir a edição página a página para evitar falhas como "
                "saltos 2→4; se não houver páginas individuais válidas, cai para o "
                "all.pdf oficial sem recompressão."
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
                "O Estado de Minas oferece a edição diária em PDF para assinantes. "
                "A V78 tenta o fluxo autorizado em segundo plano e só pede renovação "
                "de sessão quando o site exigir autenticação."
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
                "A réplica impressa é confirmada. A V78 tenta silenciosamente apenas "
                "PDF/download/exportação oferecidos pelo visualizador oficial."
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
                "A V78 usa a sessão oficial do assinante em segundo plano e só aciona "
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
                "A assinatura inclui edição digitalizada. A V78 não presume PDF integral; "
                "tenta somente exportação autorizada do serviço."
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
                "só é salvo se o visualizador oferecer essa opção ao assinante."
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
                "A edição digital pode ser lida no computador. A V78 trabalha em segundo "
                "plano e não tenta extrair recursos protegidos do visualizador."
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
                "A réplica completa está disponível a assinantes no site GZH. O download "
                "só é acionado quando o próprio serviço o disponibiliza."
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
                "A Replica Edition é operada pelo PressReader. A V78 usa somente "
                "impressão/download oferecidos pela plataforma ao assinante."
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
                "A V78 abre a conta web, mas não tenta extrair o pacote offline do app."
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
