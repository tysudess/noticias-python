from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from collections.abc import Mapping


# Nomes canônicos usados por newspapers.json / GMAIL_PAPERS.
_CANONICAL = {
    "O GLOBO": "O GLOBO",
    "FOLHA DE SÃO PAULO": "FOLHA DE SÃO PAULO",
    "ESTADÃO": "ESTADÃO",
    "CORREIO BRAZILIENSE": "CORREIO BRAZILIENSE",
    "ESTADO DE MINAS": "ESTADO DE MINAS",
    "THE NEW YORK TIMES": "THE NEW YORK TIMES",
}


def _key(value: object) -> str:
    """Chave estável: ignora caixa, acentos, pontuação e espaços."""
    raw = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = raw.encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"[^A-Z0-9]", "", ascii_text)


_ALIASES = {
    # O Globo
    "OGLOBO": "O GLOBO",
    "GLOBO": "O GLOBO",
    "INFOGLOBO": "O GLOBO",
    # Folha
    "FOLHADESAOPAULO": "FOLHA DE SÃO PAULO",
    "FOLHADESPAULO": "FOLHA DE SÃO PAULO",
    "FOLHASAOPAULO": "FOLHA DE SÃO PAULO",
    "FOLHASP": "FOLHA DE SÃO PAULO",
    "FOLHADESP": "FOLHA DE SÃO PAULO",
    # Estadão / O Estado de S. Paulo
    "ESTADAO": "ESTADÃO",
    "OESTADODESAOPAULO": "ESTADÃO",
    "ESTADODESAOPAULO": "ESTADÃO",
    "OESTADODESPAULO": "ESTADÃO",
    "ESTADODESPAULO": "ESTADÃO",
    # Correio Braziliense
    "CORREIOBRAZILIENSE": "CORREIO BRAZILIENSE",
    "CORREIODEBRASILIA": "CORREIO BRAZILIENSE",
    "CORREIOBRASILIA": "CORREIO BRAZILIENSE",
    # Estado de Minas
    "ESTADODEMINAS": "ESTADO DE MINAS",
    # The New York Times
    "THENEWYORKTIMES": "THE NEW YORK TIMES",
    "NEWYORKTIMES": "THE NEW YORK TIMES",
    "NYTIMES": "THE NEW YORK TIMES",
    "NYT": "THE NEW YORK TIMES",
}

for _name in _CANONICAL.values():
    _ALIASES[_key(_name)] = _name


def canonical_paper_name(value: object) -> str | None:
    """Converte uma variação conhecida do nome para a chave canônica.

    Nomes desconhecidos retornam None, em vez de uma associação aproximada
    que poderia atribuir a capa ao jornal errado.
    """
    return _ALIASES.get(_key(value))


def normalize_matters_payload(matters: object):
    """Normaliza o agrupamento do Apps Script sem descartar links.

    Retorna (jornais_canônicos, nomes_desconhecidos, aliases_normalizados).
    URLs repetidas são removidas somente dentro do mesmo jornal.
    """
    normalized: OrderedDict[str, list[str]] = OrderedDict()
    unknown: OrderedDict[str, list[str]] = OrderedDict()
    aliases: list[str] = []

    if not isinstance(matters, Mapping):
        return {}, {}, []

    for raw_name, raw_urls in matters.items():
        label = str(raw_name or "").strip()
        urls_iter = raw_urls if isinstance(raw_urls, (list, tuple, set)) else [raw_urls]
        urls = [str(url or "").strip() for url in urls_iter if str(url or "").strip()]
        if not label or not urls:
            continue

        canonical = canonical_paper_name(label)
        if canonical is None:
            bucket = unknown.setdefault(label, [])
        else:
            bucket = normalized.setdefault(canonical, [])
            if _key(label) != _key(canonical) or label != canonical:
                aliases.append(label)

        for url in urls:
            if url not in bucket:
                bucket.append(url)

    return dict(normalized), dict(unknown), aliases
