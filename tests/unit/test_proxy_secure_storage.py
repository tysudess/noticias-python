from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.networking.proxy import ProxySettings


class FakeSecretStore:
    def __init__(self):
        self.value = ""

    def exists(self):
        return bool(self.value)

    def save(self, text):
        self.value = text

    def load(self):
        return self.value

    def delete(self):
        self.value = ""
        return True


def test_password_not_written_to_preferences(tmp_path):
    prefs_path = tmp_path / "prefs" / "monitor_prefs.properties"
    prefs = SharedPreferences(prefs_path)
    secret = FakeSecretStore()

    settings = ProxySettings(
        prefs,
        secret_store=secret,
    )

    settings.save(
        enabled=True,
        host="proxy.test",
        port=6060,
        username="usuario",
        password="senha-ultra-secreta",
    )

    raw = prefs_path.read_text(encoding="utf-8")

    assert "senha-ultra-secreta" not in raw
    assert secret.value == "senha-ultra-secreta"
    assert settings.load().password == "senha-ultra-secreta"


def test_legacy_plaintext_is_removed(tmp_path):
    prefs_path = tmp_path / "prefs" / "monitor_prefs.properties"
    prefs = SharedPreferences(prefs_path)
    prefs.update(desktop_proxy_password="senha-legada")

    secret = FakeSecretStore()

    settings = ProxySettings(
        prefs,
        secret_store=secret,
    )

    cfg = settings.load()

    assert cfg.password == "senha-legada"
    assert secret.value == "senha-legada"

    raw = prefs_path.read_text(encoding="utf-8")
    assert "senha-legada" not in raw
