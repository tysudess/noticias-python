from monitor_noticias.extractor import EXTRACTOR_QUALITIES, classify_source, normalize_r7_url


def test_quality_labels_and_limits_match_v8_release_contract():
    assert [(q.label,q.max_height) for q in EXTRACTOR_QUALITIES] == [
        ("360p",360),("480p",480),("720p HD",720),("1080p Full HD",1080),("Melhor disponível",None)
    ]


def test_720p_selectors_match_kotlin_contract():
    q=EXTRACTOR_QUALITIES[2]
    assert q.selector == "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b[height<=720]/b"
    assert q.compat == "b[height<=720][ext=mp4]/b[height<=720]/b"


def test_source_routes_match_release():
    cases={
        "https://youtube.com/watch?v=x":"youtube",
        "https://youtu.be/x":"youtube",
        "https://globoplay.globo.com/v/123456":"globoplay",
        "globo:123456":"globoplay",
        "https://r7.com/noticias/x":"r7",
        "https://record.r7.com/x":"r7",
        "https://example.test/page":"generic",
    }
    assert {u:classify_source(u) for u in cases} == cases


def test_r7_duplicate_url_cleanup_matches_kotlin():
    assert normalize_r7_url("https://r7.com/a https://cdn.test/b") == "https://r7.com/a%20"
