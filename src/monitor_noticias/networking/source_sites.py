from __future__ import annotations

import ipaddress
import re
import unicodedata
from threading import RLock
from urllib.parse import urlencode, urlsplit


_LOCK = RLock()
_SOURCE_SITE_URLS: dict[str, str] = {}
_GOOGLE_WRAPPER_HOSTS = {
    "google.com",
    "www.google.com",
    "news.google.com",
    "g.co",
    "googleusercontent.com",
}
FAVICON_ENDPOINT = "https://www.google.com/s2/favicons"
FAVICON_SIZE = 64

_FALLBACK_SITES_RAW = {
    "Folha de S.Paulo": "https://www.folha.uol.com.br/",
    "Folha": "https://www.folha.uol.com.br/",
    "Jornal Opção": "https://www.jornalopcao.com.br/",
    "Diário do Amapá": "https://www.diariodoamapa.com.br/",
    "Banda B": "https://www.bandab.com.br/",
    "G1": "https://g1.globo.com/",
    "Correio Braziliense": "https://www.correiobraziliense.com.br/",
    "O Globo": "https://oglobo.globo.com/",
    "UOL": "https://noticias.uol.com.br/",
    "R7": "https://noticias.r7.com/",
    "Metrópoles": "https://www.metropoles.com/",
    "CNN Brasil": "https://www.cnnbrasil.com.br/",
    "Jovem Pan": "https://jovempan.com.br/",
    "Estado de Minas": "https://www.em.com.br/",
    "Estadão": "https://www.estadao.com.br/",
    "Valor Econômico": "https://valor.globo.com/",
    "Revista Oeste": "https://revistaoeste.com/",
    "O Antagonista": "https://oantagonista.com.br/",
    "A Tarde": "https://atarde.com.br/",
    "Correio 24 Horas": "https://www.correio24horas.com.br/",
    "Bahia Notícias": "https://www.bahianoticias.com.br/",
    "ContilNet": "https://contilnetnoticias.com.br/",
    "AC24Horas": "https://ac24horas.com/",
    "DOL": "https://dol.com.br/",
    "Diário do Pará": "https://diariodopara.com.br/",
    "O Liberal": "https://www.oliberal.com/",
    "GazetaWeb": "https://www.gazetaweb.com/",
    "TNH1": "https://www.tnh1.com.br/",
    "O Povo": "https://www.opovo.com.br/",
    "Diário do Nordeste": "https://diariodonordeste.verdesmares.com.br/",
    "Imirante": "https://imirante.com/",
    "Jornal da Paraíba": "https://jornaldaparaiba.com.br/",
    "Folha de Pernambuco": "https://www.folhape.com.br/",
    "Tribuna do Norte": "https://tribunadonorte.com.br/",
    "Infonet": "https://infonet.com.br/",
    "Campo Grande News": "https://www.campograndenews.com.br/",
    "Folha Vitória": "https://www.folhavitoria.com.br/",
    "Itatiaia": "https://www.itatiaia.com.br/",
    "O Dia": "https://odia.ig.com.br/",
    "GZH": "https://gauchazh.clicrbs.com.br/",
    "Correio do Povo": "https://www.correiodopovo.com.br/",
    "Gazeta do Povo": "https://www.gazetadopovo.com.br/",
    "ND Mais": "https://www.ndmais.com.br/",
    "NSC Total": "https://www.nsctotal.com.br/",
    "Bem Paraná": "https://www.bemparana.com.br/",
    "O Popular": "https://opopular.com.br/",
    "MidiaNews": "https://www.midianews.com.br/",
    "Portal 6": "https://portal6.com.br/",
    "SelesNafes.com": "https://selesnafes.com/",
}


def normalize_source_key(value: str) -> str:
    """Normaliza o nome de um veículo para consulta no registro em memória."""
    decomposed = unicodedata.normalize("NFD", str(value or "").casefold())
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", "", without_marks)


_FALLBACK_SITES = {
    normalize_source_key(name): url for name, url in _FALLBACK_SITES_RAW.items()
}


def normalize_site_url(value: str) -> str:
    """Retorna somente a origem HTTP(S) de um site público válido."""
    try:
        parsed = urlsplit(str(value or "").strip())
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").lower().rstrip(".")
        if scheme not in {"http", "https"} or not host:
            return ""
        if parsed.username or parsed.password:
            return ""
        if host in _GOOGLE_WRAPPER_HOSTS or host.endswith(".googleusercontent.com"):
            return ""
        if "." not in host or host == "localhost" or host.endswith(".local"):
            return ""
        try:
            ipaddress.ip_address(host)
            return ""
        except ValueError:
            pass
        return f"{scheme}://{host}/"
    except Exception:
        return ""


def register_source_site(source: str, site_url: str) -> None:
    """Guarda temporariamente a URL oficial que o RSS atribui ao veículo."""
    key = normalize_source_key(source)
    clean_url = normalize_site_url(site_url)
    if not key or not clean_url:
        return
    with _LOCK:
        _SOURCE_SITE_URLS[key] = clean_url


def get_source_site(source: str) -> str:
    key = normalize_source_key(source)
    if not key:
        return ""
    with _LOCK:
        return _SOURCE_SITE_URLS.get(key, "")


def clear_source_sites_for_tests() -> None:
    """Limpa o registro em memória; utilizado somente pelos testes unitários."""
    with _LOCK:
        _SOURCE_SITE_URLS.clear()


def resolve_source_site_url(news) -> str:
    """Resolve o site do veículo, priorizando a origem oficial do RSS."""
    source = str(getattr(news, "source", "") or "")
    for candidate in (
        getattr(news, "sourceUrl", ""),
        get_source_site(source),
    ):
        clean = normalize_site_url(candidate)
        if clean:
            return clean

    # Links diretos revelam o domínio oficial; links intermediários do Google
    # não devem ser exibidos com o favicon do Google Notícias.
    try:
        link = str(getattr(news, "link", "") or "")
        host = (urlsplit(link).hostname or "").lower().rstrip(".")
    except Exception:
        link, host = "", ""
    if host and host not in _GOOGLE_WRAPPER_HOSTS and not host.endswith(".google.com"):
        clean = normalize_site_url(link)
        if clean:
            return clean

    return normalize_site_url(_FALLBACK_SITES.get(normalize_source_key(source), ""))


def build_favicon_request_url(site_url: str) -> str:
    """Constrói uma URL de favicon usando somente a origem do veículo."""
    clean = normalize_site_url(site_url)
    if not clean:
        return ""
    return f"{FAVICON_ENDPOINT}?{urlencode({'domain_url': clean, 'sz': str(FAVICON_SIZE)})}"
