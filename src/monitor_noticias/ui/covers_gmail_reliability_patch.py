from __future__ import annotations

from monitor_noticias.capas_tool.app.config import GMAIL_PAPERS
from monitor_noticias.capas_tool.app.paper_names import normalize_matters_payload


_INSTALLED = False


def install_covers_gmail_reliability_patch(covers_ui) -> None:
    """Corrige associação de nomes e expõe o diagnóstico real da busca Gmail.

    A instalação ocorre antes da criação da janela interna de Capas.
    """
    global _INSTALLED

    if _INSTALLED or getattr(covers_ui.MainWindow, "_covers_gmail_reliability_installed", False):
        _INSTALLED = True
        return

    main_window_cls = covers_ui.MainWindow

    original_refresh = main_window_cls.refresh_all
    original_feed_ready = main_window_cls._feed_ready
    original_feed_error = main_window_cls._feed_error
    original_finish_gmail = main_window_cls._finish_gmail_branch
    original_finalize = main_window_cls._finalize_refresh

    def refresh_all(self):
        self._covers_gmail_report = {}
        self._covers_gmail_feed_error = ""
        original_refresh(self)

    def feed_ready(self, result, generation):
        if generation != self.refresh_generation:
            return original_feed_ready(self, result, generation)

        matters, meta = result
        mapped, unknown, aliases = normalize_matters_payload(matters)
        self._covers_gmail_report = {
            "raw_names": list((matters or {}).keys()) if isinstance(matters, dict) else [],
            "unknown_names": list(unknown.keys()),
            "aliases": list(dict.fromkeys(aliases)),
            "paper_count": len(mapped),
            "link_count": sum(len(urls) for urls in mapped.values()),
            "meta": dict(meta or {}) if isinstance(meta, dict) else {},
        }
        # Tanto a busca direta quanto a alternativa via Chromium chegam aqui.
        # A partir deste ponto, os nomes usados pelo restante da UI são canônicos.
        return original_feed_ready(self, (mapped, meta), generation)

    def feed_error(self, message, generation):
        if generation == self.refresh_generation:
            self._covers_gmail_feed_error = str(message or "Falha sem descrição")
        return original_feed_error(self, message, generation)

    def finish_gmail_branch(self, generation):
        result = original_finish_gmail(self, generation)
        if generation != self.refresh_generation:
            return result

        # O resolver já inclui erro por posição; a versão anterior não o mostrava
        # no cartão do jornal. Agora cada falha fica visível junto do respectivo jornal.
        for entry in getattr(self, "entries", []):
            if entry.name not in GMAIL_PAPERS or not entry.candidates:
                continue
            failures = [
                candidate
                for candidate in entry.candidates
                if not getattr(candidate, "available", False)
            ]
            if not failures:
                continue
            detail = []
            for candidate in failures[:3]:
                page_number = getattr(candidate, "page_number", "?")
                error = str(getattr(candidate, "error", "") or "imagem não aberta").strip()
                detail.append(f"pág. {page_number}: {error[:110]}")
            suffix = " • falha(s): " + " | ".join(detail)
            if len(failures) > 3:
                suffix += f" | +{len(failures) - 3} outra(s)"
            entry.status = str(entry.status or "") + suffix

        self._refresh_list()
        if getattr(self, "current_entry", None) is not None:
            self._show_entry()
        return result

    def finalize_refresh(self, generation=None):
        result = original_finalize(self, generation)
        if generation is not None and generation != self.refresh_generation:
            return result

        report = getattr(self, "_covers_gmail_report", {}) or {}
        feed_error = getattr(self, "_covers_gmail_feed_error", "")
        if feed_error:
            self.set_status(f"Atualização concluída • diagnóstico Gmail: {feed_error[:240]}")
            return result

        if not report:
            return result

        meta = report.get("meta", {})
        pieces = [
            f"Gmail: {report.get('link_count', 0)} link(s) em {report.get('paper_count', 0)} jornal(is)"
        ]
        if report.get("aliases"):
            labels = ", ".join(report["aliases"][:4])
            pieces.append(f"nomes normalizados: {labels}")
        unknown = report.get("unknown_names") or []
        if unknown:
            pieces.append("nomes sem correspondência: " + ", ".join(unknown[:4]))
        elif report.get("link_count", 0) == 0:
            pieces.append(
                "ponte não retornou links compatíveis; confira assunto/data no Apps Script"
            )

        if isinstance(meta, dict):
            counters = []
            for field, label in (
                ("threads", "conversas"),
                ("messagesScanned", "mensagens lidas"),
                ("rawLeiaMaisFound", "Leia mais encontrados"),
                ("datedItemsMatched", "itens na data"),
            ):
                if field in meta:
                    counters.append(f"{label}: {meta.get(field)}")
            if counters:
                pieces.append(" / ".join(counters))

        self.set_status("Atualização concluída • " + " • ".join(pieces)[:700])
        return result

    main_window_cls.refresh_all = refresh_all
    main_window_cls._feed_ready = feed_ready
    main_window_cls._feed_error = feed_error
    main_window_cls._finish_gmail_branch = finish_gmail_branch
    main_window_cls._finalize_refresh = finalize_refresh
    main_window_cls._covers_gmail_reliability_installed = True
    _INSTALLED = True
