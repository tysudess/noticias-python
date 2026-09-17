from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class SectionSpec:
    label: str
    subtitle: str
    icon: str


class Section(Enum):
    HOME = SectionSpec("Início", "Acompanhe notícias, vídeos, demandas e fontes em tempo real.", "⌂")
    NEWS = SectionSpec("Notícias", "Busca e acompanhamento de matérias com atualização contínua", "▤")
    VIDEOS = SectionSpec("Vídeos", "Busca e acompanhamento de vídeos relevantes", "▶")
    DEMANDS = SectionSpec("Demandas", "Assuntos prioritários acompanhados por veículo", "☑")
    SOURCES = SectionSpec("Fontes", "Fontes nacionais, regionais e mídias especializadas", "▣")
    HISTORY = SectionSpec("Histórico", "Histórico local das buscas e resultados", "↺")
    TERMS = SectionSpec("Termos", "Termos independentes para notícias e vídeos", "⌕")
    STOP = SectionSpec("Parar buscas", "Interrompa buscas manuais em andamento", "■")
    SETTINGS = SectionSpec("Configurações", "Automação, proxy, inicialização e operação do aplicativo", "⚙")
    PDF_EDITOR = SectionSpec("Editor de PDF", "Monte, reorganize, recorte e exporte PDFs e imagens", "PDF")
    EXTRACTOR = SectionSpec("Extrator de Vídeos", "Baixe vídeos com o fluxo direto v3.0.1", "⇩")
    VIDEO_EDITOR = SectionSpec("Editor de Vídeo", "Abra o editor nativo PySide6/QtMultimedia", "▰")


SECTION_ORDER = tuple(Section)
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
TOOL_SECTIONS = {Section.PDF_EDITOR, Section.EXTRACTOR, Section.VIDEO_EDITOR}
