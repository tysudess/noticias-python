from __future__ import annotations

from monitor_noticias.ui import settings_page as settings_page_module


_INSTALLED = False


def install_settings_credentials_patch() -> None:
    """Mostra erro de cofre seguro sem derrubar a interface."""

    global _INSTALLED

    if _INSTALLED:
        return

    cls = settings_page_module.SettingsPage
    original_save = cls._save_proxy

    def patched_save_proxy(self):
        try:
            return original_save(self)
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__

            self.proxy_message.setText(
                "⚠  Não foi possível salvar a senha do Proxy Geral "
                "no cofre seguro do sistema. "
                f"{message}"
            )
            return None

    cls._save_proxy = patched_save_proxy
    _INSTALLED = True
