from __future__ import annotations

from dataclasses import replace
import re
from urllib.parse import urlsplit, urlunsplit

from monitor_noticias.matching.common import compact, normalize
from monitor_noticias.models import Demand, VideoItem, VideoSource

STOP_WORDS = {
    "de", "do", "da", "dos", "das", "e", "em", "no", "na", "nos", "nas",
    "a", "o", "as", "os",
}
SEPTEMBER_7_EVENT_TOKENS = {
    "desfile", "desfiles", "comemoracao", "comemoracoes", "independencia"
}
GENERIC_TITLES = {
    "videos", "video", "todos os videos", "todos videos", "ultimos videos",
    "mais videos", "ver videos", "ver todos os videos", "ao vivo",
    "assistir ao vivo", "carregar mais", "ver mais", "ver tudo",
}
GENERIC_SLUGS = {"videos", "video", "ao vivo", "todos os videos", "ultimos videos"}
GENERIC_PATHS = {
    "/videos", "/video", "/ao-vivo", "/busca", "/search", "/categorias/jornalismo",
}
_GLOBOPLAY_DIRECT_PATH_RE = re.compile(r"/v/[0-9]+/?$", re.IGNORECASE)


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
        "7" in hay_tokens
        and "setembro" in hay_tokens
        and any(token in SEPTEMBER_7_EVENT_TOKENS for token in hay_tokens)
    )


def phrase_matches(text: str, phrase: str) -> bool:
    """Equivalente à função privada VideoRepository.phraseMatches."""
    haystack = normalize(text)
    wanted = normalize(phrase)
    if not wanted:
        return True
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


def source_matches_demand(source: VideoSource, vehicle: str) -> bool:
    if not vehicle.strip():
        return True
    wanted = normalize(vehicle)
    wanted_compact = compact(vehicle)
    candidates = [source.name, source.group, *source.aliases]
    for candidate in candidates:
        actual = normalize(candidate)
        actual_compact = compact(candidate)
        if actual == wanted or actual_compact == wanted_compact:
            return True
        if len(wanted_compact) >= 4 and wanted_compact in actual_compact:
            return True
        if len(actual_compact) >= 4 and actual_compact in wanted_compact:
            return True
    return False


def merge_video(previous: VideoItem, incoming: VideoItem) -> VideoItem:
    terms: list[str] = []
    for raw in previous.matchedTerm.split(",") + incoming.matchedTerm.split(","):
        value = raw.strip()
        if value and value not in terms:
            terms.append(value)
    return replace(
        incoming,
        matchedTerm=", ".join(terms),
        matchedDemand=incoming.matchedDemand if incoming.matchedDemand.strip() else previous.matchedDemand,
        capturedAt=max(previous.capturedAt, incoming.capturedAt),
    )


def canonicalize_url(value: str) -> str:
    if not value.strip():
        return ""
    trimmed = value.strip()
    try:
        uri = urlsplit(trimmed)
        host = (uri.hostname or "").lower()
        query = uri.query or ""
        path = uri.path or ""
        if host == "youtu.be" or host.endswith("youtube.com"):
            video_id = ""
            if host == "youtu.be":
                video_id = path.strip("/").split("/", 1)[0]
            elif path.lower() == "/watch":
                for piece in query.split("&"):
                    if piece.startswith("v="):
                        video_id = piece.split("=", 1)[1]
                        break
            else:
                parts = [part for part in path.strip("/").split("/") if part]
                if len(parts) >= 2 and parts[0].lower() in {"shorts", "live"}:
                    video_id = parts[1]
            return (
                f"https://www.youtube.com/watch?v={video_id}"
                if video_id
                else trimmed
            )
        if uri.hostname is None:
            return trimmed
        final_path = path or "/"
        scheme = uri.scheme or "https"
        return urlunsplit((scheme, uri.netloc, final_path, "", "")).rstrip("/")
    except (ValueError, UnicodeError):
        return trimmed


def canonical_key(value: str) -> str:
    return canonicalize_url(value).lower().rstrip("/")


def same_page(first: str, second: str) -> bool:
    return canonical_key(first) == canonical_key(second)


def in_period(item: VideoItem, from_: int | None, to: int | None) -> bool:
    if from_ is not None and item.publishedAt < from_:
        return False
    if to is not None and item.publishedAt > to:
        return False
    return True


def useful_title(value: str) -> bool:
    if len(value) < 8:
        return False
    normalized = normalize(value)
    if normalized in GENERIC_TITLES:
        return False
    if normalized.startswith("todos os videos"):
        return False
    if normalized.startswith("ultimos videos"):
        return False
    if normalized.startswith("mais videos"):
        return False
    return True


def is_generic_summary(value: str) -> bool:
    normalized = normalize(value)
    return normalized.startswith("busca por") or normalized in GENERIC_TITLES


def is_youtube_url(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return host == "youtu.be" or host.endswith("youtube.com")


def is_youtube_video_url(url: str) -> bool:
    try:
        uri = urlsplit(url)
    except ValueError:
        return False
    host = (uri.hostname or "").lower()
    path = (uri.path or "").strip("/")
    if host == "youtu.be":
        return len(path.split("/", 1)[0]) >= 6
    if not host.endswith("youtube.com"):
        return False
    if (uri.path or "").lower() == "/watch":
        video_id = ""
        for piece in (uri.query or "").split("&"):
            if piece.startswith("v="):
                video_id = piece.split("=", 1)[1]
                break
        return len(video_id) >= 6
    parts = [part for part in path.split("/") if part]
    return (
        len(parts) >= 2
        and parts[0].lower() in {"shorts", "live"}
        and len(parts[1]) >= 6
    )


def is_globoplay_source(source: VideoSource) -> bool:
    return (
        "globoplay.globo.com" in source.landingUrl.lower()
        or "globoplay.globo.com" in source.searchUrlTemplate.lower()
        or source.id.startswith("globoplay-")
        or source.id.startswith("video-globoplay")
    )


def has_specific_suffix(path: str, marker: str) -> bool:
    index = path.lower().find(marker.lower())
    if index < 0:
        return False
    suffix = path[index + len(marker):].strip("/")
    if len(suffix) < 4:
        return False
    normalized_suffix = normalize(suffix)
    return bool(normalized_suffix) and normalized_suffix not in GENERIC_SLUGS


def is_specific_video_url(source: VideoSource, url: str) -> bool:
    if not url.strip():
        return False
    if is_youtube_url(url):
        return is_youtube_video_url(url)
    if any(ch.isspace() for ch in url):
        return False
    try:
        uri = urlsplit(url)
    except ValueError:
        return False
    path = uri.path or ""
    normalized_path = path.lower().rstrip("/")
    if not normalized_path or normalized_path == "/":
        return False
    if any(normalized_path == item or normalized_path.endswith(item) for item in GENERIC_PATHS):
        return False
    if "/busca" in normalized_path or "/search" in normalized_path:
        return False
    if is_globoplay_source(source):
        return bool(_GLOBOPLAY_DIRECT_PATH_RE.search(path))
    if source.id == "video-r7-record":
        return has_specific_suffix(path, "/videos/") or has_specific_suffix(path, "/video/")
    if source.id.startswith("video-r7-"):
        return any(has_specific_suffix(path, hint) for hint in source.linkHints)
    if source.id == "video-sbt-news":
        return has_specific_suffix(path, "/videos/")
    if source.id == "video-cnn-brasil":
        return has_specific_suffix(path, "/videos/") or has_specific_suffix(path, "/video/")
    if source.id.startswith("video-band"):
        return has_specific_suffix(path, "/videos/")
    return any(has_specific_suffix(path, hint) for hint in source.linkHints)


def prioritize_globoplay_candidates(
    candidates: list[VideoItem],
    source: VideoSource,
    terms: list[str],
    demands: list[Demand],
) -> list[VideoItem]:
    if len(candidates) <= 1:
        return candidates
    indexed = list(enumerate(candidates))
    indexed.sort(
        key=lambda pair: (
            -int(
                any(phrase_matches(f"{pair[1].title} {pair[1].summary}", term) for term in terms)
                or any(
                    source_matches_demand(source, demand.vehicle)
                    and phrase_matches(f"{pair[1].title} {pair[1].summary}", demand.subject)
                    for demand in demands
                )
            ),
            pair[0],
        )
    )
    return [item for _, item in indexed]
