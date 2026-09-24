from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import requests

from monitor_noticias.networking.proxy import ProxySettings

from .device import DeviceIdentity
from .models import (
    AuthSession,
    AuthUser,
)


log = logging.getLogger(__name__)


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts: list[int] = []

    for piece in str(value or "").split(".")[:3]:
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts)


class AuthApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "AUTH_ERROR",
    ) -> None:
        super().__init__(message)
        self.code = code


class AuthApiClient:
    def __init__(
        self,
        api_url: str,
        device: DeviceIdentity,
        *,
        proxy_settings: ProxySettings | None = None,
        timeout: float = 18.0,
    ) -> None:
        self.api_url = str(api_url).strip()
        self.device = device
        self.proxy_settings = proxy_settings
        self.timeout = float(timeout)

    def _proxies(self) -> dict[str, str] | None:
        if self.proxy_settings is None:
            return None

        config = self.proxy_settings.load()

        if not config.enabled:
            return None

        if not config.ready:
            raise AuthApiError(
                "O Proxy Geral está ativo, mas usuário/senha não estão configurados.",
                code="PROXY_NOT_READY",
            )

        return self.proxy_settings.requests_proxies(config)

    def _request_kwargs(self) -> dict[str, Any]:
        return {
            "timeout": self.timeout,
            "allow_redirects": True,
            "proxies": self._proxies(),
            "headers": {
                "User-Agent": "CentralInteligenteDeMidia/AuthClient-1.1",
                "Accept": "application/json",
            },
        }

    def test_server(self) -> tuple[bool, str]:
        try:
            response = requests.get(
                self.api_url,
                **self._request_kwargs(),
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict):
                raise ValueError("Resposta não é objeto JSON.")

            if bool(data.get("ok")) and str(data.get("status") or "").lower() == "online":
                version = str(data.get("version") or "").strip()

                if _version_tuple(version) < (1, 1, 2):
                    return False, (
                        "Servidor de autenticação desatualizado "
                        f"(versão {version or 'desconhecida'}). "
                        "Atualize e reimplante o Apps Script V62."
                    )

                return True, (
                    "Servidor de autenticação acessível "
                    f"(versão {version})."
                )

            return False, "Servidor respondeu, mas não confirmou status online."

        except AuthApiError as exc:
            return False, str(exc)
        except requests.ProxyError:
            return False, "Falha ao conectar através do Proxy Geral."
        except requests.Timeout:
            return False, "Tempo limite ao acessar o servidor de autenticação."
        except requests.RequestException as exc:
            return False, (
                "Não foi possível acessar o servidor de autenticação: "
                + (str(exc) or exc.__class__.__name__)
            )
        except Exception as exc:
            return False, (
                "Resposta inválida do servidor de autenticação: "
                + (str(exc) or exc.__class__.__name__)
            )

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                **self._request_kwargs(),
            )
            response.raise_for_status()
        except AuthApiError:
            raise
        except requests.ProxyError as exc:
            raise AuthApiError(
                "Falha ao conectar através do Proxy Geral.",
                code="PROXY_ERROR",
            ) from exc
        except requests.Timeout as exc:
            raise AuthApiError(
                "Tempo limite ao acessar o servidor de autenticação.",
                code="NETWORK_TIMEOUT",
            ) from exc
        except requests.RequestException as exc:
            raise AuthApiError(
                "Não foi possível conectar ao servidor de autenticação.",
                code="NETWORK_ERROR",
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise AuthApiError(
                "O servidor de autenticação retornou uma resposta inválida.",
                code="INVALID_RESPONSE",
            ) from exc

        if not isinstance(data, dict):
            raise AuthApiError(
                "Resposta inválida do servidor.",
                code="INVALID_RESPONSE",
            )

        if not bool(data.get("ok")):
            raise AuthApiError(
                str(data.get("message") or "Acesso não autorizado."),
                code=str(data.get("code") or "AUTH_DENIED"),
            )

        return data

    def login(self, username: str, password: str) -> AuthSession:
        data = self._post(
            {
                "action": "login",
                "username": username,
                "password": password,
                "device_id": self.device.device_id,
                "device_name": self.device.device_name,
                "os": self.device.os_name,
            }
        )
        return self._session_from(data)

    def validate(self, token: str) -> AuthSession:
        data = self._post(
            {
                "action": "validate",
                "token": token,
                "device_id": self.device.device_id,
            }
        )
        return self._session_from(data)

    def change_password(
        self,
        token: str,
        current_password: str,
        new_password: str,
    ) -> AuthSession:
        try:
            data = self._post(
                {
                    "action":
                        "change_password",
                    "token":
                        token,
                    "device_id":
                        self.device.device_id,
                    "current_password":
                        current_password,
                    "new_password":
                        new_password,
                }
            )
        except AuthApiError as exc:
            if exc.code == "UNKNOWN_ACTION" or str(exc).strip().lower() == "ação inválida.":
                raise AuthApiError(
                    (
                        "O Apps Script publicado ainda é uma versão antiga e "
                        "não possui a troca de senha. Atualize o Code.gs para "
                        "a V62 e crie uma NOVA versão da implantação do Web App."
                    ),
                    code="SERVER_UPDATE_REQUIRED",
                ) from exc
            raise

        return self._session_from(
            data
        )

    def logout(self, token: str) -> None:
        if not token:
            return

        self._post(
            {
                "action": "logout",
                "token": token,
                "device_id": self.device.device_id,
            }
        )

    @staticmethod
    def _session_from(data: dict[str, Any]) -> AuthSession:
        user_data = data.get("user") or {}

        server_version = str(
            user_data.get("auth_server_version") or ""
        ).strip()

        if (
            not server_version
            or _version_tuple(server_version) < (1, 1, 2)
        ):
            raise AuthApiError(
                (
                    "O servidor de autenticação está desatualizado. "
                    "Atualize a implantação do Google Apps Script "
                    "para a versão V62 e tente novamente."
                ),
                code="SERVER_UPDATE_REQUIRED",
            )

        raw_permissions = user_data.get("permissions") or []

        permissions = frozenset(
            str(item).strip().lower()
            for item in raw_permissions
            if str(item).strip()
        )

        expires_at = None
        raw_expires = str(data.get("expires_at") or "").strip()

        if raw_expires:
            try:
                expires_at = datetime.fromisoformat(
                    raw_expires.replace("Z", "+00:00")
                )
            except ValueError:
                expires_at = None

        token = str(data.get("token") or "")

        if not token:
            raise AuthApiError(
                "Servidor não retornou token de sessão.",
                code="TOKEN_MISSING",
            )

        user = AuthUser(
            username=str(user_data.get("username") or ""),
            name=str(user_data.get("name") or ""),
            profile=str(user_data.get("profile") or ""),
            permissions=permissions,
            must_change_password=bool(
                user_data.get(
                    "must_change_password",
                    False,
                )
            ),
        )

        return AuthSession(
            token=token,
            expires_at=expires_at,
            user=user,
        )
