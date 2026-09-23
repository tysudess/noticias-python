from __future__ import annotations


AUTH_API_URL = (
    "https://script.google.com/macros/s/AKfycbzSv0Zxz-EQnFHKPTTtfvAErWt2cL2gPBLryMnMQiOFNv4L14FpgpZVeXWVy3YEVXgW/exec"
)


def auth_server_configured() -> bool:
    value = (
        AUTH_API_URL
        or ""
    ).strip()

    return (
        value.startswith(
            "https://script.google.com/"
        )
        and "/macros/s/" in value
        and value.endswith(
            "/exec"
        )
    )
