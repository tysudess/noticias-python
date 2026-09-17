from .news_rules import (
    demand_vehicle_matches,
    merge_news,
    reuse_historical_identity,
    source_matches_strict,
    story_key,
    subject_matches,
)
from .term_rules import clean_video_terms
from .video_match_policy import phrase_matches
from .video_rules import (
    canonical_key,
    canonicalize_url,
    in_period,
    is_generic_summary,
    is_specific_video_url,
    is_youtube_url,
    is_youtube_video_url,
    merge_video,
    phrase_matches as repository_video_phrase_matches,
    prioritize_globoplay_candidates,
    same_page,
    source_matches_demand,
    useful_title,
)

__all__ = [
    "canonical_key", "canonicalize_url", "clean_video_terms", "demand_vehicle_matches",
    "in_period", "is_generic_summary", "is_specific_video_url", "is_youtube_url",
    "is_youtube_video_url", "merge_news", "merge_video", "phrase_matches",
    "prioritize_globoplay_candidates", "repository_video_phrase_matches",
    "reuse_historical_identity", "same_page", "source_matches_demand",
    "source_matches_strict", "story_key", "subject_matches", "useful_title",
]
