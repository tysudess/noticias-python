from __future__ import annotations

from monitor_noticias.ui.demands_page import (
    DemandsPage,
)
from monitor_noticias.ui.sections import (
    Section,
)


def install_demands_news_actions(
    window,
) -> None:
    """Liga o botão Extrair matéria da aba Demanda ao extrator do Central.

    Abrir matéria, WhatsApp e Copiar link já são tratados diretamente pelo
    NewsDelegate reutilizado da aba Notícias.
    """

    page = (
        window.pages.get(
            Section.DEMANDS
        )
    )

    if not isinstance(
        page,
        DemandsPage,
    ):
        return

    if getattr(
        page,
        "_demand_news_actions_connected",
        False,
    ):
        return

    page.extract_requested.connect(
        window._open_news_extractor_link
    )

    page._demand_news_actions_connected = (
        True
    )
