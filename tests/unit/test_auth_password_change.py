from monitor_noticias.auth.client import AuthApiClient
from monitor_noticias.auth.device import DeviceIdentity


def test_session_reads_password_change_flag():
    client = AuthApiClient(
        "https://example.invalid/exec",
        DeviceIdentity(
            device_id="id",
            device_name="pc",
            os_name="Windows",
        ),
    )

    session = client._session_from(
        {
            "ok": True,
            "token": "token",
            "user": {
                "username": "teste",
                "name": "Teste",
                "profile": "CONSULTA",
                "permissions": ["home"],
                "must_change_password": True,
            },
        }
    )

    assert session.user.must_change_password is True
