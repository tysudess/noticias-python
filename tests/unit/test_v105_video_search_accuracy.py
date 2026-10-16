from __future__ import annotations

from pathlib import Path

from monitor_noticias.collectors.video.catalog import BY_ID
from monitor_noticias.collectors.video.youtube import _relative_ms, parse_feed, parse_videos_tab
from monitor_noticias.matching.video_rules import in_period, is_specific_video_url
from monitor_noticias.models import VideoItem, VideoSource
from monitor_noticias.repositories.video_search import _collect_national_portal_fallback

ROOT = Path(__file__).resolve().parents[2]


def test_youtube_unknown_publish_time_is_not_replaced_with_capture_time():
    captured = 1_800_000_000_000
    assert _relative_ms("", captured) == 0
    assert _relative_ms("data não identificada", captured) == 0
    assert _relative_ms("há 3 horas", captured) == captured - 3 * 60 * 60_000


def test_youtube_tab_with_missing_date_remains_undated():
    captured = 1_800_000_000_000
    source = VideoSource(
        id="youtube-cnn-brasil",
        name="YouTube • CNN Brasil",
        group="YouTube oficial • CNN Brasil",
        landingUrl="https://www.youtube.com/@CNNBrasil/videos",
        youtubeHandle="@CNNBrasil",
    )
    html = (
        '{"videoId":"Abcdef12345","title":{"runs":'
        '[{"text":"CNN Brasil explica operação naval"}]}'
    )
    items = parse_videos_tab(source, html, captured)
    assert len(items) == 1
    assert items[0].publishedAt == 0
    assert items[0].capturedAt == captured


def test_unknown_dates_do_not_pass_a_period_filter():
    item = VideoItem(
        title="Vídeo sem data confirmada",
        sourceId="youtube-cnn-brasil",
        sourceName="YouTube • CNN Brasil",
        publishedAt=0,
        link="https://www.youtube.com/watch?v=Abcdef12345",
        capturedAt=1_800_000_000_000,
    )
    assert not in_period(item, 1_799_900_000_000, 1_800_000_000_000)


def test_band_program_sources_reject_generic_video_routes():
    program = BY_ID["video-band-jornal-da-band"]
    general = BY_ID["video-band"]
    specific_link = "https://www.band.com.br/noticias/jornal-da-band/videos/jornal-completo"
    generic_link = "https://www.band.com.br/videos/noticia-do-dia"
    assert is_specific_video_url(program, specific_link)
    assert not is_specific_video_url(program, generic_link)
    assert is_specific_video_url(general, generic_link)


def test_national_portal_fallback_uses_search_when_landing_has_no_match():
    source = BY_ID["video-band-jornal-da-band"]
    captured = 1_800_000_000_000
    landing_item = VideoItem(
        title="Previsão do tempo desta manhã",
        sourceId=source.id,
        sourceName=source.name,
        publishedAt=captured - 60_000,
        link="https://www.band.com.br/noticias/jornal-da-band/videos/previsao-do-tempo",
        summary="Previsão do tempo",
        capturedAt=captured,
    )
    found_item = VideoItem(
        title="Marinha realiza exercício naval",
        sourceId=source.id,
        sourceName=source.name,
        publishedAt=captured - 60_000,
        link="https://www.band.com.br/noticias/jornal-da-band/videos/marinha-exercicio-naval",
        summary="Operação da Marinha",
        capturedAt=captured,
    )

    class FakeWebsite:
        calls = []

        def fetch_search_website(self, _source, query, _captured):
            self.calls.append(query)
            return [found_item]

    class FakeRepo:
        website = FakeWebsite()

    repo = FakeRepo()
    result = _collect_national_portal_fallback(
        repo, source, [landing_item], ["Marinha"], [], captured, None, lambda _stage: None
    )
    assert "Marinha" in repo.website.calls
    assert result[0].title == found_item.title
    assert any(item.title == landing_item.title for item in result)


def test_regional_sources_are_not_given_extra_search_fallback_yet():
    source = BY_ID["video-band-brasilia"]

    class FakeWebsite:
        def fetch_search_website(self, *_args):
            raise AssertionError("fallback regional não deve ser expandido nesta etapa")

    class FakeRepo:
        website = FakeWebsite()

    candidates = []
    result = _collect_national_portal_fallback(
        FakeRepo(), source, candidates, ["Marinha"], [], 1_800_000_000_000, None, lambda _stage: None
    )
    assert result == candidates


def test_search_code_keeps_early_date_filter_and_scoped_national_fallback():
    text = (ROOT / "src/monitor_noticias/repositories/video_search.py").read_text(encoding="utf-8")
    assert "if original.publishedAt > 0 and not in_period(original, effective_from, effective_to):" in text
    assert "MAX_NATIONAL_PORTAL_FALLBACK_TERMS = 6" in text
    assert "str(getattr(source, \"region\", \"Nacional\") or \"Nacional\") != \"Nacional\"" in text


def test_youtube_feed_without_publish_date_stays_undated():
    source = VideoSource(
        id="youtube-cnn-brasil",
        name="YouTube • CNN Brasil",
        group="YouTube oficial • CNN Brasil",
        landingUrl="https://www.youtube.com/@CNNBrasil/videos",
        youtubeHandle="@CNNBrasil",
    )
    xml = (
        '<feed><entry><title>CNN Brasil explica operação naval</title>'
        '<link href="https://www.youtube.com/watch?v=Abcdef12345" />'
        '</entry></feed>'
    )
    items = parse_feed(source, xml, 1_800_000_000_000)
    assert len(items) == 1
    assert items[0].publishedAt == 0


def test_globoplay_general_can_use_national_search_fallback():
    source = BY_ID["video-globoplay-jornalismo"]
    captured = 1_800_000_000_000
    match = VideoItem(
        title="Marinha realiza exercício naval",
        sourceId=source.id,
        sourceName=source.name,
        publishedAt=captured - 60_000,
        link="https://globoplay.globo.com/v/1234567/",
        summary="Operação da Marinha",
        capturedAt=captured,
    )

    class FakeWebsite:
        calls = []

        def fetch_search_website(self, _source, query, _captured):
            self.calls.append(query)
            return [match]

    class FakeRepo:
        website = FakeWebsite()

    repo = FakeRepo()
    result = _collect_national_portal_fallback(
        repo, source, [], ["Marinha"], [], captured, None, lambda _stage: None
    )
    assert "Marinha" in repo.website.calls
    assert result and result[0].title == match.title
