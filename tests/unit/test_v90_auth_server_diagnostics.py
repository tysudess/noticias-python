from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _auth_version(source: str) -> tuple[int, int, int]:
    match = re.search(
        r'const\s+AUTH_VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"\s*;',
        source,
    )

    assert match is not None, (
        "AUTH_VERSION sem formato semântico válido em tools/auth_server/Code.gs"
    )

    return tuple(
        int(part)
        for part in match.groups()
    )


def test_v90_apps_script_keeps_all_auth_actions_and_bumps_version():
    source = _read("tools/auth_server/Code.gs")

    # V90 introduziu a linha 1.2.x. Versões posteriores do Auth Server
    # (por exemplo, V94 = 1.3.0) devem continuar aprovadas desde que não
    # regridam abaixo da versão mínima introduzida pela V90.
    assert _auth_version(source) >= (1, 2, 0)

    assert 'action === "login"' in source
    assert 'action === "validate"' in source
    assert 'action === "logout"' in source
    assert 'action === "change_password"' in source
    assert 'server_timing_ms' in source


def test_v90_validation_does_not_wait_twenty_seconds_for_script_lock():
    source = _read("tools/auth_server/Code.gs")
    start = source.index("function validateSession_(request)")
    end = source.index("function changePassword_(request)")
    validate = source[start:end]

    assert "waitLock(20000)" not in validate
    assert "findSessionByToken_(token)" in validate
    assert "findUser_(session.username)" in validate
    assert "userAccessError_(user)" in validate
    assert "touchValidationBestEffort_" in validate


def test_v90_validation_uses_server_side_finders_and_nonblocking_heartbeat():
    source = _read("tools/auth_server/Code.gs")

    assert ".createTextFinder(normalized)" in source
    assert ".createTextFinder(tokenHash)" in source
    assert "VALIDATION_TOUCH_MINUTES = 15" in source
    assert "lock.tryLock(50)" in source


def test_v90_diagnostics_has_real_auth_and_proxy_checks():
    source = _read("src/monitor_noticias/diagnostics.py")

    assert "test_server" in source
    assert "test_post_transport" in source
    assert "client.validate(token)" in source
    assert "controller.test_proxy" in source
    assert "build_diagnostic_package" in source
    assert "sanitize_log_text" in source


def test_v90_settings_installs_compact_diagnostic_launcher():
    source = _read("src/monitor_noticias/ui/diagnostics_panel.py")
    application = _read("src/monitor_noticias/app/application.py")

    assert "Diagnóstico do sistema" in source
    assert "Executar diagnóstico" in source
    assert "Gerar ZIP de diagnóstico" in source
    assert "install_diagnostics_panel" in application
    assert "window,\n            auth_runtime" in application
