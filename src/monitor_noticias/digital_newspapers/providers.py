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
    entry_urls: tuple[str, ...] = ()
    dated_edition_url_template: str = ""
    edition_link_keywords: tuple[str, ...] = ()
    min_edition_pages: int = 10
    min_edition_bytes: int = 300_000
    pressreader_page_url_template: str = ""
    pressreader_max_pages: int = 180
    pressreader_min_width: int = 1800
    pressreader_target_width: int = 2200

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

    def _date_values(self, target_date: date) -> dict[str, object]:
        return {
            "year": f"{target_date.year:04d}",
            "month": f"{target_date.month:02d}",
            "day": f"{target_date.day:02d}",
            "iso": target_date.isoformat(),
            "br": target_date.strftime("%d-%m-%Y"),
            "yyyymmdd": target_date.strftime("%Y%m%d"),
        }

    def direct_pdf_url(self, target_date: date) -> str:
        template = self.direct_pdf_template.strip()
        if not template:
            return ""
        return template.format(**self._date_values(target_date))

    def edition_urls(self, target_date: date) -> tuple[str, ...]:
        """Pontos de entrada oficiais, priorizados para o fluxo automático."""
        candidates: list[str] = []

        dated = self.dated_edition_url_template.strip()
        if dated:
            candidates.append(
                dated.format(**self._date_values(target_date))
            )

        candidates.append(self.edition_url)
        candidates.extend(self.entry_urls)

        seen: set[str] = set()
        out: list[str] = []
        for raw in candidates:
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
        return tuple(out)

    def pressreader_page_url(
        self,
        target_date: date,
        page: int,
    ) -> str:
        template = self.pressreader_page_url_template.strip()
        if not template:
            return ""
        values = self._date_values(target_date)
        values["page"] = int(page)
        return template.format(**values)

    def page_pdf_urls(
        self,
        target_date: date,
        page: int,
    ) -> tuple[str, ...]:
        values = self._date_values(target_date)
        values["page"] = int(page)

        out: list[str] = []
        for template in self.page_pdf_templates:
            text = str(template or "").strip()
            if not text:
                continue
            out.append(text.format(**values))
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
            edition_link_keywords=(
                "correio braziliense",
                "edicao certificada",
                "edição certificada",
                "jornal",
                "edicao",
                "edição",
            ),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V81 volta ao fluxo direto que funcionou na V78: usa o all.pdf "
                "oficial da data selecionada, sem tentativa página a página."
            ),
        )


class EstadoMinasProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="estado-de-minas",
            name="Estado de Minas",
            edition_url="https://digital.em.com.br/estadodeminas",
            dated_edition_url_template=(
                "https://digital.em.com.br/estadodeminas/{day}/{month}/{year}/p1"
            ),
            entry_urls=("https://digital.em.com.br/",),
            domains=("em.com.br", "digital.em.com.br"),
            edition_kind="Edição diária em PDF",
            download_strategy="official_pdf",
            official_pdf_documented=True,
            edition_link_keywords=("estado de minas", "em digital", "edicao", "edição", "jornal", "pdf"),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V80 abre diretamente o leitor Estado de Minas e procura o PDF/"
                "download oferecido ao assinante, inclusive em viewer/iframe."
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
            edition_link_keywords=("gazeta revista", "gazeta do povo", "edicao", "edição", "revista", "pdf"),
            min_edition_pages=20,
            min_edition_bytes=500_000,
            note=(
                "A Gazeta Revista é semanal e oferece PDF a assinantes. A V80 segue "
                "automaticamente o link da edição/PDF dentro do site oficial."
            ),
        )


class FolhaProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="folha",
            name="Folha de S.Paulo",
            edition_url="https://acervo.folha.uol.com.br/digital/index.do",
            entry_urls=(
                "https://edicaodigital.folha.uol.com.br/",
            ),
            domains=(
                "folha.uol.com.br",
                "www1.folha.uol.com.br",
                "edicaodigital.folha.uol.com.br",
                "acervo.folha.uol.com.br",
                "paywall.folha.uol.com.br",
                "folha.com.br",
            ),
            edition_kind="Edição Folha / réplica impressa",
            download_strategy="authorized_export",
            edition_link_keywords=("folha", "edicao folha", "edição folha", "jornal", "replica", "réplica", "pdf"),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V80 entra pela Edição Folha/Acervo Digital e procura somente "
                "exportação ou PDF disponibilizado ao assinante pelo leitor oficial."
            ),
        )


class EstadaoProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="estadao",
            name="Estadão",
            edition_url="https://digital.estadao.com.br/o-estado-de-s-paulo/",
            dated_edition_url_template=(
                "https://digital.estadao.com.br/o-estado-de-s-paulo/{yyyymmdd}"
            ),
            entry_urls=("https://www.estadao.com.br/",),
            domains=("estadao.com.br",),
            edition_kind="Estadão Digital / réplica",
            download_strategy="authorized_export",
            date_selection="direct_url",
            edition_link_keywords=("estadao", "estadão", "o estado de s. paulo", "o-estado-de-s-paulo", "edicao", "edição", "jornal", "replica", "réplica"),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V80 abre diretamente a réplica do Estadão na data selecionada e "
                "procura PDF/exportação oferecidos pelo leitor oficial."
            ),
        )


class GloboProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="o-globo",
            name="O Globo",
            edition_url="https://infoglobo.pressreader.com/o-globo",
            entry_urls=(
                "https://jornaldigital.oglobo.globo.com/",
                "https://oglobo.globo.com/",
            ),
            domains=(
                "pressreader.com",
                "newspaperdirect.com",
                "prcdn.co",
                "globo.com",
            ),
            edition_kind="Edição completa via PressReader / páginas HD",
            download_strategy="pressreader_hd_images",
            date_selection="direct_url",
            pressreader_page_url_template=(
                "https://infoglobo.pressreader.com/o-globo/"
                "{yyyymmdd}/page/{page}"
            ),
            pressreader_max_pages=180,
            pressreader_min_width=1800,
            pressreader_target_width=2200,
            edition_link_keywords=(
                "o globo", "oglobo", "pressreader", "jornal digital",
                "edicao", "edição", "jornal",
            ),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V86 usa o mesmo motor PressReader HD do Valor. O viewer oficial "
                "confirmado em infoglobo.pressreader.com é percorrido página a página; "
                "as imagens HD são salvas separadamente e depois reunidas em PDF."
            ),
        )


class ValorProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="valor-economico",
            name="Valor Econômico",
            edition_url="https://valoreconomico.pressreader.com/valor-economico",
            entry_urls=(
                "https://jornaldigital.valor.globo.com/",
                "https://valor.globo.com/",
            ),
            domains=(
                "pressreader.com",
                "newspaperdirect.com",
                "prcdn.co",
                "globo.com",
            ),
            edition_kind="Edição completa via PressReader / páginas HD",
            download_strategy="pressreader_hd_images",
            date_selection="direct_url",
            pressreader_page_url_template=(
                "https://valoreconomico.pressreader.com/valor-economico/"
                "{yyyymmdd}/page/{page}"
            ),
            pressreader_max_pages=180,
            pressreader_min_width=1800,
            pressreader_target_width=2200,
            edition_link_keywords=(
                "valor economico",
                "valor econômico",
                "pressreader",
                "edicao",
                "edição",
                "jornal",
            ),
            min_edition_pages=8,
            min_edition_bytes=300_000,
            note=(
                "A V85 usa a estratégia comprovada no APK Extrator Valor e reforça a "
                "captura dos recursos do PressReader: identifica as imagens de página "
                "do CDN prcdn.co, salva cada página HD separadamente e, quando a sequência "
                "está completa, também monta um único PDF sem reduzir pixels."
            ),
        )


class ATardeProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="a-tarde",
            name="A Tarde",
            edition_url="https://flip.atarde.com.br/edicaodehoje/",
            entry_urls=("https://atarde.com.br/",),
            domains=("atarde.com.br",),
            edition_kind="Edição digital",
            download_strategy="authorized_export",
            edition_link_keywords=("a tarde", "atarde", "edicao", "edição", "jornal", "flip", "pdf"),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V80 tenta primeiro o leitor Flip A TARDE e depois o portal oficial, "
                "procurando apenas edição/PDF/exportação permitidos."
            ),
        )


class GZHProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="gzh-zero-hora",
            name="Gaúcha / Zero Hora / GZH",
            edition_url=(
                "https://flipzh.clicrbs.com.br/jornal-digital/pub/gruporbs/"
            ),
            dated_edition_url_template=(
                "https://flipzh.clicrbs.com.br/jornal-digital/pub/gruporbs/"
                "?numero={yyyymmdd}"
            ),
            entry_urls=(
                "https://gauchazh.clicrbs.com.br/",
                "https://www.gauchazh.com.br/",
            ),
            domains=(
                "clicrbs.com.br",
                "gzh.rs",
                "gauchazh.com.br",
            ),
            edition_kind="Réplica completa de Zero Hora",
            download_strategy="authorized_export",
            edition_link_keywords=("zero hora", "zh", "gzh", "jornal digital", "edicao", "edição", "replica", "réplica"),
            min_edition_pages=10,
            min_edition_bytes=300_000,
            note=(
                "A V80 entra diretamente no leitor de Zero Hora e passa a preservar "
                "também a sessão do domínio gauchazh.com.br."
            ),
        )


class NYTimesProvider(DigitalNewspaperProvider):
    def __init__(self) -> None:
        super().__init__(
            id="new-york-times",
            name="The New York Times",
            edition_url=(
                "https://eeditionnytimes.newspaperdirect.com/epaper/viewer.aspx"
            ),
            entry_urls=(
                "https://nytimes.pressreader.com/the-new-york-times",
            ),
            domains=(
                "newspaperdirect.com",
                "pressreader.com",
                "nytimes.com",
            ),
            edition_kind="Replica Edition / PressReader",
            download_strategy="authorized_export",
            edition_link_keywords=("new york times", "replica edition", "pressreader", "epaper", "edition", "newspaper"),
            min_edition_pages=20,
            min_edition_bytes=500_000,
            note=(
                "A V80 usa o viewer oficial da Replica Edition e o PressReader como "
                "fallback, limitando-se aos recursos de impressão/download disponíveis."
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
                "A Print Edition continua documentada no aplicativo oficial. A V80 não "
                "extrai pacotes offline do app nem anuncia PDF desktop inexistente."
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
