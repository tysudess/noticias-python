from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class WindowsTrayNotifier:
    """Adaptador do callback do AutomationService para o tray Qt."""

    def __init__(self, tray_icon: Any) -> None:
        self.tray_icon = tray_icon

    def __call__(self, title: str, message: str) -> None:
        try:
            visible_title = str(title or "").strip()
            if visible_title.casefold() in {
                "monitor de notícias".casefold(),
                "monitor de noticias".casefold(),
            }:
                visible_title = "Central Inteligente de Mídia"

            self.tray_icon.showMessage(
                visible_title or "Central Inteligente de Mídia",
                message,
            )
        except Exception:
            log.exception(
                "Falha ao enviar notificação Windows pelo tray."
            )
