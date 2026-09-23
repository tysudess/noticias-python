from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .current import is_linux, is_windows


PROXY_KEYRING_SERVICE = "CentralInteligenteDeMidia"
PROXY_KEYRING_ACCOUNT = "proxy-password"


class CredentialStoreUnavailable(RuntimeError):
    """O sistema não possui cofre seguro utilizável."""


class SecureTextStore(Protocol):
    def exists(self) -> bool: ...
    def save(self, text: str) -> None: ...
    def load(self) -> str: ...
    def delete(self) -> bool: ...


class KeyringApi(Protocol):
    def get_password(
        self,
        service_name: str,
        username: str,
    ) -> str | None: ...

    def set_password(
        self,
        service_name: str,
        username: str,
        password: str,
    ) -> None: ...

    def delete_password(
        self,
        service_name: str,
        username: str,
    ) -> None: ...


@dataclass(slots=True)
class LinuxKeyringTextStore:
    """Armazena senha no Secret Service/keyring da sessão Linux.

    Não existe fallback para plaintext.
    """

    service_name: str = PROXY_KEYRING_SERVICE
    account_name: str = PROXY_KEYRING_ACCOUNT
    keyring_api: KeyringApi | None = None

    def _api(self) -> KeyringApi:
        if self.keyring_api is not None:
            return self.keyring_api

        try:
            import keyring
        except Exception as exc:
            raise CredentialStoreUnavailable(
                "O módulo keyring não está disponível no Ubuntu."
            ) from exc

        try:
            backend = keyring.get_keyring()
            priority = getattr(backend, "priority", 0)

            try:
                priority_value = float(priority)
            except Exception:
                priority_value = 0.0

            backend_name = (
                f"{type(backend).__module__}."
                f"{type(backend).__name__}"
            ).lower()

            if (
                priority_value <= 0
                or ".fail." in backend_name
                or backend_name.endswith(".fail")
                or "plaintext" in backend_name
            ):
                raise CredentialStoreUnavailable(
                    "Nenhum cofre seguro Secret Service/Keyring "
                    "está disponível na sessão Linux."
                )

            return keyring

        except CredentialStoreUnavailable:
            raise
        except Exception as exc:
            raise CredentialStoreUnavailable(
                "Não foi possível acessar o cofre seguro do Linux."
            ) from exc

    def exists(self) -> bool:
        try:
            return bool(self.load())
        except CredentialStoreUnavailable:
            return False

    def save(self, text: str) -> None:
        if not text:
            self.delete()
            return

        try:
            self._api().set_password(
                self.service_name,
                self.account_name,
                text,
            )
        except CredentialStoreUnavailable:
            raise
        except Exception as exc:
            raise CredentialStoreUnavailable(
                "O cofre seguro do Linux recusou "
                "o armazenamento da senha."
            ) from exc

    def load(self) -> str:
        try:
            value = self._api().get_password(
                self.service_name,
                self.account_name,
            )
        except CredentialStoreUnavailable:
            raise
        except Exception as exc:
            raise CredentialStoreUnavailable(
                "Não foi possível ler a senha do Proxy Geral "
                "no cofre seguro do Linux."
            ) from exc

        return str(value or "")

    def delete(self) -> bool:
        api = self._api()

        try:
            current = api.get_password(
                self.service_name,
                self.account_name,
            )

            if current is None:
                return True

            api.delete_password(
                self.service_name,
                self.account_name,
            )
            return True

        except CredentialStoreUnavailable:
            raise
        except Exception as exc:
            name = exc.__class__.__name__.lower()

            if (
                "passworddelete" in name
                or "notfound" in name
            ):
                return True

            raise CredentialStoreUnavailable(
                "Não foi possível remover a senha do Proxy Geral "
                "do cofre seguro Linux."
            ) from exc


@dataclass(slots=True)
class UnsupportedSecureTextStore:
    platform_name: str

    def exists(self) -> bool:
        return False

    def save(self, text: str) -> None:
        _ = text
        raise CredentialStoreUnavailable(
            "Armazenamento seguro de credenciais "
            f"não implementado para {self.platform_name}."
        )

    def load(self) -> str:
        return ""

    def delete(self) -> bool:
        return True


def create_proxy_secret_store(
    data_dir: Path,
) -> SecureTextStore:
    if is_windows():
        from monitor_noticias.windows.dpapi import DpapiTextStore

        return DpapiTextStore(
            Path(data_dir)
            / "prefs"
            / "desktop_proxy_password.dpapi"
        )

    if is_linux():
        return LinuxKeyringTextStore()

    return UnsupportedSecureTextStore("sistema atual")


def credential_backend_label() -> str:
    if is_windows():
        return "DPAPI CurrentUser"
    if is_linux():
        return "Secret Service / Keyring"
    return "Indisponível"
