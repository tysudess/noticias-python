from __future__ import annotations
from datetime import datetime
import re
from urllib.parse import urljoin

from monitor_noticias.matching.common import normalize
from monitor_noticias.models import VideoItem

BROWSER_UA = "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
VIDEO_LINK_RE = re.compile(r'(?:https?://globoplay\.globo\.com)?/v/([0-9]{5,})/?', re.I)
PROGRAM_LINK_RE = re.compile(r'(?:https?://globoplay\.globo\.com/)?([^/"\\]+?)/t/([A-Za-z0-9_-]+)', re.I)
EMBED_TITLE_RE = re.compile(r'"(?:headline|title|name)"\s*:\s*"([^"]+)"', re.I)
EMBED_SUMMARY_RE = re.compile(r'"(?:description|summary|seoDescription)"\s*:\s*"([^"]+)"', re.I)
EMBED_DATE_RE = re.compile(r'"(?:datePublished|uploadDate|dateCreated|publishedAt|publicationDate|publishedDate|exhibitedAt)"\s*:\s*"([^"]+)"', re.I)
SECTION_DATE_RE = re.compile(r'(\d{2}/\d{2}/\d{4})')
DURATION_PREFIX_RE = re.compile(r'^\s*\d{1,2}:\d{2}(?::\d{2})?\s*[-–—•|]?\s*')
UNICODE_ESCAPE_RE = re.compile(r'\\u([0-9a-fA-F]{4})')

def clean_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()

def normalize_embedded(value: str) -> str:
    return (value.replace(r'\/', '/').replace(r'\u002F', '/').replace(r'\u002f', '/')
            .replace(r'\u003A', ':').replace(r'\u003a', ':').replace(r'\u0026', '&')
            .replace(r'\u003D', '=').replace(r'\u003d', '=').replace(r'\"', '"'))

def clean_json_text(value: str) -> str:
    decoded = normalize_embedded(value).replace(r'\n', ' ').replace(r'\r', ' ').replace(r'\t', ' ').replace(r'\\', '\\')
    decoded = UNICODE_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 16)), decoded)
    return clean_text(decoded).replace('&quot;', '"').replace('&#39;', "'")

def normalize_program_page(value: str) -> str | None:
    if not value.strip(): return None
    match = PROGRAM_LINK_RE.search(normalize_embedded(value))
    return f"https://globoplay.globo.com/{match.group(1)}/t/{match.group(2)}" if match else None

def normalize_direct_video_url(value: str) -> str | None:
    if not value.strip(): return None
    match = VIDEO_LINK_RE.search(normalize_embedded(value))
    return f"https://globoplay.globo.com/v/{match.group(1)}" if match else None

def resolve_url(base: str, value: str) -> str:
    return urljoin(base, value)

def parse_iso_ms(value: str, captured_at: int) -> int | None:
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        millis = int(dt.timestamp() * 1000)
        return millis if 1 <= millis <= captured_at else None
    except Exception:
        return None

def parse_day_upper(value: str, captured_at: int) -> int | None:
    match = SECTION_DATE_RE.search(value)
    if not match: return None
    try:
        day = datetime.strptime(match.group(1), '%d/%m/%Y').astimezone()
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        if int(start.timestamp() * 1000) > captured_at: return None
        end = day.replace(hour=23, minute=59, second=59, microsecond=999000)
        return min(int(end.timestamp() * 1000), captured_at)
    except Exception:
        return None

def clean_trecho_title(value: str, program: str) -> str:
    title = DURATION_PREFIX_RE.sub('', clean_text(value)).strip(' -•|')
    if program and title.lower().endswith(program.lower()):
        title = title[:-len(program)].strip(' -•|')
    return title

def useful_globo_title(value: str) -> bool:
    if len(value) < 8: return False
    return normalize(value) not in {'video', 'videos', 'mais videos', 'todos os videos', 'ultimos videos', 'ao vivo', 'globoplay'}

def candidate_quality(item: VideoItem) -> int:
    score = 0
    if not item.title.lower().startswith('trecho recente •'): score += 30
    if item.summary: score += min(len(item.summary) // 30, 20)
    if item.publishedAt > 0 and item.publishedAt != item.capturedAt: score += 8
    return score
