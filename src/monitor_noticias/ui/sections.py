from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import sys


@dataclass(frozen=True, slots=True)
class SectionSpec:
    label: str
    subtitle: str
    icon: str


class Section(Enum):
    HOME = SectionSpec(
        "Início",
        "Acompanhe notícias, vídeos, demandas e fontes em tempo real.",
        "⌂",
    )
    NEWS = SectionSpec(
        "Notícias",
        "Busca e acompanhamento de matérias com atualização contínua",
        "▤",
    )
    VIDEOS = SectionSpec(
        "Vídeos",
        "Busca e acompanhamento de vídeos relevantes",
        "▶",
    )
    DEMANDS = SectionSpec(
        "Demandas",
        "Assuntos prioritários acompanhados por veículo",
        "☑",
    )
    SOURCES = SectionSpec(
        "Fontes",
        "Fontes nacionais, regionais e mídias especializadas",
        "▣",
    )
    HISTORY = SectionSpec(
        "Histórico",
        "Histórico local das buscas e resultados",
        "↺",
    )
    TERMS = SectionSpec(
        "Termos",
        "Termos independentes para notícias e vídeos",
        "⌕",
    )
    STOP = SectionSpec(
        "Parar buscas",
        "Interrompa buscas manuais em andamento",
        "■",
    )
    NEWS_EXTRACTOR = SectionSpec(
        "Extrator de Notícias",
        "Extraia e revise matérias a partir do link do veículo",
        "⇲",
    )
    COVERS = SectionSpec(
        "Capas",
        "Principais capas de jornais com revisão e exportação em PDF",
        "▧",
    )
    PDF_EDITOR = SectionSpec(
        "Editor de PDF",
        "Monte, reorganize, recorte e exporte PDFs e imagens",
        "PDF",
    )
    EXTRACTOR = SectionSpec(
        "Extrator de Vídeos",
        "Baixe vídeos com o fluxo direto v3.0.1",
        "⇩",
    )
    VIDEO_EDITOR = SectionSpec(
        "Editor de Vídeo",
        "Editor de vídeo incorporado ao Monitor",
        "▰",
    )
    SETTINGS = SectionSpec(
        "Configurações",
        "Automação, proxy, inicialização e operação do aplicativo",
        "⚙",
    )


_ALL_SECTION_ORDER = (
    Section.HOME,
    Section.NEWS,
    Section.VIDEOS,
    Section.DEMANDS,
    Section.SOURCES,
    Section.HISTORY,
    Section.TERMS,
    Section.STOP,
    Section.NEWS_EXTRACTOR,
    Section.COVERS,
    Section.PDF_EDITOR,
    Section.EXTRACTOR,
    Section.VIDEO_EDITOR,
    Section.SETTINGS,
)

# Ubuntu/Linux: a aba Capas fica fora da navegação e do QStackedWidget.
# O Windows mantém a ordem original, inclusive Section.COVERS.
# Isso evita que a página de Capas seja ativada no Linux e elimina o caminho
# que vinha encerrando a Central ao clicar em "Atualizar Capas".
SECTION_ORDER = tuple(
    section
    for section in _ALL_SECTION_ORDER
    if not (
        sys.platform.startswith("linux")
        and section is Section.COVERS
    )
)

CORE_SECTIONS = {
    Section.HOME,
    Section.NEWS,
    Section.VIDEOS,
    Section.DEMANDS,
    Section.SOURCES,
    Section.HISTORY,
    Section.TERMS,
    Section.STOP,
    Section.SETTINGS,
}

TOOL_SECTIONS = {
    Section.NEWS_EXTRACTOR,
    Section.COVERS,
    Section.PDF_EDITOR,
    Section.EXTRACTOR,
    Section.VIDEO_EDITOR,
}

if sys.platform.startswith("linux"):
    TOOL_SECTIONS.discard(Section.COVERS)
