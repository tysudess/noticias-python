from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "monitor_noticias" / "ui" / "news_page.py"


def _source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_news_page_has_recent_and_new_modes():
    text = _source()

    assert "QComboBox" in text
    assert 'self.sort_mode.addItem("Mais recentes", self.SORT_RECENT)' in text
    assert 'self.sort_mode.addItem("Novas", self.SORT_NEW)' in text
    assert "self.sort_mode.currentIndexChanged.connect" in text


def test_new_mode_uses_current_search_new_links_only():
    text = _source()

    start = text.index("    def _rows(self, state: UiState):")
    end = text.index("\n    def refresh(self, state: UiState) -> None:", start)
    block = text[start:end]

    assert 'getattr(state, "new_news_links", ())' in block
    assert "show_new_only = self._sort_mode() == self.SORT_NEW" in block
    assert "news.link in new_links" in block


def test_both_modes_keep_newest_date_first():
    text = _source()

    start = text.index("    def _rows(self, state: UiState):")
    end = text.index("\n    def refresh(self, state: UiState) -> None:", start)
    block = text[start:end]

    assert 'key=lambda news: getattr(news, "date", 0)' in block
    assert "reverse=True" in block
