from __future__ import annotations

from collections.abc import Callable
import importlib

from monitor_noticias.matching.common import normalize

# Estes termos descrevem um cargo/instituição, não uma lista de palavras soltas.
# A busca por Ministro da Defesa também aceita a forma feminina do mesmo cargo,
# mas não aceita ministros de outras pastas apenas porque "defesa" aparece
# noutro trecho do título/resumo.
_STRICT_PHRASES: dict[str, tuple[str, ...]] = {
    "ministro da defesa": ("ministro da defesa", "ministra da defesa"),
    "ministra da defesa": ("ministro da defesa", "ministra da defesa"),
    "ministerio da defesa": ("ministerio da defesa",),
}

_PatchedMatcher = Callable[[str, str], bool]
_FALLBACK = Callable[[str, str], bool]
_PATCHED = False


def strict_phrase_decision(text: str, phrase: str) -> bool | None:
    """Retorna True/False para os termos de cargo estritos, ou None nos demais.

    O uso de ``normalize`` mantém compatibilidade com maiúsculas, acentos e
    pontuação sem relaxar a correspondência para tokens separados.
    """
    wanted = normalize(str(phrase or ""))
    forms = _STRICT_PHRASES.get(wanted)
    if forms is None:
        return None

    haystack = f" {normalize(str(text or ""))} "
    return any(f" {form} " in haystack for form in forms)


def strict_phrase_matches(text: str, phrase: str, fallback: _FALLBACK) -> bool:
    """Impõe termos de cargo exatos e delega os demais à regra atual."""
    decision = strict_phrase_decision(text, phrase)
    if decision is not None:
        return decision
    return bool(fallback(text, phrase))


def _guard(original: _FALLBACK) -> _PatchedMatcher:
    def guarded(text: str, phrase: str) -> bool:
        return strict_phrase_matches(text, phrase, original)

    guarded.__name__ = "strict_video_phrase_matches"
    guarded.__doc__ = "Correspondência de vídeo com cargos nacionais estritos."
    return guarded


def install_video_defense_term_patch() -> None:
    """Aplica o filtro nos módulos já usados pelo fluxo ativo de busca.

    O VideoRepository importa ``phrase_matches`` diretamente em
    ``repositories.video_search``. Por isso, além de proteger o módulo original,
    precisamos atualizar esse alias de execução. A instalação é idempotente.
    """
    global _PATCHED
    if _PATCHED:
        return

    matching_package = importlib.import_module("monitor_noticias.matching")
    rules_module = importlib.import_module("monitor_noticias.matching.video_rules")
    policy_module = importlib.import_module("monitor_noticias.matching.video_match_policy")
    search_module = importlib.import_module("monitor_noticias.repositories.video_search")

    guarded_rules = _guard(rules_module.phrase_matches)
    guarded_policy = _guard(policy_module.phrase_matches)

    rules_module.phrase_matches = guarded_rules
    policy_module.phrase_matches = guarded_policy
    search_module.phrase_matches = guarded_rules

    # Mantém consistentes os exports públicos do pacote matching.
    matching_package.phrase_matches = guarded_policy
    matching_package.repository_video_phrase_matches = guarded_rules

    _PATCHED = True
