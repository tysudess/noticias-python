from __future__ import annotations

import logging

from monitor_noticias.auth.storage import AuthTokenStore


class FailingSecureStore:
    def load(self):
        raise RuntimeError("credential=never-log-this-secret")


def test_secure_store_failure_is_logged_without_exception_details(caplog):
    store = object.__new__(AuthTokenStore)
    store._store = FailingSecureStore()

    with caplog.at_level(logging.WARNING, logger="monitor_noticias.auth.storage"):
        assert store.load() == ""

    assert "RuntimeError" in caplog.text
    assert "falha ao ler token do cofre seguro" in caplog.text
    assert "never-log-this-secret" not in caplog.text
    assert "credential=" not in caplog.text
