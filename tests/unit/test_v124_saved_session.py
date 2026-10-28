from __future__ import annotations

from monitor_noticias.auth.saved_session_v124 import (
    handle_saved_session_failure,
)


class FakeTokenStore:
    def __init__(self):
        self.cleared = False

    def clear(self):
        self.cleared = True


class FakeRuntime:
    def __init__(self):
        self.token_store = FakeTokenStore()
        self.session = object()


def test_definitive_saved_session_failure_clears_token():
    runtime = FakeRuntime()

    assert handle_saved_session_failure(runtime, "SESSION_EXPIRED") is True
    assert runtime.token_store.cleared
    assert runtime.session is None


def test_transient_saved_session_failure_preserves_token():
    runtime = FakeRuntime()

    assert handle_saved_session_failure(runtime, "NETWORK_TIMEOUT") is False
    assert not runtime.token_store.cleared
    assert runtime.session is None


def test_unknown_saved_session_failure_preserves_token():
    runtime = FakeRuntime()

    assert handle_saved_session_failure(runtime, "UNRECOGNIZED_SERVER_CODE") is False
    assert not runtime.token_store.cleared


def test_failure_codes_are_normalized():
    runtime = FakeRuntime()

    assert handle_saved_session_failure(runtime, " session_revoked ") is True
    assert runtime.token_store.cleared
