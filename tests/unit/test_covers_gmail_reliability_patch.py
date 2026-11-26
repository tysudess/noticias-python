from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_covers_page_installs_gmail_reliability_patch_before_creating_window():
    source = _read("src/monitor_noticias/ui/covers_page.py")
    install = source.index("install_covers_gmail_reliability_patch(covers_ui)")
    create = source.index("window = CoversWindow()")
    assert install < create


def test_patch_normalizes_feed_before_original_gmail_matching():
    source = _read("src/monitor_noticias/ui/covers_gmail_reliability_patch.py")
    assert "normalize_matters_payload(matters)" in source
    assert "original_feed_ready(self, (mapped, meta), generation)" in source


def test_patch_reports_unknown_names_and_apps_script_counters():
    source = _read("src/monitor_noticias/ui/covers_gmail_reliability_patch.py")
    for field in ("threads", "messagesScanned", "rawLeiaMaisFound", "datedItemsMatched"):
        assert f'("{field}"' in source
    assert "nomes sem correspondência" in source


def test_patch_surfaces_the_actual_failed_page_diagnostics():
    source = _read("src/monitor_noticias/ui/covers_gmail_reliability_patch.py")
    assert 'getattr(candidate, "error", "")' in source
    assert "falha(s):" in source
    assert "original_finish_gmail(self, generation)" in source


def test_patch_is_idempotent_and_does_not_touch_build_workflows_or_art_studio():
    source = _read("src/monitor_noticias/ui/covers_gmail_reliability_patch.py")
    assert "_covers_gmail_reliability_installed" in source
    assert "workflow" not in source.lower()
    assert "art_studio" not in source.lower()
