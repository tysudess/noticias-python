from monitor_noticias.ui.catalog import NEWS_SOURCES, REGIONS, SPECIALIZED, STATES
from monitor_noticias.ui.sections import SECTION_ORDER, Section
from monitor_noticias.ui.theme import V5_BG, V5_BLUE, V5_GREEN, V5_INK, V5_NAVY, V5_ORANGE, V5_PURPLE, V5_RED


def test_dashboard_v5_section_order_after_release_transform():
    assert [s.name for s in SECTION_ORDER] == [
        "HOME","NEWS","VIDEOS","DEMANDS","SOURCES","HISTORY","TERMS","STOP","SETTINGS","PDF_EDITOR","EXTRACTOR","VIDEO_EDITOR"
    ]
    assert [s.value.label for s in SECTION_ORDER] == [
        "Início","Notícias","Vídeos","Demandas","Fontes","Histórico","Termos","Parar buscas","Configurações","Editor de PDF","Extrator de Vídeos","Editor de Vídeo"
    ]


def test_dashboard_v5_visual_identity_constants():
    assert (V5_NAVY,V5_INK,V5_BG,V5_BLUE,V5_PURPLE,V5_ORANGE,V5_GREEN,V5_RED)==(
        "#052D57","#0A1F4B","#F3F8FE","#087AF7","#743AF3","#FF820A","#08A86F","#D92F43"
    )


def test_source_catalog_static_contract():
    assert REGIONS == ("Todas","Nacional","Norte","Nordeste","Centro-Oeste","Sudeste","Sul")
    assert len(STATES)==27
    assert len(NEWS_SOURCES)==160
    assert len(SPECIALIZED)==12
    assert NEWS_SOURCES[0].id=="nacional-o-globo"
    assert any(s.id=="especializada-agencia-marinha" and s.name=="Agência Marinha de Notícias" for s in NEWS_SOURCES)


def test_tool_sections_are_visual_integration_points_only():
    assert Section.PDF_EDITOR.value.label=="Editor de PDF"
    assert Section.EXTRACTOR.value.label=="Extrator de Vídeos"
    assert Section.VIDEO_EDITOR.value.label=="Editor de Vídeo"
