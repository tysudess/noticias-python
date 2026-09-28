from monitor_noticias.ui import home_page
from monitor_noticias.ui.home_layout_v76_patch import (
    install_home_layout_v76_patch,
)


def test_v76_replaces_home_builders():
    old_schedule = home_page.HomePage._build_schedule_and_summary
    old_bottom = home_page.HomePage._build_bottom_cards

    install_home_layout_v76_patch()

    assert (
        home_page.HomePage._build_schedule_and_summary
        is not old_schedule
        or "home_layout_v76_patch"
        in home_page.HomePage._build_schedule_and_summary.__module__
    )

    assert (
        home_page.HomePage._build_bottom_cards
        is not old_bottom
        or "home_layout_v76_patch"
        in home_page.HomePage._build_bottom_cards.__module__
    )


def test_v76_does_not_build_summary_or_tips():
    install_home_layout_v76_patch()

    schedule_code = (
        home_page.HomePage
        ._build_schedule_and_summary
        .__code__
    )

    bottom_code = (
        home_page.HomePage
        ._build_bottom_cards
        .__code__
    )

    schedule_text = " ".join(
        str(item)
        for item in schedule_code.co_consts
    )

    bottom_text = " ".join(
        str(item)
        for item in bottom_code.co_consts
    )

    assert "Resumo do dia" not in schedule_text
    assert "Dicas" not in bottom_text
