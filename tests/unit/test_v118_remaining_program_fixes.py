from __future__ import annotations

from pathlib import Path

from monitor_noticias.app.runtime_runners import RuntimeNewsRunner
from monitor_noticias.ui.remaining_program_patch import should_preserve_login_password


ROOT = Path(__file__).resolve().parents[2]


def test_network_and_proxy_failures_preserve_typed_password():
    for code in (
        "NETWORK_ERROR",
        "NETWORK_TIMEOUT",
        "PROXY_ERROR",
        "PROXY_NOT_READY",
        "PROXY_AUTH_REQUIRED",
        "TLS_ERROR",
        "AUTH_UPSTREAM_ERROR",
    ):
        assert should_preserve_login_password(code)


def test_authentication_failures_still_clear_password():
    for code in (
        "AUTH_DENIED",
        "INVALID_CREDENTIALS",
        "USER_DISABLED",
        "AUTH_SESSION_EXPIRED",
        "SERVER_UPDATE_REQUIRED",
    ):
        assert not should_preserve_login_password(code)


def test_composition_installs_v118_without_removing_existing_patches():
    source = (
        ROOT / "src/monitor_noticias/app/composition.py"
    ).read_text(encoding="utf-8")

    assert "install_remaining_program_patch()" in source
    for integration in (
        "install_first_tabs_functional_patch()",
        "install_first_tabs_performance_patch()",
        "install_first_tabs_visual_patch()",
        "install_admin_user_management_patch()",
        "install_video_preview_layout_patch()",
        "install_video_timeline_side_controls_patch()",
    ):
        assert integration in source


def test_login_visibility_patch_does_not_change_auth_transport_or_permissions():
    source = (
        ROOT / "src/monitor_noticias/ui/remaining_program_patch.py"
    ).read_text(encoding="utf-8")

    assert "QLineEdit.EchoMode.Password" in source
    assert "QLineEdit.EchoMode.Normal" in source
    assert "_TRANSIENT_AUTH_CODES" in source
    assert "verify=False" not in source
    assert "permissions" not in source.lower()


def test_proxy_password_is_hidden_after_save_and_linux_label_is_neutral():
    source = (
        ROOT / "src/monitor_noticias/ui/remaining_program_patch.py"
    ).read_text(encoding="utf-8")

    assert 'toggle.setChecked(False)' in source
    assert 'label.setText("Iniciar com o sistema")' in source


def test_paused_video_preview_is_refreshed_after_resize():
    source = (
        ROOT / "src/monitor_noticias/ui/remaining_program_patch.py"
    ).read_text(encoding="utf-8")

    assert "QTimer.singleShot(" in source
    assert "self._refresh_video_pixmap()" in source


class FakePreferences:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_boolean(self, key, default=False):
        return bool(self.values.get(key, default))

    def get_string_set(self, key, default=None):
        value = self.values.get(key, default)
        return set(value or set())


def test_news_runner_keeps_general_and_specialized_source_groups_independent():
    general = type("Source", (), {"id": "nacional-globo", "name": "O Globo"})()
    specialized_a = type("Source", (), {
        "id": "especializada-defesatv", "name": "DefesaTV"
    })()
    specialized_b = type("Source", (), {
        "id": "especializada-poder-naval", "name": "Poder Naval"
    })()
    prefs = FakePreferences({
        "desktop_news_all_sources": False,
        "desktop_news_source_ids": {"nacional-globo"},
        "desktop_specialized_all_sources": True,
    })
    runner = RuntimeNewsRunner(
        repository=object(),
        prefs=prefs,
        news_sources=(general, specialized_a, specialized_b),
    )

    selected, all_sources = runner._selection()
    assert not all_sources
    assert {item.id for item in selected} == {
        "nacional-globo",
        "especializada-defesatv",
        "especializada-poder-naval",
    }


def test_news_runner_does_not_leak_specialized_ids_into_general_selection():
    general = type("Source", (), {"id": "nacional-globo", "name": "O Globo"})()
    specialized = type("Source", (), {
        "id": "especializada-defesatv", "name": "DefesaTV"
    })()
    prefs = FakePreferences({
        "desktop_news_all_sources": False,
        "desktop_news_source_ids": {"nacional-globo", "especializada-defesatv"},
        "desktop_specialized_all_sources": False,
        "desktop_specialized_source_ids": set(),
    })
    runner = RuntimeNewsRunner(
        repository=object(),
        prefs=prefs,
        news_sources=(general, specialized),
    )

    selected, all_sources = runner._selection()
    assert not all_sources
    assert [item.id for item in selected] == ["nacional-globo"]
