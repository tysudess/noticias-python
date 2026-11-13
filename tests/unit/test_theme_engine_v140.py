from __future__ import annotations

from monitor_noticias.ui.theme_engine import (
    THEME_AWARE_DELEGATE_NAMES,
    transform_painter_color,
    transform_stylesheet,
)
from monitor_noticias.ui.theme_store import THEME_CLARO, THEME_ESCURO


def test_source_delegate_is_wrapped_by_the_global_theme_adapter():
    assert "SourceDelegate" in THEME_AWARE_DELEGATE_NAMES
    assert "NewsDelegate" in THEME_AWARE_DELEGATE_NAMES
    assert "HistoryDelegate" in THEME_AWARE_DELEGATE_NAMES


def test_sources_qpainter_cards_use_dark_surfaces_and_readable_text():
    assert transform_painter_color("#FFFFFF", "fill", THEME_ESCURO) == "#192D40"
    assert transform_painter_color("#08245F", "text", THEME_ESCURO) != "#08245F"
    assert transform_painter_color("#6079A5", "text", THEME_ESCURO) != "#6079A5"


def test_home_and_sources_stylesheets_do_not_retain_white_panels_in_dark_mode():
    qss = """
    QFrame#metricCard { background:#FFFFFF; color:#173E75; }
    QFrame#heroCard, QFrame#homeCard { background:#FFFFFF; color:#08245F; }
    QFrame#sourcesTop, QFrame#sourcesControl { background:#FFFFFF; color:#08245F; }
    QFrame#sourceStateCard { background:#ECFBF4; color:#08795A; }
    QPushButton#sourceSecondary { background:white; color:#123B73; }
    """
    result = transform_stylesheet(qss, THEME_ESCURO)
    assert "background:#FFFFFF" not in result
    assert "background:white" not in result
    assert "color:#08245F" not in result
    assert "color:#123B73" not in result


def test_claro_keeps_the_original_white_surfaces():
    qss = "QFrame#sourcesTop { background:#FFFFFF; color:#08245F; }"
    assert transform_stylesheet(qss, THEME_CLARO) == qss
    assert transform_painter_color("#FFFFFF", "fill", THEME_CLARO) == "#FFFFFF"
