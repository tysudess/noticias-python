from __future__ import annotations

from monitor_noticias.ui.sections import (
    Section,
)


_INSTALLED = False


def install_removed_integrations_guard(
    main_window_class,
) -> None:
    """Retira Planilhas do menu e bloqueia navegação para a integração.

    A classe MainWindow ainda contém referências legadas ao módulo de
    Planilhas para preservar compatibilidade/rollback. Este patch é instalado
    ANTES de criar a janela e garante que a integração não apareça no Central.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    original_sidebar_order = (
        main_window_class
        ._sidebar_navigation_order
    )

    original_navigate = (
        main_window_class.navigate
    )

    original_global_search = (
        main_window_class
        ._run_global_search
    )

    def sidebar_order_without_removed(
        self,
    ):
        return tuple(
            section
            for section
            in original_sidebar_order(
                self
            )
            if section
            is not Section.SPREADSHEETS
        )

    def navigate_without_removed(
        self,
        section,
    ):
        if section is Section.SPREADSHEETS:
            section = Section.NEWS

        return original_navigate(
            self,
            section,
        )

    def global_search_without_removed(
        self,
    ) -> None:
        text = (
            self.global_search
            .text()
            .strip()
        )

        if not text:
            self.controller.search_news()
            return

        lowered = text.lower()

        if (
            "video" in lowered
            or "vídeo" in lowered
        ):
            self.navigate(
                Section.VIDEOS
            )

        elif "demanda" in lowered:
            self.navigate(
                Section.DEMANDS
            )

        elif "fonte" in lowered:
            self.navigate(
                Section.SOURCES
            )

        # WhatsApp/Planilhas não possuem mais uma seção própria.
        # A busca segue como busca normal de notícias.
        else:
            self.navigate(
                Section.NEWS
            )

            page = self.pages.get(
                Section.NEWS
            )

            if hasattr(
                page,
                "query",
            ):
                page.query.setText(
                    text
                )

    main_window_class._sidebar_navigation_order = (
        sidebar_order_without_removed
    )

    main_window_class.navigate = (
        navigate_without_removed
    )

    main_window_class._run_global_search = (
        global_search_without_removed
    )

    _INSTALLED = True


def remove_legacy_pages(
    window,
) -> None:
    """Descarta a página legada de Planilhas após criar o MainWindow."""

    page = window.pages.pop(
        Section.SPREADSHEETS,
        None,
    )

    if page is None:
        return

    try:
        shutdown = getattr(
            page,
            "shutdown",
            None,
        )
        if callable(shutdown):
            shutdown()
    except Exception:
        pass

    try:
        page.hide()
        page.setParent(None)
        page.deleteLater()
    except Exception:
        pass
