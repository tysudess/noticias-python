from __future__ import annotations

import json
from pathlib import Path

from monitor_noticias.matching import (
    canonicalize_url,
    repository_video_phrase_matches,
    subject_matches,
)


def _golden() -> dict:
    path = Path(__file__).with_name("golden_matching_cases.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_news_subject_golden_cases_from_kotlin_rules():
    for case in _golden()["news_subject"]:
        assert subject_matches(case["text"], case["subject"]) is case["expected"]


def test_video_phrase_golden_cases_from_kotlin_rules():
    for case in _golden()["video_phrase"]:
        assert repository_video_phrase_matches(case["text"], case["phrase"]) is case["expected"]


def test_canonical_url_golden_cases_from_kotlin_rules():
    for case in _golden()["canonical_url"]:
        assert canonicalize_url(case["value"]) == case["expected"]
