from __future__ import annotations

from monitor_noticias.ui.theme_engine import transform_stylesheet
from monitor_noticias.ui.theme_store import THEME_CLARO, THEME_ESCURO


def test_dark_theme_recolors_page_background_cards_and_text():
    qss = """
    QWidget#root { background:#F4F9FF; color:#08245F; }
    QFrame#homeCard { background:#FFFFFF; border:1px solid #D6E6F7; }
    QLabel#metricTitle { color:#173E75; }
    """
    result = transform_stylesheet(qss, THEME_ESCURO)
    assert "background:#0D1926" in result
    assert "background:#152637" in result
    assert "border:1px solid #364A5D" in result
    assert "color:#08245F" not in result


def test_light_theme_recolors_entire_sidebar_and_keeps_active_state():
    qss = """
    QFrame#sidebar { background:#071D31; border-right:1px solid #173750; }
    QFrame#sidebarNavItem[active="true"] { background:#123B58; }
    QLabel#sidebarBrandTitle { color:#F4F7FA; }
    """
    result = transform_stylesheet(qss, THEME_CLARO)
    assert "background:#F3F6FA" in result
    assert "background:#E2ECF4" in result
    assert "border-right:1px solid #CAD7E2" in result
    assert "color:#1D3548" in result


def test_light_theme_preserves_white_text_on_colored_action_buttons():
    qss = "QPushButton#save { background:#0A7DF8; color:#FFFFFF; border:1px solid #CFE0F5; }"
    result = transform_stylesheet(qss, THEME_CLARO)
    assert "background:#0A7DF8" in result
    assert "color:#FFFFFF" in result


def test_dark_theme_converts_pastel_status_cards_to_muted_dark_surfaces():
    qss = "QLabel#status { background:#EAF9F2; color:#078B5F; border:1px solid #C4ECD9; }"
    result = transform_stylesheet(qss, THEME_ESCURO)
    assert "background:#" in result and "background:#EAF9F2" not in result
    assert "color:#078B5F" not in result


def test_theme_samples_and_media_previews_keep_their_original_colors():
    sample = 'QPushButton#themeChoice[themeId="escuro"] { background:#0B2B45; color:#F4F7FA; }'
    preview = "QLabel#pdfPreview { background:#FFFFFF; color:#000000; }"
    assert transform_stylesheet(sample, THEME_CLARO) == sample
    assert transform_stylesheet(preview, THEME_ESCURO, "pdfPreview") == preview
