from __future__ import annotations

from monitor_noticias.ui.theme_engine import (
    transform_painter_color,
    transform_stylesheet,
)
from monitor_noticias.ui.theme_store import THEME_CLARO, THEME_ESCURO


def test_dark_theme_converts_qpainter_row_fills_and_ink_colors():
    assert transform_painter_color("#FFFFFF", "fill", THEME_ESCURO) == "#192D40"
    assert transform_painter_color("#EAF4FF", "fill", THEME_ESCURO) != "#EAF4FF"
    assert transform_painter_color("#08245F", "text", THEME_ESCURO) != "#08245F"
    assert transform_painter_color("#FFFFFF", "text", THEME_ESCURO) == "#FFFFFF"


def test_light_theme_leaves_qpainter_colors_unchanged():
    assert transform_painter_color("#FFFFFF", "fill", THEME_CLARO) == "#FFFFFF"
    assert transform_painter_color("#08245F", "text", THEME_CLARO) == "#08245F"


def test_dark_theme_converts_white_surfaces_used_by_remaining_pages():
    qss = """
    QFrame#demandItem { background:#FFFFFF; color:#08245F; }
    QFrame#videoItem { background:white; color:#08245F; }
    QFrame#historyTop { background:white; color:#08245F; }
    QFrame#header, QFrame#card { background:#FFFFFF; color:#08245F; }
    QListWidget { background:#FFFFFF; color:#08245F; }
    """
    result = transform_stylesheet(qss, THEME_ESCURO)
    assert "background:#FFFFFF" not in result
    assert "background:white" not in result
    assert "color:#08245F" not in result
