from __future__ import annotations

from dataclasses import replace

from monitor_noticias.matching.common import compact, normalize
from monitor_noticias.models import MediaSource, News

STOP_WORDS = {
    "de", "do", "da", "dos", "das", "e", "em", "no", "na", "nos", "nas",
    "a", "o", "as", "os",
}


def story_key(news: News) -> str:
    source_key = normalize(news.source).replace(" noticias", "").replace(" jornal", "").strip()
    title_key = normalize(news.title)
    return f"{source_key}|{title_key}"


def merge_news(previous: News, incoming: News) -> News:
    terms: list[str] = []
    for raw in previous.matchedTerm.split(",") + incoming.matchedTerm.split(","):
        value = raw.strip()
        if value and value not in terms:
            terms.append(value)
    return replace(
        incoming,
        important=previous.important or incoming.important,
        demand=previous.demand or incoming.demand,
        matchedTerm=", ".join(terms),
        matchedDemand=incoming.matchedDemand if incoming.matchedDemand.strip() else previous.matchedDemand,
        capturedAt=previous.capturedAt if previous.capturedAt > 0 else incoming.capturedAt,
    )


def publisher_host_key(value: str) -> str:
    cleaned = value.strip().lower()
    base = cleaned.split(".", 1)[0] if "." in cleaned else cleaned
    return compact(base)


def demand_vehicle_matches(actual_source: str, vehicle: str) -> bool:
    if not vehicle.strip():
        return True
    actual = normalize(actual_source)
    actual_key = compact(actual_source)
    host_key = publisher_host_key(actual_source)
    wanted = normalize(vehicle)
    wanted_key = compact(vehicle)
    if actual == wanted or actual_key == wanted_key or host_key == wanted_key:
        return True
    tokens = [
        token for token in wanted.split(" ")
        if len(token) >= 2 and token not in STOP_WORDS
    ]
    return (
        len(tokens) >= 2
        and len(wanted_key) >= 5
        and (actual_key.startswith(wanted_key) or host_key.startswith(wanted_key))
    )


def subject_matches(text: str, subject: str) -> bool:
    haystack = normalize(text)
    wanted = normalize(subject)
    if not wanted:
        return True
    if f" {wanted} " in f" {haystack} ":
        return True
    hay_tokens = {token for token in haystack.split(" ") if token}
    wanted_tokens = [token for token in wanted.split(" ") if token]
    if len(wanted_tokens) == 1:
        return wanted_tokens[0] in hay_tokens
    tokens = [
        token for token in wanted_tokens
        if len(token) >= 3 and token not in STOP_WORDS
    ]
    return bool(tokens) and all(token in hay_tokens for token in tokens)


def source_matches_strict(actual_source: str, selected: MediaSource) -> bool:
    actual_normalized = normalize(actual_source)
    actual_key = compact(actual_source)
    host_key = publisher_host_key(actual_source)
    for candidate in [selected.name, *selected.aliases]:
        candidate_normalized = normalize(candidate)
        candidate_key = compact(candidate)
        if not candidate_normalized or not candidate_key:
            continue
        if (
            actual_normalized == candidate_normalized
            or actual_key == candidate_key
            or host_key == candidate_key
        ):
            return True
        meaningful_tokens = [
            token for token in candidate_normalized.split(" ")
            if len(token) >= 2 and token not in STOP_WORDS
        ]
        if (
            len(meaningful_tokens) >= 2
            and len(candidate_key) >= 6
            and (actual_key.startswith(candidate_key) or host_key.startswith(candidate_key))
        ):
            return True
    return False


def reuse_historical_identity(incoming: News, history: list[News]) -> News:
    by_link = {item.link: item for item in history}
    by_story = {story_key(item): item for item in history}
    previous = by_link.get(incoming.link) or by_story.get(story_key(incoming))
    if previous is None:
        return incoming
    return merge_news(
        previous,
        replace(incoming, link=previous.link, capturedAt=previous.capturedAt),
    )
