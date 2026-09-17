from __future__ import annotations

from monitor_noticias.matching.common import normalize

SEPTEMBER_7_EVENT_TOKENS = {
    "desfile", "desfiles", "comemoracao", "comemoracoes", "independencia"
}
STOP_WORDS = {
    "de", "do", "da", "dos", "das", "e", "em", "no", "na", "nos", "nas",
    "a", "o", "as", "os",
}


def _inflection_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("r"):
        variants.add(token + "es")
    elif token.endswith("l"):
        variants.add(token[:-1] + "is")
    elif token.endswith("m"):
        variants.add(token[:-1] + "ns")
    elif token.endswith("ao"):
        variants.add(token[:-2] + "oes")
        variants.add(token[:-2] + "aes")
        variants.add(token[:-2] + "aos")
    elif not token.endswith("s"):
        variants.add(token + "s")
    if token.endswith("res") and len(token) > 5:
        variants.add(token[:-2])
    elif token.endswith("is") and len(token) > 5:
        variants.add(token[:-2] + "l")
    elif token.endswith("ns") and len(token) > 5:
        variants.add(token[:-2] + "m")
    elif token.endswith("s") and len(token) > 5:
        variants.add(token[:-1])
    return variants


def _token_equivalent(actual: str, wanted: str) -> bool:
    if actual == wanted:
        return True
    if len(actual) < 5 or len(wanted) < 5:
        return False
    return actual in _inflection_variants(wanted) or wanted in _inflection_variants(actual)


def _matches_september_7_event(haystack: str, wanted: str) -> bool:
    wanted_tokens = {token for token in wanted.split(" ") if token}
    if "7" not in wanted_tokens or "setembro" not in wanted_tokens:
        return False
    if not any(token in SEPTEMBER_7_EVENT_TOKENS for token in wanted_tokens):
        return False
    hay_tokens = {token for token in haystack.split(" ") if token}
    return (
        "7" in hay_tokens and "setembro" in hay_tokens
        and any(token in SEPTEMBER_7_EVENT_TOKENS for token in hay_tokens)
    )


def phrase_matches(text: str, phrase: str) -> bool:
    """Equivalente ao objeto Kotlin VideoMatchPolicy, usado pelo reparo do banco."""
    haystack = normalize(text)
    wanted = normalize(phrase)
    if not wanted:
        return False
    if _matches_september_7_event(haystack, wanted):
        return True
    hay_tokens = {token for token in haystack.split(" ") if token}
    wanted_tokens = [token for token in wanted.split(" ") if token]
    if not wanted_tokens:
        return False
    if len(wanted_tokens) == 1:
        return any(_token_equivalent(token, wanted_tokens[0]) for token in hay_tokens)
    if f" {wanted} " in f" {haystack} ":
        return True
    meaningful = [
        token for token in wanted_tokens
        if len(token) >= 3 and token not in STOP_WORDS
    ]
    return bool(meaningful) and all(
        any(_token_equivalent(actual, wanted_token) for actual in hay_tokens)
        for wanted_token in meaningful
    )
