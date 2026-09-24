from monitor_noticias.auth.client import AuthApiClient, AuthApiError
from monitor_noticias.auth.device import DeviceIdentity


def _client():
    return AuthApiClient(
        "https://example.invalid/exec",
        DeviceIdentity("id", "pc", "Windows"),
    )


def _payload(version="1.1.1", must_change=True):
    return {
        "ok": True,
        "token": "token",
        "expires_at": "2026-09-24T10:00:00.000Z",
        "user": {
            "auth_server_version": version,
            "username": "usuario",
            "name": "Usuário",
            "profile": "CONSULTA",
            "permissions": ["home", "news"],
            "must_change_password": must_change,
        },
    }


def test_v61_reads_force_change_true():
    session = _client()._session_from(_payload())
    assert session.user.must_change_password is True


def test_old_server_is_rejected():
    try:
        _client()._session_from(_payload(version="1.1.0"))
    except AuthApiError as exc:
        assert exc.code == "SERVER_UPDATE_REQUIRED"
    else:
        raise AssertionError("Servidor antigo deveria ser recusado")
