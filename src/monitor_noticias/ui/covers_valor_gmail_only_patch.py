from __future__ import annotations

from monitor_noticias.capas_tool.app import ui as covers_ui


_INSTALLED = False


def install_valor_gmail_only_patch() -> None:
    """V43 — Valor Econômico deve vir exclusivamente do Gmail."""

    global _INSTALLED

    if _INSTALLED:
        return

    main_window_cls = covers_ui.MainWindow

    def valor_email_ready(
        self,
        entry,
        candidates,
        generation,
        one_done,
    ):
        if generation != self.refresh_generation:
            return

        candidates = list(candidates or [])

        page1_indexes = [
            index
            for index, candidate in enumerate(candidates)
            if (
                candidate.page_number == 1
                and candidate.available
                and candidate.path
                and candidate.path.exists()
            )
        ]

        if not page1_indexes:
            entry.candidates = candidates
            entry.chosen_index = -1
            entry.review_index = 0 if candidates else -1
            entry.automatic_index = -1

            entry.status = (
                "Valor: Gmail consultado, mas a Página 1 "
                "não está disponível • FrontPages desativado "
                "para o Valor"
            )
            entry.automatic_status = entry.status

            self._refresh_list()

            if self.current_entry is entry:
                self._show_entry()

            one_done()
            return

        entry.candidates = candidates
        index = page1_indexes[0]

        entry.chosen_index = index
        entry.review_index = index
        entry.automatic_index = index

        available = sum(
            1
            for candidate in candidates
            if (
                candidate.available
                and candidate.path
                and candidate.path.exists()
            )
        )
        total = len(candidates)

        entry.automatic_status = (
            "Gmail • "
            f"{available}/{total} PDF(s) do Valor recebido(s) "
            "• Página 1 selecionada "
            "• fonte obrigatória: Gmail"
        )
        entry.status = entry.automatic_status

        self._refresh_list()

        if self.current_entry is entry:
            self._show_entry()

        one_done()

    def valor_email_error(
        self,
        entry,
        message,
        generation,
        one_done,
    ):
        if generation != self.refresh_generation:
            return

        text = str(message or "erro desconhecido")

        entry.candidates = []
        entry.chosen_index = -1
        entry.review_index = -1
        entry.automatic_index = -1

        entry.status = (
            "Valor: não foi possível obter a capa pelo Gmail • "
            f"{text} • FrontPages desativado para o Valor"
        )
        entry.automatic_status = entry.status

        self._refresh_list()

        if self.current_entry is entry:
            self._show_entry()

        # Gmail é obrigatório: não chama fallback web.
        one_done()

    main_window_cls._valor_email_ready = valor_email_ready
    main_window_cls._valor_email_error = valor_email_error

    _INSTALLED = True
