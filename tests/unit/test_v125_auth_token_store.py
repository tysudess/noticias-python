from __future__ import annotations

from monitor_noticias.auth.storage import AuthTokenStore


class FakeSecureStore:
    def __init__(self, value=""):
        self.value = value
        self.exists_calls = 0
        self.load_calls = 0
        self.raise_on_load = False

    def exists(self):
        self.exists_calls += 1
        return bool(self.value)

    def load(self):
        self.load_calls += 1
        if self.raise_on_load:
            raise RuntimeError("secure store unavailable")
        return self.value


def _store_with(secure_store):
    store = object.__new__(AuthTokenStore)
    store._store = secure_store
    return store


def test_load_reads_secure_store_once_without_exists_round_trip():
    secure = FakeSecureStore("  saved-token  ")

    assert _store_with(secure).load() == "saved-token"
    assert secure.load_calls == 1
    assert secure.exists_calls == 0


def test_load_returns_empty_when_no_saved_token():
    secure = FakeSecureStore("")

    assert _store_with(secure).load() == ""
    assert secure.load_calls == 1
    assert secure.exists_calls == 0


def test_load_safely_handles_unavailable_secure_store():
    secure = FakeSecureStore("saved-token")
    secure.raise_on_load = True

    assert _store_with(secure).load() == ""
    assert secure.load_calls == 1
    assert secure.exists_calls == 0


def test_load_returns_empty_when_backend_is_not_available():
    store = object.__new__(AuthTokenStore)
    store._store = None

    assert store.load() == ""
