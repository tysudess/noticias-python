from __future__ import annotations

from monitor_noticias.ui import pdf_export_quality_fix as fix


def test_raster_page_uses_cover_width_and_preserves_aspect():
    previous = fix._EXPORT_TARGET_WIDTH_PT

    try:
        fix._EXPORT_TARGET_WIDTH_PT = 298.8

        page = fix._page_for_pixels(
            1240,
            1960,
            300.0,
            300.0,
        )

        assert round(float(page.mediabox.width), 3) == 298.8

        expected_height = 298.8 * 1960 / 1240

        assert (
            round(float(page.mediabox.height), 3)
            == round(expected_height, 3)
        )

    finally:
        fix._EXPORT_TARGET_WIDTH_PT = previous


def test_folha_example_expected_width():
    cover_width = 298.8
    source_width = 561.6
    source_height = 888.48

    final_height = (
        cover_width
        * source_height
        / source_width
    )

    assert round(final_height, 3) == 472.717
