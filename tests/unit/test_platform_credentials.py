from monitor_noticias.platform.credentials import LinuxKeyringTextStore


class FakeKeyring:
    def __init__(self):
        self.value = None

    def get_password(self, service, account):
        return self.value

    def set_password(self, service, account, password):
        self.value = password

    def delete_password(self, service, account):
        self.value = None


def test_keyring_roundtrip():
    fake = FakeKeyring()
    store = LinuxKeyringTextStore(keyring_api=fake)

    assert store.exists() is False
    store.save("segredo")
    assert store.exists() is True
    assert store.load() == "segredo"
    assert store.delete() is True
    assert store.exists() is False
