from __future__ import annotations

from monitor_noticias.models import VideoSource
from .catalog_helpers import globoplay_sweep, national_globo, youtube
from .catalog_regions_a import GLOBOPLAY_REGIONAL_A
from .catalog_regions_b import GLOBOPLAY_REGIONAL_B
from .sources import DESKTOP_VIDEO_EXTRAS

PORTAL_NATIONAL = [
    VideoSource(id="video-globoplay-jornalismo",name="Globoplay Jornalismo (geral)",group="Globo / Globoplay",landingUrl="https://globoplay.globo.com/categorias/jornalismo/",linkHints=["/v/"],aliases=["Globo","Globoplay","GloboNews","Globo News"],searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}"),
    VideoSource(id="video-r7-record",name="R7 / Record",group="Record",landingUrl="https://noticias.r7.com/videos/",linkHints=["/videos/"],aliases=["R7","Record","Record TV","Record News"],searchUrlTemplate="https://noticias.r7.com/busca?q={query}"),
    VideoSource(id="video-cnn-brasil",name="CNN Brasil",group="CNN",landingUrl="https://www.cnnbrasil.com.br/ao-vivo/",linkHints=["/ao-vivo/","/videos/"],aliases=["CNN","CNN Brasil"],searchUrlTemplate="https://www.cnnbrasil.com.br/?s={query}"),
    VideoSource(id="video-sbt-news",name="SBT News",group="SBT",landingUrl="https://sbtnews.sbt.com.br/videos/ao-vivo",linkHints=["/videos/"],aliases=["SBT","SBT News"],searchUrlTemplate="https://sbtnews.sbt.com.br/busca?q={query}"),
    VideoSource(id="video-band",name="Band Jornalismo",group="Band",landingUrl="https://www.band.com.br/videos",linkHints=["/videos/"],aliases=["Band","Band Jornalismo","BandNews","Band News"],searchUrlTemplate="https://www.band.com.br/busca?q={query}"),
]
PORTAL_PROGRAMS_NATIONAL = [
    VideoSource(id="video-band-jornal-da-band",name="Jornal da Band",group="Band • Jornal da Band",landingUrl="https://www.band.com.br/programas/jornal-da-band",linkHints=["/noticias/jornal-da-band/videos/"],aliases=["Band","Jornal da Band","JDB"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Jornal da Band"),
    VideoSource(id="video-band-brasil-urgente",name="Brasil Urgente",group="Band • Brasil Urgente",landingUrl="https://www.band.com.br/programas/brasil-urgente",linkHints=["/noticias/brasil-urgente/videos/"],aliases=["Band","Brasil Urgente","BU"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Brasil Urgente"),
    VideoSource(id="video-r7-jornal-da-record",name="Jornal da Record",group="Record • Jornal da Record",landingUrl="https://noticias.r7.com/jr-na-tv/videos/",linkHints=["/jr-na-tv/videos/"],aliases=["Record","Record TV","Jornal da Record","JR","JR na TV"],searchUrlTemplate="https://noticias.r7.com/busca?q={query}",searchPrefix="Jornal da Record"),
    VideoSource(id="video-r7-domingo-espetacular",name="Domingo Espetacular",group="Record • Domingo Espetacular",landingUrl="https://record.r7.com/domingo-espetacular/videos/",linkHints=["/domingo-espetacular/videos/","/domingo-espetacular/video/"],aliases=["Record","Record TV","Domingo Espetacular"],searchUrlTemplate="https://www.r7.com/busca?q={query}",searchPrefix="Domingo Espetacular"),
    VideoSource(id="video-r7-balanco-geral-sp",name="Balanço Geral SP",group="Record • Balanço Geral",region="Sudeste",state="SP",landingUrl="https://record.r7.com/balanco-geral/videos/",linkHints=["/balanco-geral/videos/"],aliases=["Record","Record TV","Balanço Geral","Balanço Geral SP","BG SP"],searchUrlTemplate="https://www.r7.com/busca?q={query}",searchPrefix="Balanço Geral SP"),
]
PORTAL_PROGRAMS_REGIONAL = [
    VideoSource(id="video-band-jornal-do-rio",name="Jornal do Rio",group="Band Regional • Jornal do Rio",region="Sudeste",state="RJ",landingUrl="https://www.band.com.br/rio-de-janeiro/videos",linkHints=["/rio-de-janeiro/videos/"],aliases=["Band","Band Rio","Jornal do Rio"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Jornal do Rio"),
    VideoSource(id="video-r7-balanco-geral-rj",name="Balanço Geral RJ",group="Record • Balanço Geral",region="Sudeste",state="RJ",landingUrl="https://record.r7.com/balanco-geral-rj/videos/",linkHints=["/balanco-geral-rj/videos/"],aliases=["Record","Record TV","Balanço Geral","Balanço Geral RJ","BG RJ"],searchUrlTemplate="https://www.r7.com/busca?q={query}",searchPrefix="Balanço Geral RJ"),
]
YOUTUBE_OFFICIAL = [
    youtube("youtube-cnn-brasil","CNN Brasil","@CNNBrasil",["CNN","CNN Brasil"]),
    youtube("youtube-jovem-pan-news","Jovem Pan News","@jovempannews",["Jovem Pan","Jovem Pan News","JP News"]),
    youtube("youtube-globonews","GloboNews","@globonews",["GloboNews","Globo News","Globo"]),
    youtube("youtube-record-news","Record News","@recordnews",["Record News","RecordNews"]),
    youtube("youtube-jornal-da-record","Jornal da Record","@JornaldaRecord",["Jornal da Record","JR","Record TV"]),
    youtube("youtube-band-jornalismo","Band Jornalismo","@bandjornalismo",["Band","Band Jornalismo","BandNews","Band News","BandNews TV"]),
    youtube("youtube-sbt-news","SBT News","@sbtnews",["SBT","SBT News","SBT Jornalismo"]),
]
GLOBOPLAY_NATIONAL = [
    national_globo("globoplay-bom-dia-brasil","Bom Dia Brasil"), national_globo("globoplay-hora-1","Hora 1"),
    national_globo("globoplay-jornal-hoje","Jornal Hoje"), national_globo("globoplay-jornal-nacional","Jornal Nacional"),
    national_globo("globoplay-jornal-da-globo","Jornal da Globo"), national_globo("globoplay-fantastico","Fantástico"),
]
GLOBOPLAY_REGIONAL_SPECIFIC = [*GLOBOPLAY_REGIONAL_A,*GLOBOPLAY_REGIONAL_B]
GLOBOPLAY_REGIONAL_SWEEPS = [
    globoplay_sweep("globoplay-regionais-bom-dia","Globoplay • Cobertura ampla — Bom Dia","Bom Dia",["Bom Dia regional"]),
    globoplay_sweep("globoplay-regionais-primeira-edicao","Globoplay • Cobertura ampla — 1ª Edições","1ª Edição",["Primeira Edição","1a Edição"]),
    globoplay_sweep("globoplay-regionais-segunda-edicao","Globoplay • Cobertura ampla — 2ª Edições","2ª Edição",["Segunda Edição","2a Edição"]),
]
BAND_REGIONAL = [
    VideoSource(id="video-band-brasilia",name="Band Brasília",group="Band Regional",region="Centro-Oeste",state="DF",landingUrl="https://www.band.com.br/band-brasilia/videos",linkHints=["/band-brasilia/videos/","/videos/"],aliases=["Band Brasília","Band DF"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Band Brasília"),
    VideoSource(id="video-band-minas",name="Band Minas",group="Band Regional",region="Sudeste",state="MG",landingUrl="https://www.band.com.br/minas-gerais",linkHints=["/band-minas/videos/","/minas-gerais/videos/","/videos/"],aliases=["Band Minas","Band Minas Gerais"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Band Minas"),
    VideoSource(id="video-band-rio",name="Band Rio",group="Band Regional",region="Sudeste",state="RJ",landingUrl="https://www.band.com.br/rio-de-janeiro/videos",linkHints=["/rio-de-janeiro/videos/","/videos/"],aliases=["Band Rio","Band Rio de Janeiro"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Band Rio"),
    VideoSource(id="video-band-parana",name="Band Paraná",group="Band Regional",region="Sul",state="PR",landingUrl="https://www.band.com.br/band-parana",linkHints=["/band-parana/videos/","/videos/"],aliases=["Band Paraná","Band PR"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Band Paraná"),
    VideoSource(id="video-band-bahia",name="Band Bahia",group="Band Regional",region="Nordeste",state="BA",landingUrl="https://www.band.com.br/ao-vivo/band-bahia",linkHints=["/band-bahia/videos/","/videos/"],aliases=["Band Bahia","Band BA"],searchUrlTemplate="https://www.band.com.br/busca?q={query}",searchPrefix="Band Bahia"),
]
NATIONAL = [*PORTAL_NATIONAL,*PORTAL_PROGRAMS_NATIONAL,*YOUTUBE_OFFICIAL,*GLOBOPLAY_NATIONAL]
REGIONAL = [*BAND_REGIONAL,*PORTAL_PROGRAMS_REGIONAL,*GLOBOPLAY_REGIONAL_SPECIFIC,*GLOBOPLAY_REGIONAL_SWEEPS]
BASE_VIDEO_SOURCES = [*NATIONAL,*REGIONAL]
VIDEO_SOURCES = list({source.id:source for source in [*BASE_VIDEO_SOURCES,*DESKTOP_VIDEO_EXTRAS]}.values())
BY_ID = {source.id:source for source in VIDEO_SOURCES}
DEFAULT_IDS = {source.id for source in NATIONAL} | {source.id for source in DESKTOP_VIDEO_EXTRAS}
YOUTUBE_OFFICIAL_IDS = {source.id for source in YOUTUBE_OFFICIAL}
GLOBOPLAY_TELEJOURNAL_IDS = {source.id for source in [*GLOBOPLAY_NATIONAL,*GLOBOPLAY_REGIONAL_SPECIFIC]}
GLOBOPLAY_REGIONAL_SWEEP_IDS = {source.id for source in GLOBOPLAY_REGIONAL_SWEEPS}
PORTAL_PROGRAM_SCAN_IDS = {source.id for source in [*PORTAL_PROGRAMS_NATIONAL,*PORTAL_PROGRAMS_REGIONAL,*BAND_REGIONAL]} | {"video-r7-record","video-sbt-news","video-band"}
CORE_NATIONAL_GLOBOPLAY_IDS = {"globoplay-bom-dia-brasil","globoplay-hora-1","globoplay-jornal-hoje","globoplay-jornal-nacional","globoplay-jornal-da-globo"}

def selected(ids):
    return [BY_ID[id_] for id_ in ids if id_ in BY_ID]
