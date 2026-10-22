from __future__ import annotations
from types import SimpleNamespace
from monitor_noticias.ui.source_list_logos_patch import _source_site

def test_source_logo_resolves_direct_site_url_first():
    source = SimpleNamespace(name="Canal Teste", url="https://canal-teste.example/videos")
    assert _source_site(source) == "https://canal-teste.example/"

def test_source_logo_uses_known_news_vehicle_fallback():
    source = SimpleNamespace(name="G1")
    assert _source_site(source) == "https://g1.globo.com/"

def test_source_logo_without_known_site_falls_back_without_crashing():
    source = SimpleNamespace(name="Fonte sem domínio cadastrado")
    assert _source_site(source) == ""
