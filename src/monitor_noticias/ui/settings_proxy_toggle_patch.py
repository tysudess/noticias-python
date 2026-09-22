from __future__ import annotations

from monitor_noticias.ui import settings_page as settings_page_module


_INSTALLED = False


def install_settings_proxy_toggle_patch() -> None:
    """Impede o refresh de 500 ms de desfazer a edição do Proxy Geral."""

    global _INSTALLED

    if _INSTALLED:
        return

    cls = settings_page_module.SettingsPage

    original_init = cls.__init__
    original_mark_dirty = cls._mark_dirty
    original_save_proxy = cls._save_proxy
    original_apply_auto = cls._apply_auto
    original_refresh = cls.refresh

    def patched_init(self, controller):
        original_init(self, controller)

        self._proxy_editing = False
        self._automation_dirty_separate = False

        def mark_proxy(*_args):
            if getattr(self, "_loaded", False):
                self._proxy_editing = True

        # O proxy não fazia parte da lista _dirty original.
        # Assim o refresh periódico restaurava o valor salvo até 2 vezes/s.
        self.proxy_enabled.toggled.connect(mark_proxy)
        self.host.textEdited.connect(mark_proxy)
        self.port.valueChanged.connect(mark_proxy)
        self.user.textEdited.connect(mark_proxy)
        self.password.textEdited.connect(mark_proxy)

    def patched_mark_dirty(self, *args):
        if getattr(self, "_loaded", False):
            self._automation_dirty_separate = True
        return original_mark_dirty(self, *args)

    def patched_save_proxy(self):
        auto_dirty = bool(
            getattr(
                self,
                "_automation_dirty_separate",
                False,
            )
        )

        result = original_save_proxy(self)

        self._proxy_editing = False

        # Mantém alterações de automação não salvas, se existirem.
        self._dirty = auto_dirty

        return result

    def patched_apply_auto(self):
        result = original_apply_auto(self)
        self._automation_dirty_separate = False
        return result

    def patched_refresh(self, state):
        proxy_editing = bool(
            getattr(
                self,
                "_proxy_editing",
                False,
            )
        )

        if not proxy_editing:
            return original_refresh(self, state)

        # Usa o mecanismo _dirty que a própria página já possui para impedir
        # que refresh() sobrescreva checkbox/campos enquanto o usuário edita.
        old_dirty = bool(
            getattr(
                self,
                "_dirty",
                False,
            )
        )

        self._dirty = True

        try:
            return original_refresh(self, state)
        finally:
            self._dirty = old_dirty

    cls.__init__ = patched_init
    cls._mark_dirty = patched_mark_dirty
    cls._save_proxy = patched_save_proxy
    cls._apply_auto = patched_apply_auto
    cls.refresh = patched_refresh

    _INSTALLED = True
