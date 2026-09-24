from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Any

import requests

from monitor_noticias.networking.proxy import ProxySettings

from .device import DeviceIdentity
from .models import AuthSession, AuthUser


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

    def _proxy_config(self):
        if self.proxy_settings is None:
            return None
        return self.proxy_settings.load()

    def _proxies(
        self,
        config=None,
    ) -> dict[str, str] | None:
        if self.proxy_settings is None:
            return None

        cfg = (
            config
            if config is not None
            else self.proxy_settings.load()
        )

        if not cfg.enabled:
            return None

        if not cfg.ready:
            raise AuthApiError(
                "O Proxy Geral está ativo, mas usuário/senha não estão configurados.",
                code="PROXY_NOT_READY",
            )

        return self.proxy_settings.requests_proxies(cfg)

    def _request_context(self):
        cfg = self._proxy_config()

        verify = True
        proxies = None

        if (
            self.proxy_settings is not None
            and cfg is not None
        ):
            proxies = self._proxies(cfg)
            verify = self.proxy_settings.requests_verify(cfg)

        session = requests.Session()

        # V71:
        # Proxy Geral ativo = não herdar HTTP_PROXY/HTTPS_PROXY/NO_PROXY
        # do Ubuntu/Windows. A sessão usa exclusivamente a configuração
        # escolhida dentro da Central.
        if cfg is not None and cfg.enabled:
            session.trust_env = False

        return session, cfg, proxies, verify

    def _headers(
        self,
        *,
        post: bool = False,
    ) -> dict[str, str]:
        headers = {
            "User-Agent": "CentralInteligenteDeMidia/AuthClient-1.2",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        }

        if post:
            # O Apps Script lê e faz JSON.parse(e.postData.contents),
            # portanto o conteúdo continua JSON, mas usamos text/plain
            # para máxima compatibilidade com filtros/proxies corporativos.
            headers["Content-Type"] = "text/plain; charset=utf-8"

        return headers

    @staticmethod
    def _safe_response_excerpt(
        response: requests.Response,
    ) -> str:
        try:
            text = (response.text or "").strip()
        except Exception:
            return ""

        if not text:
            return ""

        # Limita para não despejar páginas HTML inteiras na interface.
        return " ".join(text.split())[:220]

    def _http_error(
        self,
        response: requests.Response,
    ) -> AuthApiError:
        status = int(response.status_code)
        excerpt = self._safe_response_excerpt(response)

        if status == 407:
            return AuthApiError(
                "O proxy recusou usuário/senha (HTTP 407). "
                "Confira as credenciais do Proxy Geral.",
                code="PROXY_AUTH_REQUIRED",
            )

        if status in {401, 403}:
            message = (
                f"O acesso ao servidor de autenticação foi bloqueado "
                f"(HTTP {status})."
            )

            if excerpt:
                message += " Resposta: " + excerpt

            return AuthApiError(
                message,
                code="AUTH_HTTP_BLOCKED",
            )

        if status == 429:
            return AuthApiError(
                "O servidor limitou temporariamente as requisições (HTTP 429). "
                "Aguarde alguns instantes e tente novamente.",
                code="AUTH_RATE_LIMIT",
            )

        if 500 <= status <= 599:
            return AuthApiError(
                f"O servidor/proxy retornou HTTP {status}.",
                code="AUTH_UPSTREAM_ERROR",
            )

        message = (
            f"O servidor de autenticação retornou HTTP {status}."
        )

        if excerpt:
            message += " Resposta: " + excerpt

        return AuthApiError(
            message,
            code="AUTH_HTTP_ERROR",
        )

    def _network_error(
        self,
        exc: requests.exceptions.RequestException,
    ) -> AuthApiError:
        detail = str(exc) or exc.__class__.__name__

        # Nunca expõe credencial de proxy nos detalhes.
        if self.proxy_settings is not None:
            try:
                cfg = self.proxy_settings.load()

                if cfg.password:
                    detail = detail.replace(
                        cfg.password,
                        "***",
                    )
            except Exception:
                pass

        return AuthApiError(
            "Falha de rede ao acessar o servidor de autenticação. "
            + detail[:350],
            code="NETWORK_ERROR",
        )

    def test_server(self) -> tuple[bool, str]:
        session, _cfg, proxies, verify = self._request_context()

        try:
            response = session.get(
                self.api_url,
                timeout=self.timeout,
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                headers=self._headers(),
            )

            if not (200 <= response.status_code <= 399):
                error = self._http_error(response)
                return False, str(error)

            data = response.json()

            if not isinstance(data, dict):
                raise ValueError("Resposta não é objeto JSON.")

            if (
                bool(data.get("ok"))
                and str(data.get("status") or "").lower() == "online"
            ):
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

        except requests.exceptions.ProxyError:
            return False, "Falha ao conectar através do Proxy Geral."

        except requests.exceptions.Timeout:
            return False, "Tempo limite ao acessar o servidor de autenticação."

        except requests.exceptions.SSLError:
            return False, (
                "Falha na validação HTTPS. O modo de compatibilidade "
                "é restrito ao proxy corporativo autorizado."
            )

        except requests.exceptions.RequestException as exc:
            return False, str(self._network_error(exc))

        except Exception as exc:
            return False, (
                "Resposta inválida do servidor de autenticação: "
                + (str(exc) or exc.__class__.__name__)
            )

        finally:
            session.close()

    def test_post_transport(self) -> tuple[bool, str]:
        """Testa o mesmo canal POST usado no login sem enviar senha real."""

        session, _cfg, proxies, verify = self._request_context()

        payload = {
            "action": "__connection_test__",
        }

        try:
            response = session.post(
                self.api_url,
                data=json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                timeout=self.timeout,
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                headers=self._headers(post=True),
            )

            if not (200 <= response.status_code <= 399):
                error = self._http_error(response)
                return False, str(error)

            data = response.json()

            if not isinstance(data, dict):
                return False, "POST respondeu, mas o conteúdo não é JSON."

            # A ação propositalmente não existe. Se o Apps Script responder
            # UNKNOWN_ACTION, o POST chegou ao doPost() corretamente.
            code = str(data.get("code") or "").strip().upper()

            if code == "UNKNOWN_ACTION":
                return True, "Canal POST do login acessível pelo proxy."

            # Também aceitamos qualquer JSON válido do servidor: o transporte
            # chegou ao Apps Script.
            return True, "Canal POST do login respondeu corretamente."

        except requests.exceptions.ProxyError:
            return False, "O proxy recusou a conexão POST do login."

        except requests.exceptions.Timeout:
            return False, "Tempo limite no teste POST do login."

        except requests.exceptions.SSLError:
            return False, "Falha TLS no teste POST do login."

        except requests.exceptions.RequestException as exc:
            return False, str(self._network_error(exc))

        except Exception as exc:
            return False, (
                "Resposta inválida no teste POST: "
                + (str(exc) or exc.__class__.__name__)
            )

        finally:
            session.close()

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        session, _cfg, proxies, verify = self._request_context()

        try:
            response = session.post(
                self.api_url,
                data=json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                timeout=self.timeout,
                allow_redirects=True,
                proxies=proxies,
                verify=verify,
                headers=self._headers(post=True),
            )

            if not (200 <= response.status_code <= 399):
                raise self._http_error(response)

        except AuthApiError:
            raise

        except requests.exceptions.ProxyError as exc:
            raise AuthApiError(
                "Falha ao conectar através do Proxy Geral.",
                code="PROXY_ERROR",
            ) from exc

        except requests.exceptions.Timeout as exc:
            raise AuthApiError(
                "Tempo limite ao acessar o servidor de autenticação.",
                code="NETWORK_TIMEOUT",
            ) from exc

        except requests.exceptions.SSLError as exc:
            raise AuthApiError(
                "Falha na validação HTTPS.",
                code="TLS_ERROR",
            ) from exc

        except requests.exceptions.RequestException as exc:
            raise self._network_error(exc) from exc

        finally:
            session.close()

        try:
            data = response.json()
        except ValueError as exc:
            excerpt = self._safe_response_excerpt(response)

            suffix = (
                " Resposta: " + excerpt
                if excerpt
                else ""
            )

            raise AuthApiError(
                "O servidor de autenticação retornou uma resposta inválida."
                + suffix,
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
                    "action": "change_password",
                    "token": token,
                    "device_id": self.device.device_id,
                    "current_password": current_password,
                    "new_password": new_password,
                }
            )
        except AuthApiError as exc:
            if (
                exc.code == "UNKNOWN_ACTION"
                or str(exc).strip().lower() == "ação inválida."
            ):
                raise AuthApiError(
                    (
                        "O Apps Script publicado ainda é uma versão antiga e "
                        "não possui a troca de senha. Atualize o Code.gs para "
                        "a V62 e crie uma NOVA versão da implantação do Web App."
                    ),
                    code="SERVER_UPDATE_REQUIRED",
                ) from exc
            raise

        return self._session_from(data)

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
                user_data.get("must_change_password", False)
            ),
        )

        return AuthSession(
            token=token,
            expires_at=expires_at,
            user=user,
        )
