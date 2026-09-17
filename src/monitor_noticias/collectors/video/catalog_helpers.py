from __future__ import annotations

from urllib.parse import quote_plus
from monitor_noticias.models import VideoSource

REGIONAL_GLOBO_ALIASES = [
    "TV Globo","Globo SP","Globo Rio","Globo Minas","Globo Brasília","Globo Pernambuco",
    "Rede Amazônica","TV Acre","TV Amapá","TV Amazonas","TV Rondônia","TV Roraima",
    "TV Gazeta","TV Gazeta AL","TV Gazeta ES","TV Bahia","TV Verdes Mares","TV Anhanguera",
    "TV Mirante","TV Centro América","TV Morena","TV Liberal","TV Tapajós","TV Cabo Branco",
    "RPC","TV Clube","Inter TV Cabugi","RBS TV","NSC TV","EPTV","TV TEM","TV Tribuna",
    "TV Fronteira","TV Sergipe","TV Anhanguera Tocantins",
]

def globoplay_search(program: str) -> str:
    return "https://globoplay.globo.com/busca/?q=" + quote_plus(program)

def youtube(id_: str, label: str, handle: str, aliases: list[str]) -> VideoSource:
    return VideoSource(id=id_, name=f"YouTube • {label}", group=f"YouTube oficial • {label}", landingUrl=f"https://www.youtube.com/{handle}/videos", linkHints=["/watch"], aliases=aliases, youtubeHandle=handle)

def national_globo(id_: str, program: str) -> VideoSource:
    return VideoSource(id=id_, name=f"Globoplay • {program}", group="Globo / Globoplay • Telejornal nacional", landingUrl=globoplay_search(program), linkHints=["/v/"], aliases=["Globo","Globoplay",program], searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}", searchPrefix=program)

def regional_globo(id_: str, program: str, state: str, region: str, aliases: list[str] | None = None, landing_override: str = "") -> VideoSource:
    merged = list(dict.fromkeys(["Globo","Globoplay",program,*(aliases or [])]))
    return VideoSource(id=id_, name=f"Globoplay • {program}", group="Globo / Globoplay • Telejornal regional", region=region, state=state, landingUrl=landing_override or globoplay_search(program), linkHints=["/v/"], aliases=merged, searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}", searchPrefix=program)

def globoplay_sweep(id_: str, name: str, program: str, aliases: list[str]) -> VideoSource:
    return VideoSource(id=id_, name=name, group="Globo / Globoplay • Cobertura regional ampla", region="Todas", state="BR", landingUrl=globoplay_search(program), linkHints=["/v/"], aliases=list(dict.fromkeys([*REGIONAL_GLOBO_ALIASES,*aliases])), searchUrlTemplate="https://globoplay.globo.com/busca/?q={query}", searchPrefix=program)
