from __future__ import annotations


# V57:
# Depois de publicar o Apps Script, esta URL será substituída pela URL /exec.
AUTH_API_URL = (
    "COLE_AQUI_A_URL_DO_APPS_SCRIPT_EXEC"
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
