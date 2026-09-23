from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import requests

from .device import DeviceIdentity
from .models import (
    AuthSession,
    AuthUser,
)


log = logging.getLogger(
    __name__
)


class AuthApiError(
    RuntimeError
):
    def __init__(
        self,
        message: str,
        *,
        code: str = "AUTH_ERROR",
    ) -> None:
        super().__init__(
            message
        )
        self.code = code


class AuthApiClient:
    def __init__(
        self,
        api_url: str,
        device: DeviceIdentity,
        *,
        timeout: float = 18.0,
    ) -> None:
        self.api_url = (
            str(
                api_url
            ).strip()
        )
        self.device = device
        self.timeout = float(
            timeout
        )

    def _post(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    "User-Agent":
                        (
                            "CentralInteligenteDeMidia/"
                            "AuthClient-1.0"
                        ),
                    "Accept":
                        "application/json",
                },
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            raise AuthApiError(
                (
                    "Não foi possível conectar ao "
                    "servidor de autenticação."
                ),
                code="NETWORK_ERROR",
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise AuthApiError(
                (
                    "O servidor de autenticação "
                    "retornou uma resposta inválida."
                ),
                code="INVALID_RESPONSE",
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise AuthApiError(
                "Resposta inválida do servidor.",
                code="INVALID_RESPONSE",
            )

        if not bool(
            data.get(
                "ok"
            )
        ):
            raise AuthApiError(
                str(
                    data.get(
                        "message"
                    )
                    or (
                        "Acesso não autorizado."
                    )
                ),
                code=str(
                    data.get(
                        "code"
                    )
                    or "AUTH_DENIED"
                ),
            )

        return data

    def login(
        self,
        username: str,
        password: str,
    ) -> AuthSession:
        data = self._post(
            {
                "action":
                    "login",
                "username":
                    username,
                "password":
                    password,
                "device_id":
                    self.device.device_id,
                "device_name":
                    self.device.device_name,
                "os":
                    self.device.os_name,
            }
        )

        return self._session_from(
            data
        )

    def validate(
        self,
        token: str,
    ) -> AuthSession:
        data = self._post(
            {
                "action":
                    "validate",
                "token":
                    token,
                "device_id":
                    self.device.device_id,
            }
        )

        return self._session_from(
            data
        )

    def logout(
        self,
        token: str,
    ) -> None:
        if not token:
            return

        self._post(
            {
                "action":
                    "logout",
                "token":
                    token,
                "device_id":
                    self.device.device_id,
            }
        )

    @staticmethod
    def _session_from(
        data: dict[str, Any],
    ) -> AuthSession:
        user_data = (
            data.get(
                "user"
            )
            or {}
        )

        raw_permissions = (
            user_data.get(
                "permissions"
            )
            or []
        )

        permissions = frozenset(
            str(
                item
            ).strip().lower()
            for item in raw_permissions
            if str(
                item
            ).strip()
        )

        expires_at = None

        raw_expires = str(
            data.get(
                "expires_at"
            )
            or ""
        ).strip()

        if raw_expires:
            try:
                expires_at = (
                    datetime.fromisoformat(
                        raw_expires.replace(
                            "Z",
                            "+00:00",
                        )
                    )
                )
            except ValueError:
                expires_at = None

        token = str(
            data.get(
                "token"
            )
            or ""
        )

        if not token:
            raise AuthApiError(
                "Servidor não retornou token de sessão.",
                code="TOKEN_MISSING",
            )

        user = AuthUser(
            username=str(
                user_data.get(
                    "username"
                )
                or ""
            ),
            name=str(
                user_data.get(
                    "name"
                )
                or ""
            ),
            profile=str(
                user_data.get(
                    "profile"
                )
                or ""
            ),
            permissions=permissions,
        )

        return AuthSession(
            token=token,
            expires_at=expires_at,
            user=user,
        )
