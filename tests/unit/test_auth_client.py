from monitor_noticias.auth.client import (
    AuthApiClient,
)
from monitor_noticias.auth.device import (
    DeviceIdentity,
)


def test_session_mapping() -> None:
    client = AuthApiClient(
        "https://example.invalid/exec",
        DeviceIdentity(
            device_id="abc",
            device_name="pc",
            os_name="Windows",
        ),
    )

    session = client._session_from(
        {
            "ok": True,
            "token": "token-123",
            "expires_at":
                "2026-09-24T10:00:00.000Z",
            "user": {
                "username": "operador",
                "name": "Operador",
                "profile": "OPERADOR",
                "permissions": [
                    "home",
                    "news",
                    "videos",
                ],
            },
        }
    )

    assert session.token == "token-123"
    assert session.user.username == "operador"
    assert session.user.can("news")
    assert not session.user.can("settings")
