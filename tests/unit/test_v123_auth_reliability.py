from __future__ import annotations

import requests

from monitor_noticias.auth.client import AuthApiClient, AuthApiError
from monitor_noticias.auth.reliability_v123 import (
    _DEFINITIVE_SESSION_FAILURES,
    install_auth_reliability_patch,
)


class FakeResponse:
    text = "Authorization: Bearer sensitive-token; password=private-value"


class FakeTokenStore:
    def __init__(self, token="saved-token"):
        self.token = token
        self.cleared = False

    def load(self):
        return self.token

    def clear(self):
        self.cleared = True
        self.token = ""


class FakeClient:
    def __init__(self, error=None, session=None):
        self.error = error
        self.session = session

    def validate(self, _token):
        if self.error:
            raise self.error
        return self.session


def _runtime(error):
    runtime = object.__new__(__import__(
        "monitor_noticias.auth.runtime",
        fromlist=["AuthRuntime"],
    ).AuthRuntime)
    runtime.token_store = FakeTokenStore()
    runtime.client = FakeClient(error=error)
    runtime.session = None
    return runtime


def test_network_error_does_not_echo_exception_details_or_credentials():
    install_auth_reliability_patch()
    client = AuthApiClient("https://example.invalid/exec", type(
        "Device", (), {"device_id": "id", "device_name": "pc", "os_name": "test"}
    )())
    secret_url = "https://user:private-password@proxy.invalid/path?token=secret-token"
    error = client._network_error(requests.exceptions.ConnectionError(secret_url))

    assert error.code == "NETWORK_ERROR"
    assert "private-password" not in str(error)
    assert "secret-token" not in str(error)
    assert "proxy.invalid" not in str(error)
    assert "ConnectionError" in str(error)


def test_http_response_excerpt_is_suppressed_to_prevent_sensitive_body_leaks():
    install_auth_reliability_patch()
    assert AuthApiClient._safe_response_excerpt(FakeResponse()) == ""


def test_saved_session_token_is_preserved_for_transient_network_failure():
    runtime = _runtime(AuthApiError("temporary timeout", code="NETWORK_TIMEOUT"))

    assert runtime.validate_saved() is None
    assert runtime.token_store.token == "saved-token"
    assert not runtime.token_store.cleared


def test_saved_session_token_is_cleared_for_definitively_invalid_session():
    for code in _DEFINITIVE_SESSION_FAILURES:
        runtime = _runtime(AuthApiError("session invalid", code=code))
        assert runtime.validate_saved() is None
        assert runtime.token_store.cleared, code


def test_successful_saved_session_is_kept_in_runtime():
    session = object()
    runtime = _runtime(error=None)
    runtime.client.session = session

    assert runtime.validate_saved() is session
    assert runtime.session is session
    assert not runtime.token_store.cleared
