from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "src" / "monitor_noticias" / "ui" / "first_tabs_visual_patch.py"


def load_patch():
    spec = importlib.util.spec_from_file_location("first_tabs_visual_v117", PATCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_responsive_news_actions_keep_full_width_on_desktop_and_contract_on_small_windows():
    patch = load_patch()
    assert patch.responsive_news_button_width(1400) == 112
    assert patch.responsive_news_button_width(900) == 112
    assert patch.responsive_news_button_width(700) == 100
    assert patch.responsive_news_button_width(600) == 85
    assert patch.responsive_news_button_width(500) == 78


def test_execution_visual_state_distinguishes_running_complete_partial_failure_and_cancel():
    patch = load_patch()
    assert patch._execution_state("Buscando notícias...", True) == "running"
    assert patch._execution_state("✓ 14 resultados • 0 falhas", False) == "completed"
    assert patch._execution_state("✓ 14 resultados • 2 falhas", False) == "partial"
    progress = type("Progress", (), {"errors": 2})()
    assert patch._execution_state("Pronto", False, progress) == "partial"
    assert patch._execution_state("Falha na busca: timeout", False) == "failure"
    assert patch._execution_state("Busca interrompida pelo usuário", False) == "cancelled"
    assert patch._execution_state("Pronto", False) == "idle"


def test_common_styles_define_shared_controls_cards_progress_and_status_palette():
    patch = load_patch()
    css = patch.COMMON_FIRST_TABS_QSS
    for fragment in (
        "QLineEdit:focus",
        "QPushButton#newsPrimary",
        "QFrame#metricCard",
        "QFrame#videoItem",
        "QFrame#demandItem",
        "QProgressBar#newsProgress::chunk",
        'QLabel[executionState="running"]',
        'QLabel[executionState="failure"]',
    ):
        assert fragment in css


def test_visual_patch_keeps_existing_page_classes_and_responsive_delegate_hook():
    patch = load_patch()
    source = PATCH_PATH.read_text(encoding="utf-8")
    assert "wrap_init(HomePage, \"home\")" in source
    assert "wrap_init(NewsPage, \"news\")" in source
    assert "wrap_init(VideosPage, \"videos\")" in source
    assert "wrap_init(DemandsPage, \"demands\")" in source
    assert "NewsDelegate._buttons = responsive_buttons" in source
    assert callable(patch.install_first_tabs_visual_patch)


def test_composition_installs_visual_layer_after_functional_and_performance_stages():
    source = (ROOT / "src" / "monitor_noticias" / "app" / "composition.py").read_text(encoding="utf-8")
    assert "install_first_tabs_functional_patch()" in source
    assert "install_first_tabs_performance_patch()" in source
    assert "install_first_tabs_visual_patch()" in source
    assert source.index("install_first_tabs_functional_patch()") < source.index("install_first_tabs_performance_patch()") < source.index("install_first_tabs_visual_patch()")
