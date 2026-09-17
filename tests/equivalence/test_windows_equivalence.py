from pathlib import Path

from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import DEFAULT_PROXY_HOST, DEFAULT_PROXY_PORT, ProxySettings
from monitor_noticias.windows.startup import RUN_KEY, VALUE_NAME, startup_command


class FakeSecretStore:
    def __init__(self): self.value = ""
    def exists(self): return bool(self.value)
    def save(self, text): self.value = text
    def load(self): return self.value
    def delete(self): self.value = ""; return True


def test_kotlin_proxy_defaults_and_legacy_host_equivalence(tmp_path):
    prefs = SharedPreferences(tmp_path / "data/prefs/monitor_prefs.properties")
    secret = FakeSecretStore()
    settings = ProxySettings(prefs, secret_store=secret)
    cfg = settings.load()
    assert cfg.enabled is False
    assert cfg.host == DEFAULT_PROXY_HOST == "proxy-7dn.mb"
    assert cfg.port == DEFAULT_PROXY_PORT == 6060
    assert cfg.username == ""
    assert cfg.password == ""

    prefs.update(desktop_proxy_host="proxy-7db.mb")
    assert settings.load().host == "proxy-7dn.mb"


def test_kotlin_registry_contract_equivalence():
    assert RUN_KEY == r"Software\Microsoft\Windows\CurrentVersion\Run"
    assert VALUE_NAME == "MonitorDeNoticias"
    exe = Path(r"C:\Apps\Monitor De Noticias\MonitorDeNoticias.exe")
    assert startup_command(exe) == '"C:\\Apps\\Monitor De Noticias\\MonitorDeNoticias.exe"'


def test_kotlin_proxy_status_labels_equivalence(tmp_path):
    prefs = SharedPreferences(tmp_path / "data/prefs/monitor_prefs.properties")
    secret = FakeSecretStore()
    settings = ProxySettings(prefs, secret_store=secret)
    assert settings.load().status_label == "Proxy desativado"
    settings.save(enabled=True, host="proxy.test", port=6060, username="", password="")
    assert settings.load().status_label == "Proxy requer configuração"
    settings.save(enabled=True, host="proxy.test", port=6060, username="u", password="p")
    assert settings.load().status_label == "Proxy pronto"
