from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "src" / "monitor_noticias" / "ui" / "first_tabs_performance_patch.py"


def _load_patch_module():
    spec = importlib.util.spec_from_file_location("first_tabs_performance_v116", PATCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def article(link="https://news.example/a", title="A", **overrides):
    defaults = dict(
        id=1, link=link, title=title, source="Portal", date=100,
        snippet="Resumo", important=False, demand=False, matchedTerm="",
        matchedDemand="", capturedAt=200,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_news_rows_with_no_changes_are_skipped():
    patch = _load_patch_module()
    old = [article(), article("https://news.example/b", "B", id=2)]
    new = [article(), article("https://news.example/b", "B", id=2)]
    assert patch.changed_news_rows(old, set(), new, set()) == []


def test_news_row_update_emits_only_changed_indices_when_order_is_stable():
    patch = _load_patch_module()
    old = [article(), article("https://news.example/b", "B", id=2)]
    new = [article(), article("https://news.example/b", "B atualizado", id=2)]
    assert patch.changed_news_rows(old, set(), new, set()) == [1]


def test_news_structure_or_order_change_requests_model_reset():
    patch = _load_patch_module()
    old = [article(), article("https://news.example/b", "B", id=2)]
    inserted = old + [article("https://news.example/c", "C", id=3)]
    reordered = list(reversed(old))
    assert patch.changed_news_rows(old, set(), inserted, set()) is None
    assert patch.changed_news_rows(old, set(), reordered, set()) is None


def test_new_badge_change_invalidates_just_the_affected_row():
    patch = _load_patch_module()
    rows = [article(), article("https://news.example/b", "B", id=2)]
    assert patch.changed_news_rows(rows, set(), rows, {"https://news.example/b"}) == [1]


def test_video_row_signature_changes_when_new_badge_or_article_changes():
    patch = _load_patch_module()
    video = SimpleNamespace(
        id=1, link="https://video.example/a", title="Vídeo", sourceId="s1",
        sourceName="Canal", publishedAt=100, summary="", matchedTerm="termo",
        matchedDemand="", capturedAt=200,
    )
    old = patch.video_row_signature(video, False)
    assert old != patch.video_row_signature(video, True)
    video.title = "Título atualizado"
    assert old != patch.video_row_signature(video, False)


def test_demand_signature_covers_last_run_data_and_errors():
    patch = _load_patch_module()
    old = SimpleNamespace(id=3, vehicle="Marinha", subject="Exercício", active=True,
                          lastCheckedAt=100, lastFoundCount=2, lastNewCount=1, lastError="")
    new = SimpleNamespace(id=3, vehicle="Marinha", subject="Exercício", active=True,
                          lastCheckedAt=200, lastFoundCount=3, lastNewCount=1, lastError="timeout")
    assert patch.demand_row_signature(old) != patch.demand_row_signature(new)


def test_demand_progress_includes_current_source_counts_and_completion_state():
    patch = _load_patch_module()
    active = patch.demand_progress_payload(
        started_at=100, now_ms=200, completed=2, total=5, vehicle="Marinha",
        subject="Exercício", found=8, new_count=3, errors=1, active=True,
    )
    assert active["kind"] == "Demandas"
    assert active["currentSource"] == "Marinha"
    assert active["currentQuery"] == "Exercício"
    assert active["completed"] == 2 and active["total"] == 5
    assert active["found"] == 8 and active["newCount"] == 3 and active["errors"] == 1
    assert active["finishedAt"] == 0

    done = patch.demand_progress_payload(
        started_at=100, now_ms=250, completed=5, total=5, found=17,
        new_count=4, errors=2, active=False,
    )
    assert done["active"] is False and done["finishedAt"] == 250
    assert done["completed"] == done["total"] == 5


def test_composition_installs_stage_two_after_v115_functional_patch():
    composition = (ROOT / "src" / "monitor_noticias" / "app" / "composition.py").read_text(encoding="utf-8")
    assert "install_first_tabs_functional_patch()" in composition
    assert "install_first_tabs_performance_patch()" in composition
    assert composition.index("install_first_tabs_functional_patch()") < composition.index("install_first_tabs_performance_patch()")


def test_performance_patch_uses_cached_signatures_and_incremental_demand_progress():
    source = PATCH_PATH.read_text(encoding="utf-8")
    for fragment in (
        "self._v116_video_list_signature",
        "self._v116_demand_list_signature",
        "NewsRepository.search_all_demands = repository_search_all_demands",
        "AutomationService._run_demands = service_run_demands",
        "self.state.news = self.news_db.listPeriod(start, end, 1000)",
    ):
        assert fragment in source


def test_demand_sweep_result_supports_items_and_new_links_without_breaking_old_calls():
    path = ROOT / "src" / "monitor_noticias" / "automation" / "models.py"
    spec = importlib.util.spec_from_file_location("models_v116_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    legacy = module.DemandSweepResult(2, 7, 3, 1)
    assert legacy.items == () and legacy.newLinks == ()

    full = module.DemandSweepResult(2, 7, 3, 1, ("article",), ("https://news.example/a",))
    assert full.items == ("article",)
    assert full.newLinks == ("https://news.example/a",)
