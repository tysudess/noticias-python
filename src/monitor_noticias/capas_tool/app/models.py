from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

@dataclass
class CandidatePage:
    path: Optional[Path]
    score: int = 0
    confidence: int = 0
    recognized_text: str = ""
    source_url: str = ""
    page_number: int = 1
    available: bool = True
    error: str = ""
    pdf_path: Optional[Path] = None
    source_filename: str = ""

@dataclass
class CoverEntry:
    name: str
    mastheads: List[str]
    pdf_margin_percent: int = 2
    selected: bool = True
    status: str = "Aguardando"
    candidates: List[CandidatePage] = field(default_factory=list)
    chosen_index: int = -1
    manual_path: Optional[Path] = None
    automatic_index: int = -1
    automatic_status: str = ""
    review_index: int = -1

    @property
    def current_path(self) -> Optional[Path]:
        if self.manual_path and self.manual_path.exists():
            return self.manual_path
        if 0 <= self.chosen_index < len(self.candidates):
            c = self.candidates[self.chosen_index]
            p = c.path
            return p if c.available and p and p.exists() else None
        return None

    @property
    def is_manual(self) -> bool:
        return bool(self.manual_path)

    def choose(self, index: int):
        if 0 <= index < len(self.candidates) and self.candidates[index].available:
            self.chosen_index = index
            self.review_index = index
            self.manual_path = None

    def set_manual(self, path: Path):
        self.automatic_index = self.chosen_index
        self.automatic_status = self.status
        self.manual_path = path
        self.status = "Capa inserida manualmente"

    def restore_automatic(self):
        self.manual_path = None
        if 0 <= self.automatic_index < len(self.candidates):
            self.chosen_index = self.automatic_index
            self.review_index = self.automatic_index
        if self.automatic_status:
            self.status = self.automatic_status
