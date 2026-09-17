from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class WindowsTrayNotifier:
    """Adaptador do callback do AutomationService para o tray Qt.

    A baseline Compose envia apenas título e mensagem, sem ação de clique,
    duração ou ícone explícitos. Este adaptador não acrescenta esses campos.
    """

    def __init__(self, tray_icon: Any) -> None:
        self.tray_icon = tray_icon

    def __call__(self, title: str, message: str) -> None:
        try:
            self.tray_icon.showMessage(title, message)
        except Exception:
            log.exception("Falha ao enviar notificação Windows pelo tray.")
