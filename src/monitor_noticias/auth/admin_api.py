from __future__ import annotations

from typing import Any

from monitor_noticias.auth.client import AuthApiError
from monitor_noticias.auth.runtime import AuthRuntime


def _admin_session(runtime: AuthRuntime):
    session = runtime.session

    if session is None:
        raise AuthApiError(
            "Nenhuma sessão autenticada.",
            code="SESSION_MISSING",
        )

    if str(session.user.profile or "").strip().upper() != "ADMIN":
        raise AuthApiError(
            "Esta função é exclusiva do administrador.",
            code="ADMIN_REQUIRED",
        )

    return session


def _post_admin(
    runtime: AuthRuntime,
    action: str,
    **payload: Any,
) -> dict[str, Any]:
    session = _admin_session(runtime)

    request = {
        "action": action,
        "token": session.token,
        "device_id": runtime.device.device_id,
        **payload,
    }

    try:
        return runtime.client._post(request)
    except AuthApiError as exc:
        if exc.code == "UNKNOWN_ACTION":
            raise AuthApiError(
                (
                    "O Apps Script publicado ainda não possui a Administração "
                    "de Usuários V94. Atualize tools/auth_server/Code.gs e "
                    "publique uma NOVA versão do Web App."
                ),
                code="SERVER_UPDATE_REQUIRED",
            ) from exc
        raise


def list_users(
    runtime: AuthRuntime,
) -> list[dict[str, Any]]:
    data = _post_admin(
        runtime,
        "admin_list_users",
    )

    raw = data.get("users") or []

    if not isinstance(raw, list):
        raise AuthApiError(
            "O servidor retornou uma lista de usuários inválida.",
            code="INVALID_RESPONSE",
        )

    return [
        item
        for item in raw
        if isinstance(item, dict)
    ]


def create_user(
    runtime: AuthRuntime,
    *,
    username: str,
    name: str,
    temporary_password: str,
    profile: str,
    validity: str = "",
    max_devices: int = 1,
    permissions: str = "",
) -> dict[str, Any]:
    data = _post_admin(
        runtime,
        "admin_create_user",
        username=str(username or "").strip(),
        name=str(name or "").strip(),
        temporary_password=str(temporary_password or ""),
        profile=str(profile or "").strip().upper(),
        validity=str(validity or "").strip(),
        max_devices=max(1, int(max_devices)),
        permissions=str(permissions or "").strip(),
    )

    user = data.get("user")

    if not isinstance(user, dict):
        raise AuthApiError(
            "O servidor não retornou o usuário criado.",
            code="INVALID_RESPONSE",
        )

    return user


def reset_password(
    runtime: AuthRuntime,
    *,
    username: str,
    temporary_password: str,
) -> None:
    _post_admin(
        runtime,
        "admin_reset_password",
        username=str(username or "").strip(),
        temporary_password=str(temporary_password or ""),
    )
