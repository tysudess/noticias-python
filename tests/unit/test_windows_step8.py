from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import (
    DEFAULT_PROXY_HOST,
    DEFAULT_PROXY_PORT,
    ProxySettings,
)
from monitor_noticias.windows.dpapi import DpapiTextStore
from monitor_noticias.windows.notifications import WindowsTrayNotifier
from monitor_noticias.windows.processes import HiddenProcessRunner
from monitor_noticias.windows.startup import RUN_KEY, VALUE_NAME, StartupManager, startup_command


class FakeSecretStore:
    def __init__(self):
        self.value = ""
    def exists(self): return bool(self.value)
    def save(self, text): self.value = text
    def load(self): return self.value
    def delete(self):
        self.value = ""
        return True


class FakeRegistry:
    def __init__(self): self.values = {}
    def set_string(self, path, name, value): self.values[(path, name)] = value
    def delete_value(self, path, name): self.values.pop((path, name), None)


class FakeResponse:
    def __init__(self, status_code): self.status_code = status_code


class FakeSession:
    def __init__(self, status=204, error=None):
        self.status = status
        self.error = error
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error: raise self.error
        return FakeResponse(self.status)


def make_proxy(tmp_path: Path):
    prefs = SharedPreferences(tmp_path / "data/prefs/monitor_prefs.properties")
    secret = FakeSecretStore()
    return prefs, secret, ProxySettings(prefs, secret_store=secret)


def test_proxy_defaults_and_disabled(tmp_path):
    prefs, secret, settings = make_proxy(tmp_path)
    cfg = settings.load()
    assert cfg.enabled is False
    assert cfg.host == DEFAULT_PROXY_HOST
    assert cfg.port == DEFAULT_PROXY_PORT
    assert cfg.status_label == "Proxy desativado"
    assert settings.requests_proxies(cfg) is None


def test_proxy_migrates_legacy_host_and_plaintext_password(tmp_path):
    prefs, secret, settings = make_proxy(tmp_path)
    prefs.update(
        desktop_proxy_enabled=True,
        desktop_proxy_host="proxy-7db.mb",
        desktop_proxy_port=6060,
        desktop_proxy_username="usuario",
        desktop_proxy_password="senha-ficticia",
    )
    cfg = settings.load()
    assert cfg.host == "proxy-7dn.mb"
    assert cfg.password == "senha-ficticia"
    assert secret.value == "senha-ficticia"
    assert prefs.get_string("desktop_proxy_password", None) is None
    raw = prefs.file.read_text(encoding="utf-8")
    assert "senha-ficticia" not in raw


def test_proxy_save_clamps_port_and_url_encodes_credentials(tmp_path):
    prefs, secret, settings = make_proxy(tmp_path)
    cfg = settings.save(enabled=True, host=" proxy.example ", port=70000, username="u s", password="p@ss")
    assert cfg.port == 65535
    assert cfg.host == "proxy.example"
    proxies = settings.requests_proxies(cfg)
    assert proxies == {
        "http": "http://u%20s:p%40ss@proxy.example:65535",
        "https": "http://u%20s:p%40ss@proxy.example:65535",
    }
    assert "p@ss" not in prefs.file.read_text(encoding="utf-8")


def test_proxy_test_messages_and_contract(tmp_path):
    prefs, secret, settings = make_proxy(tmp_path)
    assert settings.test_connection(session=FakeSession()) == (False, "Ative o proxy antes de testar.")
    settings.save(enabled=True, host="proxy.test", port=6060, username="", password="")
    assert settings.test_connection(session=FakeSession()) == (False, "Informe usuário e senha do proxy.")
    settings.save(enabled=True, host="proxy.test", port=6060, username="u", password="p")
    session = FakeSession(204)
    assert settings.test_connection(session=session) == (True, "Conexão pelo proxy realizada com sucesso.")
    url, kwargs = session.calls[-1]
    assert url.endswith("/generate_204")
    assert kwargs["timeout"] == 12
    assert kwargs["allow_redirects"] is True


def test_proxy_error_message_redacts_password(tmp_path):
    prefs, secret, settings = make_proxy(tmp_path)
    settings.save(enabled=True, host="proxy.test", port=6060, username="u", password="senha-super-secreta")
    session = FakeSession(error=RuntimeError("falha http://u:senha-super-secreta@proxy.test:6060"))
    ok, message = settings.test_connection(session=session)
    assert ok is False
    assert "senha-super-secreta" not in message
    assert "***" in message


def test_startup_command_and_registry_values(tmp_path):
    backend = FakeRegistry()
    mgr = StartupManager(backend)
    exe = tmp_path / "Monitor de Noticias" / "MonitorDeNoticias.exe"
    assert mgr.configure(True, executable=exe) is True
    assert backend.values[(RUN_KEY, VALUE_NAME)] == f'"{exe}"'
    assert startup_command(exe) == f'"{exe}"'
    assert mgr.configure(False) is True
    assert (RUN_KEY, VALUE_NAME) not in backend.values


def test_notification_adapter_preserves_title_and_message():
    class Tray:
        def __init__(self): self.calls=[]
        def showMessage(self, title, message): self.calls.append((title, message))
    tray = Tray()
    notify = WindowsTrayNotifier(tray)
    notify("Monitor de Notícias", "✓ 1 nova(s) notícia(s)")
    assert tray.calls == [("Monitor de Notícias", "✓ 1 nova(s) notícia(s)")]


def test_process_runner_exit_stdout_and_space_argument(tmp_path):
    runner = HiddenProcessRunner()
    script = "import sys; print(sys.argv[1]); print('ERR', file=sys.stderr); raise SystemExit(7)"
    result = runner.run(
        [sys.executable, "-c", script, "argumento com espacos"],
        directory=tmp_path,
        timeout=10,
    )
    assert result.exit_code == 7
    assert "argumento com espacos" in result.output
    assert "ERR" in result.output


def test_process_runner_missing_file(tmp_path):
    runner = HiddenProcessRunner()
    with pytest.raises(FileNotFoundError):
        runner.start(["__arquivo_que_nao_existe__.exe"], directory=tmp_path)


@pytest.mark.skipif(os.name != "nt", reason="DPAPI real requer Windows")
def test_dpapi_roundtrip_current_user(tmp_path):
    store = DpapiTextStore(tmp_path / "test-secret.dpapi")
    store.save("segredo-ficticio")
    raw = store.path.read_text(encoding="utf-8")
    assert "segredo-ficticio" not in raw
    assert store.load() == "segredo-ficticio"
    assert store.delete()


@pytest.mark.skipif(os.name != "nt", reason="Compatibilidade .NET DPAPI requer Windows")
def test_dpapi_compatible_with_dotnet_protecteddata(tmp_path):
    import base64
    from monitor_noticias.windows.dpapi import unprotect_text_from_base64, protect_text_to_base64

    plain = "credencial-ficticia-step8"
    plain_b64 = base64.b64encode(plain.encode("utf-8")).decode("ascii")
    protect_script = (
        "Add-Type -AssemblyName System.Security;"
        "$b=[Convert]::FromBase64String($env:STEP8_PLAIN);"
        "$e=[System.Security.Cryptography.ProtectedData]::Protect($b,$null,"
        "[System.Security.Cryptography.DataProtectionScope]::CurrentUser);"
        "[Console]::Write([Convert]::ToBase64String($e))"
    )
    env = os.environ.copy()
    env["STEP8_PLAIN"] = plain_b64
    dotnet_blob = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", protect_script],
        capture_output=True, text=True, check=True, env=env
    ).stdout.strip()
    assert unprotect_text_from_base64(dotnet_blob) == plain

    python_blob = protect_text_to_base64(plain)
    unprotect_script = (
        "Add-Type -AssemblyName System.Security;"
        "$e=[Convert]::FromBase64String($env:STEP8_BLOB);"
        "$p=[System.Security.Cryptography.ProtectedData]::Unprotect($e,$null,"
        "[System.Security.Cryptography.DataProtectionScope]::CurrentUser);"
        "[Console]::Write([Text.Encoding]::UTF8.GetString($p))"
    )
    env["STEP8_BLOB"] = python_blob
    decoded = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", unprotect_script],
        capture_output=True, text=True, check=True, env=env
    ).stdout
    assert decoded == plain


@pytest.mark.skipif(os.name != "nt", reason="Registry real requer Windows")
def test_winreg_backend_isolated_test_key():
    from monitor_noticias.windows.startup import WinRegBackend
    import winreg

    path = r"Software\MonitorDeNoticias\Tests\Step8"
    name = "Step8Value"
    backend = WinRegBackend()
    try:
        backend.set_string(path, name, "valor-ficticio")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
            value, value_type = winreg.QueryValueEx(key, name)
        assert value == "valor-ficticio"
        assert value_type == winreg.REG_SZ
    finally:
        backend.delete_value(path, name)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            pass
