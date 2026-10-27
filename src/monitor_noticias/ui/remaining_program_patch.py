from __future__ import annotations

import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit

from monitor_noticias.ui.controller import MainUiController
from monitor_noticias.ui.login_dialog import LoginDialog
from monitor_noticias.ui.source_page import SourcesPage
from monitor_noticias.ui.settings_page import SettingsPage
from monitor_noticias.ui.video_editor_reference_page import (
    ReferenceAdvancedVideoEditorWidget,
)


_INSTALLED = False


_TRANSIENT_AUTH_CODES = frozenset(
    {
        "NETWORK_ERROR",
        "NETWORK_TIMEOUT",
        "PROXY_ERROR",
        "PROXY_NOT_READY",
        "PROXY_AUTH_REQUIRED",
        "TLS_ERROR",
        "AUTH_UPSTREAM_ERROR",
    }
)


def should_preserve_login_password(code: str) -> bool:
    """Preserva o texto só quando falhou o transporte, não a autenticação."""
    return str(code or "").strip().upper() in _TRANSIENT_AUTH_CODES


def _install_login_password_visibility() -> None:
    original_init = LoginDialog.__init__

    if getattr(original_init, "_central_v118_password_visibility", False):
        return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        if getattr(self, "_central_v118_password_visibility_ready", False):
            return

        self.show_password = QCheckBox("Mostrar senha", self)
        self.show_password.setObjectName("loginShowPassword")
        self.show_password.setToolTip(
            "Mostra a senha somente enquanto esta opção estiver marcada."
        )
        self.show_password.setAccessibleName("Mostrar ou ocultar senha")
        self.show_password.setChecked(False)

        def toggle_password(visible: bool) -> None:
            self.password.setEchoMode(
                QLineEdit.EchoMode.Normal
                if visible
                else QLineEdit.EchoMode.Password
            )
            self.show_password.setText(
                "Ocultar senha" if visible else "Mostrar senha"
            )

        self.show_password.toggled.connect(toggle_password)

        # A senha é adicionada logo abaixo do campo já existente, antes da
        # opção de manter a sessão. Não substitui nem recria o formulário.
        password_layout = self.password.parentWidget().layout()
        password_index = password_layout.indexOf(self.password)
        if password_index >= 0:
            password_layout.insertWidget(
                password_index + 1,
                self.show_password,
            )
        else:
            password_layout.addWidget(self.show_password)

        # Reserva espaço para o novo controle sem alterar a largura do login.
        self.setFixedSize(self.width(), self.height() + 40)
        self._central_v118_password_visibility_ready = True

    patched_init._central_v118_password_visibility = True
    LoginDialog.__init__ = patched_init

    original_auth_failed = LoginDialog._auth_failed

    if not getattr(
        original_auth_failed,
        "_central_v118_preserve_network_password",
        False,
    ):
        def patched_auth_failed(self, code: str, message: str) -> None:
            typed_password = self.password.text()
            keep_password = should_preserve_login_password(code)

            # Volta ao modo oculto em qualquer falha, mesmo se o usuário
            # tiver habilitado a visualização para conferir a digitação.
            show_password = getattr(self, "show_password", None)
            if show_password is not None:
                show_password.setChecked(False)

            original_auth_failed(self, code, message)

            # Erros de senha/conta continuam limpando o campo como antes.
            # Falhas transitórias de rede não obrigam o usuário a redigitar.
            if keep_password and typed_password:
                self.password.setText(typed_password)
                self.password.setCursorPosition(len(typed_password))
                self.password.setFocus(Qt.FocusReason.OtherFocusReason)

        patched_auth_failed._central_v118_preserve_network_password = True
        LoginDialog._auth_failed = patched_auth_failed


def _install_settings_password_visibility() -> None:
    original_init = SettingsPage.__init__

    if getattr(original_init, "_central_v118_settings_password", False):
        return

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        if not hasattr(self, "password") or getattr(
            self,
            "_central_v118_settings_password_ready",
            False,
        ):
            return

        self.show_proxy_password = QCheckBox(
            "Mostrar senha do proxy",
            self.proxy_frame,
        )
        self.show_proxy_password.setObjectName(
            "settingsShowProxyPassword"
        )
        self.show_proxy_password.setToolTip(
            "A senha fica visível somente enquanto esta opção estiver marcada."
        )
        self.show_proxy_password.setChecked(False)
        self.show_proxy_password.toggled.connect(
            lambda visible: self.password.setEchoMode(
                QLineEdit.EchoMode.Normal
                if visible
                else QLineEdit.EchoMode.Password
            )
        )

        proxy_layout = self.proxy_frame.layout()
        # Cabeçalho (0), campos (1), botões (2), mensagem (3).
        # Colocamos o seletor entre os campos e os botões existentes.
        proxy_layout.insertWidget(2, self.show_proxy_password)

        if sys.platform.startswith("linux"):
            for label in self.findChildren(QLabel):
                if label.text().strip() == "Iniciar com o Windows":
                    label.setText("Iniciar com o sistema")

        self._central_v118_settings_password_ready = True

    patched_init._central_v118_settings_password = True
    SettingsPage.__init__ = patched_init

    original_save_proxy = SettingsPage._save_proxy

    if not getattr(
        original_save_proxy,
        "_central_v118_hide_proxy_password_after_save",
        False,
    ):
        def patched_save_proxy(self, *args, **kwargs):
            try:
                return original_save_proxy(self, *args, **kwargs)
            finally:
                toggle = getattr(self, "show_proxy_password", None)
                if toggle is not None:
                    toggle.setChecked(False)
                password = getattr(self, "password", None)
                if password is not None:
                    password.setEchoMode(QLineEdit.EchoMode.Password)

        patched_save_proxy._central_v118_hide_proxy_password_after_save = True
        SettingsPage._save_proxy = patched_save_proxy


def _install_video_preview_resize_fix() -> None:
    cls = ReferenceAdvancedVideoEditorWidget
    original_resize = cls.__dict__.get("resizeEvent")

    if getattr(original_resize, "_central_v118_video_preview_resize", False):
        return

    def patched_resize(self, event) -> None:
        if original_resize is not None:
            original_resize(self, event)
        else:
            super(cls, self).resizeEvent(event)

        # A prévia pode estar pausada; nesse caso não chega um novo frame que
        # redimensione a imagem. Reajustamos após o layout terminar.
        QTimer.singleShot(
            0,
            lambda: self._refresh_video_pixmap()
            if hasattr(self, "_refresh_video_pixmap")
            else None,
        )

    patched_resize._central_v118_video_preview_resize = True
    cls.resizeEvent = patched_resize



def _install_independent_specialized_sources() -> None:
    """Separa la seleção de mídia especializada da seleção de notícias gerais."""
    # Propriedades adicionais no controller mantêm a persistência centralizada
    # nas preferências já usadas pela aplicação, sem trocar sua API pública.
    if not isinstance(
        getattr(MainUiController, "specialized_all_sources", None),
        property,
    ):
        def get_specialized_all(self) -> bool:
            return self.prefs.get_boolean(
                "desktop_specialized_all_sources",
                self.news_all_sources,
            )

        def set_specialized_all(self, value: bool) -> None:
            self.prefs.update(
                desktop_specialized_all_sources=bool(value)
            )

        MainUiController.specialized_all_sources = property(
            get_specialized_all,
            set_specialized_all,
        )

    if not isinstance(
        getattr(MainUiController, "selected_specialized_source_ids", None),
        property,
    ):
        def get_specialized_ids(self) -> set[str]:
            known = {
                str(source.id)
                for source in getattr(self, "specialized_sources", ())
                if getattr(source, "id", "")
            }
            legacy = self.prefs.get_string_set(
                "desktop_news_source_ids",
                set(),
            ) or set()
            legacy_specialized = set(legacy) & known
            values = self.prefs.get_string_set(
                "desktop_specialized_source_ids",
                legacy_specialized,
            )
            return set(values or set()) & known

        def set_specialized_ids(self, value: set[str]) -> None:
            known = {
                str(source.id)
                for source in getattr(self, "specialized_sources", ())
                if getattr(source, "id", "")
            }
            self.prefs.update(
                desktop_specialized_source_ids=set(value) & known
            )

        MainUiController.selected_specialized_source_ids = property(
            get_specialized_ids,
            set_specialized_ids,
        )

    if not getattr(
        getattr(MainUiController, "set_specialized_source", None),
        "_central_v118_specialized_sources",
        False,
    ):
        def set_specialized_source(self, source_id: str, checked: bool) -> None:
            values = set(self.selected_specialized_source_ids)
            if checked:
                values.add(str(source_id))
            else:
                values.discard(str(source_id))
            self.selected_specialized_source_ids = values
            self._emit()

        set_specialized_source._central_v118_specialized_sources = True
        MainUiController.set_specialized_source = set_specialized_source

    sources_cls = SourcesPage
    original_sources = sources_cls._sources
    original_selected = sources_cls._selected_ids
    original_toggle = sources_cls._toggle_source
    original_all_changed = sources_cls._all_news_changed
    original_set_visible = sources_cls._set_visible
    original_set_all = sources_cls._set_all
    original_refresh = sources_cls.refresh

    if getattr(original_sources, "_central_v118_general_sources", False):
        return

    def patched_sources(self):
        if self._tab() == 0:
            specialized_ids = {
                str(source.id)
                for source in getattr(self.controller, "specialized_sources", ())
            }
            return tuple(
                source
                for source in self.controller.news_sources
                if str(getattr(source, "id", "")) not in specialized_ids
            )
        return original_sources(self)

    def patched_selected_ids(self):
        tab = self._tab()
        if tab == 1:
            return original_selected(self)
        if tab == 0:
            general_ids = {
                str(getattr(source, "id", ""))
                for source in self._sources()
            }
            if self.controller.news_all_sources:
                return general_ids
            return set(self.controller.selected_news_source_ids) & general_ids

        specialized_ids = {
            str(getattr(source, "id", ""))
            for source in getattr(self.controller, "specialized_sources", ())
        }
        if self.controller.specialized_all_sources:
            return specialized_ids
        return set(self.controller.selected_specialized_source_ids) & specialized_ids

    def patched_toggle_source(self, source_id: str, checked: bool) -> None:
        if not source_id:
            return
        if self._tab() == 2:
            if self.controller.specialized_all_sources and not checked:
                self.controller.specialized_all_sources = False
                self.controller.selected_specialized_source_ids = {
                    str(source.id)
                    for source in self.controller.specialized_sources
                }
            self.controller.set_specialized_source(source_id, checked)
            self.refresh(self.controller.state)
            return
        if self._tab() == 0:
            if self.controller.news_all_sources:
                # A lista geral não pode colocar ids especializados no conjunto
                # legado: cada grupo é salvo independentemente a partir desta versão.
                self.controller.news_all_sources = False
                self.controller.selected_news_source_ids = {
                    str(source.id) for source in self._sources()
                }
            self.controller.set_news_source(source_id, checked)
            self.refresh(self.controller.state)
            return
        original_toggle(self, source_id, checked)

    def patched_all_changed(self, checked: bool) -> None:
        if self._guard or self._tab() == 1:
            return
        if self._tab() == 2:
            self.controller.specialized_all_sources = bool(checked)
            if checked:
                self.controller.selected_specialized_source_ids = set()
            self.refresh(self.controller.state)
            return
        original_all_changed(self, checked)

    def patched_set_visible(self, checked: bool) -> None:
        tab = self._tab()
        if tab not in {0, 2}:
            return original_set_visible(self, checked)

        is_specialized = tab == 2
        all_active = (
            self.controller.specialized_all_sources
            if is_specialized
            else self.controller.news_all_sources
        )
        if all_active and not checked:
            # Ao desmarcar um subconjunto durante o modo “todos”, começa com
            # todas as fontes daquele grupo selecionadas e remove só as visíveis.
            if is_specialized:
                self.controller.specialized_all_sources = False
                self.controller.selected_specialized_source_ids = {
                    str(source.id)
                    for source in self.controller.specialized_sources
                }
            else:
                self.controller.news_all_sources = False
                self.controller.selected_news_source_ids = {
                    str(source.id) for source in self._sources()
                }

        for source in self._visible_sources():
            if is_specialized:
                self.controller.set_specialized_source(source.id, checked)
            else:
                self.controller.set_news_source(source.id, checked)
        self.refresh(self.controller.state)

    def patched_set_all(self, checked: bool) -> None:
        if self._tab() != 2:
            return original_set_all(self, checked)
        self.controller.specialized_all_sources = bool(checked)
        self.controller.selected_specialized_source_ids = set()
        self.refresh(self.controller.state)

    def patched_refresh(self, state) -> None:
        original_refresh(self, state)
        if self._tab() != 2:
            return
        self._guard = True
        self.all_news.blockSignals(True)
        active = bool(self.controller.specialized_all_sources)
        self.all_news.setChecked(active)
        self.all_news.setText("ATIVADO" if active else "DESATIVADO")
        self.all_news.blockSignals(False)
        self._guard = False

    patched_sources._central_v118_general_sources = True
    sources_cls._sources = patched_sources
    sources_cls._selected_ids = patched_selected_ids
    sources_cls._toggle_source = patched_toggle_source
    sources_cls._all_news_changed = patched_all_changed
    sources_cls._set_visible = patched_set_visible
    sources_cls._set_all = patched_set_all
    sources_cls.refresh = patched_refresh

def install_remaining_program_patch() -> None:
    """Ajustes complementares para autenticação, configurações e editor de vídeo."""
    global _INSTALLED

    if _INSTALLED:
        return

    _install_login_password_visibility()
    _install_settings_password_visibility()
    _install_video_preview_resize_fix()
    _install_independent_specialized_sources()
    _INSTALLED = True
