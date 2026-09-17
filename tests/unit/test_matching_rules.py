from monitor_noticias.matching import (
    canonical_key,
    canonicalize_url,
    clean_video_terms,
    demand_vehicle_matches,
    is_generic_summary,
    is_specific_video_url,
    merge_news,
    merge_video,
    phrase_matches,
    prioritize_globoplay_candidates,
    repository_video_phrase_matches,
    reuse_historical_identity,
    same_page,
    source_matches_demand,
    source_matches_strict,
    story_key,
    subject_matches,
    useful_title,
)
from monitor_noticias.models import Demand, MediaSource, News, VideoItem, VideoSource


def test_news_normalization_case_accents_and_word_boundaries():
    assert subject_matches("São Paulo", "Sao Paulo")
    assert subject_matches("GLOBO", "globo")
    assert not subject_matches("prioridade", "rio")
    assert subject_matches("Rio de Janeiro", "rio")
    assert subject_matches("Rio\nde\tJaneiro", "Rio de Janeiro")


def test_news_multiword_fallback_ignores_stop_words_and_order():
    assert subject_matches("Janeiro recebe evento no Rio", "Rio de Janeiro")
    assert not subject_matches("Rio recebe evento", "Rio de Janeiro")
    assert subject_matches("qualquer texto", "   ")


def test_news_vehicle_and_source_matching_exact_kotlin_rules():
    assert demand_vehicle_matches("g1.globo.com", "g1")
    assert demand_vehicle_matches("Folha de S.Paulo", "Folha de S Paulo")
    assert not demand_vehicle_matches("CNN Brasil", "Globo")
    selected = MediaSource(
        id="nacional-folha", name="Folha de S.Paulo", region="Nacional",
        state="", stateName="", group="Nacional",
        aliases=["Folha de São Paulo", "Folha"],
    )
    assert source_matches_strict("Folha de São Paulo", selected)
    assert not source_matches_strict("Folha Vitória", selected)


def test_news_story_identity_merge_and_first_capture_are_stable():
    previous = News(
        title="Marinha em operação", source="G1 Notícias", date=100,
        link="https://old", demand=True, matchedTerm="MARINHA",
        matchedDemand="G1 • Marinha", capturedAt=111,
    )
    incoming = News(
        title="Marinha em operação", source="G1", date=200,
        link="https://new", important=True, matchedTerm="MARINHA, PROSUB",
        capturedAt=999,
    )
    assert story_key(previous) == story_key(incoming)
    merged = merge_news(previous, incoming)
    assert merged.important is True and merged.demand is True
    assert merged.matchedTerm == "MARINHA, PROSUB"
    assert merged.matchedDemand == "G1 • Marinha"
    assert merged.capturedAt == 111
    stable = reuse_historical_identity(incoming, [previous])
    assert stable.link == "https://old" and stable.capturedAt == 111


def test_video_policy_and_repository_matcher_keep_blank_difference():
    assert phrase_matches("qualquer texto", "") is False
    assert repository_video_phrase_matches("qualquer texto", "") is True


def test_video_matcher_flexions_september_event_case_accents_and_substring():
    assert repository_video_phrase_matches("Militares participam", "militar")
    assert repository_video_phrase_matches("Desfile de 7 de Setembro", "comemoração 7 setembro")
    assert repository_video_phrase_matches("FORÇAS ARMADAS", "forcas armadas")
    assert not repository_video_phrase_matches("prioridade", "rio")


def test_video_source_demand_matching_contains_rule():
    source = VideoSource(
        id="globoplay-jornal-nacional", name="Jornal Nacional", group="Globo",
        landingUrl="https://globoplay.globo.com/jornal-nacional/", aliases=["JN"],
    )
    assert source_matches_demand(source, "Globo")
    assert source_matches_demand(source, "Jornal")
    assert source_matches_demand(source, "Jornal Nacional")
    assert not source_matches_demand(source, "Band News")


def test_video_canonicalization_and_logical_dedup_key():
    expected = "https://www.youtube.com/watch?v=abcdef12"
    assert canonicalize_url("https://youtu.be/abcdef12?t=30") == expected
    assert canonicalize_url("https://www.youtube.com/shorts/abcdef12?feature=share") == expected
    assert canonicalize_url("https://www.youtube.com/watch?v=abcdef12&list=x") == expected
    assert canonicalize_url("https://EXAMPLE.com/noticia/?utm_source=x#frag").lower() == "https://example.com/noticia"
    assert same_page("https://example.com/a/?x=1", "https://example.com/a")
    assert canonical_key("HTTPS://EXAMPLE.COM/A/") == "https://example.com/a"


def test_video_merge_preserves_union_demand_and_max_capture():
    previous = VideoItem(
        title="A", sourceId="s", sourceName="S", publishedAt=100,
        link="https://x/v/1", matchedTerm="MARINHA", matchedDemand="S • Tema",
        capturedAt=900,
    )
    incoming = VideoItem(
        title="B", sourceId="s", sourceName="S", publishedAt=200,
        link="https://x/v/1", matchedTerm="MARINHA, PROSUB", capturedAt=800,
    )
    merged = merge_video(previous, incoming)
    assert merged.matchedTerm == "MARINHA, PROSUB"
    assert merged.matchedDemand == "S • Tema"
    assert merged.capturedAt == 900 and merged.title == "B"


def test_video_exclusion_rules_for_titles_summaries_and_urls():
    globoplay = VideoSource(
        id="globoplay-jornal-nacional", name="Jornal Nacional", group="Globo",
        landingUrl="https://globoplay.globo.com/jornal-nacional/",
    )
    assert not useful_title("Vídeos")
    assert not useful_title("Todos os vídeos recentes")
    assert useful_title("Marinha participa de operação")
    assert is_generic_summary("Busca por marinha")
    assert is_specific_video_url(globoplay, "https://globoplay.globo.com/v/123456/")
    assert not is_specific_video_url(globoplay, "https://globoplay.globo.com/videos/")
    assert not is_specific_video_url(globoplay, "https://globoplay.globo.com/busca/?q=marinha")


def test_globoplay_priority_is_match_first_and_stable():
    source = VideoSource(
        id="globoplay-jornal-nacional", name="Jornal Nacional", group="Globo",
        landingUrl="https://globoplay.globo.com/jornal-nacional/",
    )
    items = [
        VideoItem(title="Economia do dia", sourceId=source.id, sourceName=source.name, publishedAt=1, link="https://globoplay.globo.com/v/100001/", capturedAt=1),
        VideoItem(title="Marinha realiza exercício", sourceId=source.id, sourceName=source.name, publishedAt=2, link="https://globoplay.globo.com/v/100002/", capturedAt=2),
        VideoItem(title="PROSUB avança", sourceId=source.id, sourceName=source.name, publishedAt=3, link="https://globoplay.globo.com/v/100003/", capturedAt=3),
        VideoItem(title="Tempo no país", sourceId=source.id, sourceName=source.name, publishedAt=4, link="https://globoplay.globo.com/v/100004/", capturedAt=4),
    ]
    ordered = prioritize_globoplay_candidates(items, source, ["MARINHA", "PROSUB"], [])
    assert [item.link for item in ordered] == [
        "https://globoplay.globo.com/v/100002/",
        "https://globoplay.globo.com/v/100003/",
        "https://globoplay.globo.com/v/100001/",
        "https://globoplay.globo.com/v/100004/",
    ]


def test_video_term_cleaning_rule_without_persistence():
    values = ["  Marinha ", "marinha", "", "PROSUB", "  fab", "FAB  "]
    assert clean_video_terms(values) == ["fab", "Marinha", "PROSUB"]
