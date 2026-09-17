from __future__ import annotations

import re
import unicodedata
from monitor_noticias.models import MediaSource, VideoSource
from monitor_noticias.collectors.video.sources import DESKTOP_VIDEO_EXTRAS

REGIONS = ("Todas", "Nacional", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")
STATES = (
    ("AC","Acre","Norte"),("AP","Amapá","Norte"),("AM","Amazonas","Norte"),("PA","Pará","Norte"),("RO","Rondônia","Norte"),("RR","Roraima","Norte"),("TO","Tocantins","Norte"),
    ("AL","Alagoas","Nordeste"),("BA","Bahia","Nordeste"),("CE","Ceará","Nordeste"),("MA","Maranhão","Nordeste"),("PB","Paraíba","Nordeste"),("PE","Pernambuco","Nordeste"),("PI","Piauí","Nordeste"),("RN","Rio Grande do Norte","Nordeste"),("SE","Sergipe","Nordeste"),
    ("DF","Distrito Federal","Centro-Oeste"),("GO","Goiás","Centro-Oeste"),("MT","Mato Grosso","Centro-Oeste"),("MS","Mato Grosso do Sul","Centro-Oeste"),
    ("ES","Espírito Santo","Sudeste"),("MG","Minas Gerais","Sudeste"),("RJ","Rio de Janeiro","Sudeste"),("SP","São Paulo","Sudeste"),("PR","Paraná","Sul"),("SC","Santa Catarina","Sul"),("RS","Rio Grande do Sul","Sul"),
)

def _slug(value: str) -> str:
    normalized=unicodedata.normalize("NFD",value.lower()); clean="".join(ch for ch in normalized if unicodedata.category(ch)!="Mn")
    return re.sub(r"[^a-z0-9]+","-",clean).strip("-")

def _national(id_:str,name:str,*aliases:str)->MediaSource:
    return MediaSource(id=id_,name=name,region="Nacional",state="BR",stateName="Brasil",group="Jornais nacionais",aliases=list(aliases))

def _state(state:str,state_name:str,region:str,name:str,*aliases:str)->MediaSource:
    return MediaSource(id=f"{state.lower()}-{_slug(name)}",name=name,region=region,state=state,stateName=state_name,group=f"{state_name} • {region}",aliases=list(aliases))

def _special(id_:str,name:str,*aliases:str)->MediaSource:
    return MediaSource(id=id_,name=name,region="Nacional",state="BR",stateName="Brasil",group="Mídia especializada",aliases=list(aliases))

NATIONAL = (
    _national("nacional-o-globo","O Globo","oglobo","Globo"),_national("nacional-correio-brasiliense","Correio Braziliense","Correio Braziliense"),_national("nacional-g1","G1","g1","Globo.com"),_national("nacional-r7","R7","R7.com"),_national("nacional-revista-oeste","Revista Oeste","Oeste"),_national("nacional-folha","Folha de S.Paulo","Folha de São Paulo","Folha"),_national("nacional-estadao","Estadão","O Estado de S. Paulo","Estado de S. Paulo"),_national("nacional-valor","Valor Econômico","Valor"),_national("nacional-antagonista","O Antagonista","Antagonista"),_national("nacional-cnn","CNN Brasil","CNN"),_national("nacional-jovem-pan","Jovem Pan","JP"),_national("nacional-estado-minas","Estado de Minas","EM.com.br"),_national("nacional-metropoles","Metrópoles","Metropoles"),
)

_STATE_SPECS = (
("AC","Acre","Norte","ac24horas","AC24Horas"),("AC","Acre","Norte","ContilNet","ContilNet Notícias"),("AC","Acre","Norte","Folha do Acre"),("AC","Acre","Norte","O Rio Branco","Jornal O Rio Branco"),("AC","Acre","Norte","Ecos da Notícia","Ecos da Noticia"),
("AP","Amapá","Norte","Diário do Amapá","Diario do Amapa"),("AP","Amapá","Norte","SelesNafes.com","Seles Nafes"),("AP","Amapá","Norte","A Gazeta do Amapá","Jornal A Gazeta do Amapá"),("AP","Amapá","Norte","Amapá Digital","Amapa Digital"),("AP","Amapá","Norte","Portal do Amapá","Portal Amapá","Portal Amapa"),
("AM","Amazonas","Norte","Portal do Holanda"),("AM","Amazonas","Norte","A Crítica","A Critica"),("AM","Amazonas","Norte","D24AM","Diário do Amazonas","Diario do Amazonas"),("AM","Amazonas","Norte","Amazonas Atual"),("AM","Amazonas","Norte","Em Tempo","Amazonas Em Tempo"),
("PA","Pará","Norte","DOL","Diário Online","Diario Online"),("PA","Pará","Norte","O Liberal","Oliberal.com"),("PA","Pará","Norte","Diário do Pará","Diario do Para"),("PA","Pará","Norte","Roma News","RomaNews"),("PA","Pará","Norte","Portal Canaã","Portal Canaa"),
("RO","Rondônia","Norte","Rondoniaovivo","Rondônia ao Vivo"),("RO","Rondônia","Norte","Rondoniagora","Rondônia Agora"),("RO","Rondônia","Norte","Portal de Rondônia","Portal de Rondonia"),("RO","Rondônia","Norte","Rondonotícias","Rondonoticias"),("RO","Rondônia","Norte","EuIdeal","Eu Ideal"),
("RR","Roraima","Norte","Folha BV","Folha de Boa Vista"),("RR","Roraima","Norte","Roraima em Tempo"),("RR","Roraima","Norte","Roraima 1","Roraima1"),("RR","Roraima","Norte","Portal Norte Roraima","Portal Norte"),("RR","Roraima","Norte","Portal Roraima","Roraima Portal"),
("TO","Tocantins","Norte","Sou de Palmas"),("TO","Tocantins","Norte","AF Notícias","AF Noticias"),("TO","Tocantins","Norte","Gazeta do Cerrado"),("TO","Tocantins","Norte","Agência Tocantins","Agencia Tocantins"),("TO","Tocantins","Norte","T1 Notícias","T1 Noticias"),
("AL","Alagoas","Nordeste","TNH1"),("AL","Alagoas","Nordeste","Gazeta de Alagoas","GazetaWeb"),("AL","Alagoas","Nordeste","Cada Minuto"),("AL","Alagoas","Nordeste","7Segundos","7 Segundos"),("AL","Alagoas","Nordeste","Tribuna Hoje","Tribuna Independente"),
("BA","Bahia","Nordeste","BNews"),("BA","Bahia","Nordeste","Bahia Notícias","Bahia Noticias"),("BA","Bahia","Nordeste","Correio 24 Horas","Correio da Bahia","Correio*"),("BA","Bahia","Nordeste","iBahia","IBahia"),("BA","Bahia","Nordeste","A Tarde"),
("CE","Ceará","Nordeste","O Povo"),("CE","Ceará","Nordeste","Diário do Nordeste","Diario do Nordeste"),("CE","Ceará","Nordeste","GCMAIS","GC Mais"),("CE","Ceará","Nordeste","CN7"),("CE","Ceará","Nordeste","Ceará Agora","Ceara Agora"),
("MA","Maranhão","Nordeste","Imirante"),("MA","Maranhão","Nordeste","O Imparcial"),("MA","Maranhão","Nordeste","Jornal Pequeno"),("MA","Maranhão","Nordeste","Atual7"),("MA","Maranhão","Nordeste","Marrapá","Marrapa"),
("PB","Paraíba","Nordeste","Portal Correio"),("PB","Paraíba","Nordeste","Jornal da Paraíba","Jornal da Paraiba"),("PB","Paraíba","Nordeste","ClickPB"),("PB","Paraíba","Nordeste","WSCOM"),("PB","Paraíba","Nordeste","Polêmica Paraíba","Polemica Paraiba"),
("PE","Pernambuco","Nordeste","Jornal do Commercio","JC Online","JCPE","JC PE"),("PE","Pernambuco","Nordeste","Diario de Pernambuco","Diário de Pernambuco"),("PE","Pernambuco","Nordeste","Folha de Pernambuco"),("PE","Pernambuco","Nordeste","NE10"),("PE","Pernambuco","Nordeste","LeiaJá","LeiaJa"),
("PI","Piauí","Nordeste","Meio Norte"),("PI","Piauí","Nordeste","Cidade Verde"),("PI","Piauí","Nordeste","GP1"),("PI","Piauí","Nordeste","180graus","180 Graus"),("PI","Piauí","Nordeste","Lupa1","Lupa 1"),
("RN","Rio Grande do Norte","Nordeste","Tribuna do Norte"),("RN","Rio Grande do Norte","Nordeste","Blog do BG","BG"),("RN","Rio Grande do Norte","Nordeste","Agora RN"),("RN","Rio Grande do Norte","Nordeste","Via Certa Natal","Via Certa"),("RN","Rio Grande do Norte","Nordeste","Saiba Mais","Agência Saiba Mais"),
("SE","Sergipe","Nordeste","Infonet"),("SE","Sergipe","Nordeste","Jornal da Cidade","Jornal da Cidade Sergipe"),("SE","Sergipe","Nordeste","F5 News","F5News"),("SE","Sergipe","Nordeste","FaxAju"),("SE","Sergipe","Nordeste","NE Notícias","NE Noticias"),
("DF","Distrito Federal","Centro-Oeste","Metrópoles","Metropoles"),("DF","Distrito Federal","Centro-Oeste","Correio Braziliense"),("DF","Distrito Federal","Centro-Oeste","Jornal de Brasília","Jornal de Brasilia"),("DF","Distrito Federal","Centro-Oeste","GPS Brasília","GPS Brasilia"),("DF","Distrito Federal","Centro-Oeste","Brasília Capital","Brasilia Capital"),
("GO","Goiás","Centro-Oeste","Portal 6","Portal6"),("GO","Goiás","Centro-Oeste","O Popular"),("GO","Goiás","Centro-Oeste","Jornal Opção","Jornal Opcao"),("GO","Goiás","Centro-Oeste","Mais Goiás","Mais Goias"),("GO","Goiás","Centro-Oeste","Diário de Goiás","Diario de Goias"),
("MT","Mato Grosso","Centro-Oeste","MidiaNews"),("MT","Mato Grosso","Centro-Oeste","Olhar Direto"),("MT","Mato Grosso","Centro-Oeste","Gazeta Digital"),("MT","Mato Grosso","Centro-Oeste","RDNews"),("MT","Mato Grosso","Centro-Oeste","HiperNotícias","HiperNoticias"),
("MS","Mato Grosso do Sul","Centro-Oeste","Campo Grande News"),("MS","Mato Grosso do Sul","Centro-Oeste","Midiamax"),("MS","Mato Grosso do Sul","Centro-Oeste","TopMídiaNews","Top Midia News","TopMídia News"),("MS","Mato Grosso do Sul","Centro-Oeste","O Jacaré","O Jacare"),("MS","Mato Grosso do Sul","Centro-Oeste","Correio do Estado"),
("ES","Espírito Santo","Sudeste","Folha Vitória","Folha Vitoria"),("ES","Espírito Santo","Sudeste","A Gazeta","A Gazeta ES"),("ES","Espírito Santo","Sudeste","Tribuna Online","A Tribuna ES","A Tribuna Espírito Santo"),("ES","Espírito Santo","Sudeste","ES Hoje"),("ES","Espírito Santo","Sudeste","Século Diário","Seculo Diario"),
("MG","Minas Gerais","Sudeste","Itatiaia","Rádio Itatiaia"),("MG","Minas Gerais","Sudeste","Estado de Minas","EM.com.br"),("MG","Minas Gerais","Sudeste","O Tempo"),("MG","Minas Gerais","Sudeste","Hoje em Dia"),("MG","Minas Gerais","Sudeste","BHAZ","Bhaz"),
("RJ","Rio de Janeiro","Sudeste","O Globo","oglobo"),("RJ","Rio de Janeiro","Sudeste","O Dia","O Dia RJ"),("RJ","Rio de Janeiro","Sudeste","Extra","Extra Online"),("RJ","Rio de Janeiro","Sudeste","Jornal do Brasil","JB"),("RJ","Rio de Janeiro","Sudeste","Diário do Rio","Diario do Rio"),
("SP","São Paulo","Sudeste","Folha de S.Paulo","Folha de São Paulo","Folha"),("SP","São Paulo","Sudeste","Estadão","O Estado de S. Paulo"),("SP","São Paulo","Sudeste","Valor Econômico","Valor"),("SP","São Paulo","Sudeste","Diário de S.Paulo","Diario de S.Paulo"),("SP","São Paulo","Sudeste","A Tribuna","A Tribuna de Santos","atribuna.com.br"),
("PR","Paraná","Sul","Banda B"),("PR","Paraná","Sul","aRede","Portal aRede"),("PR","Paraná","Sul","Tribuna do Paraná","Tribuna do Parana"),("PR","Paraná","Sul","Bem Paraná","Bem Parana"),("PR","Paraná","Sul","Gazeta do Povo"),
("SC","Santa Catarina","Sul","ND Mais","ND+"),("SC","Santa Catarina","Sul","NSC Total","NSC"),("SC","Santa Catarina","Sul","SCC10","SCC"),("SC","Santa Catarina","Sul","O Município","O Municipio"),("SC","Santa Catarina","Sul","Oeste Mais","OesteMais"),
("RS","Rio Grande do Sul","Sul","GZH","Zero Hora","GaúchaZH","GauchaZH"),("RS","Rio Grande do Sul","Sul","Correio do Povo"),("RS","Rio Grande do Sul","Sul","Jornal do Comércio","Jornal do Comercio RS"),("RS","Rio Grande do Sul","Sul","Sul21"),("RS","Rio Grande do Sul","Sul","O Sul","Jornal O Sul"),
)
BY_STATE = tuple(_state(*spec) for spec in _STATE_SPECS)
SPECIALIZED = (
    _special("especializada-defesatv","DefesaTV","Defesa TV","defesa.tv.br"),_special("especializada-poder-naval","Poder Naval","PoderNaval","naval.com.br"),_special("especializada-poder-aereo","Poder Aéreo","Poder Aereo","aereo.jor.br"),_special("especializada-defesa-em-foco","Defesa em Foco","defesaemfoco.com.br"),_special("especializada-gbn-news","GBN News","GBN Defense","GBNNews","gbnnews.com.br"),_special("especializada-zona-militar","Zona Militar","Zona-Militar","zona-militar.com"),_special("especializada-tecnologia-defesa","Tecnodefesa","Tecnologia & Defesa","Tecnologia e Defesa","tecnodefesa.com.br"),_special("especializada-defesa-aerea-naval","Defesa Aérea & Naval","Defesa Aérea e Naval","Defesa Aerea e Naval","DAN","defesaaereanaval.com.br"),_special("especializada-agencia-marinha","Agência Marinha de Notícias","Agência Marinha","agencia.marinha.mil.br"),_special("especializada-forcas-terrestres","Forças Terrestres","Forcas Terrestres","forte.jor.br"),_special("especializada-defesanet","DefesaNet","Defesa Net","defesanet.com.br"),_special("especializada-agencia-forca-aerea","Agência Força Aérea","Agência FAB","Agencia Forca Aerea","fab.mil.br"),
)
NEWS_SOURCES = tuple(dict((s.id,s) for s in NATIONAL + BY_STATE + SPECIALIZED).values())
# O catálogo base de vídeo (VideoSourceCatalog.kt) ainda não possui módulo equivalente no destino.
# Os dois extras Desktop já foram migrados no Passo 6 e são os únicos aqui disponíveis sem duplicar MIG pendente.
VIDEO_SOURCES = tuple(DESKTOP_VIDEO_EXTRAS)
VIDEO_CATALOG_COMPLETE = False
