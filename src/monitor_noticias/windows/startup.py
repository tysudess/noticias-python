from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import sys
from typing import Protocol

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "MonitorDeNoticias"
VALUE_TYPE = "REG_SZ"


class RegistryBackend(Protocol):
    def set_string(self, path: str, name: str, value: str) -> None: ...
    def delete_value(self, path: str, name: str) -> None: ...


class WinRegBackend:
    def set_string(self, path: str, name: str, value: str) -> None:
        if os.name != "nt":
            return
        import winreg
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def delete_value(self, path: str, name: str) -> None:
        if os.name != "nt":
            return
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass


def startup_command(executable: Path) -> str:
    return f'"{Path(executable)}"'


def packaged_executable() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve()


@dataclass(slots=True)
class StartupManager:
    backend: RegistryBackend

    @classmethod
    def default(cls) -> "StartupManager":
        return cls(WinRegBackend())

    def configure(self, enabled: bool, *, executable: Path | None = None) -> bool:
        if os.name != "nt" and isinstance(self.backend, WinRegBackend):
            return False
        if enabled:
            exe = Path(executable) if executable is not None else packaged_executable()
            if exe is None:
                log.info("Startup não alterado: executável empacotado ainda não existe.")
                return False
            self.backend.set_string(RUN_KEY, VALUE_NAME, startup_command(exe))
            log.info("Startup habilitado em HKCU Run (%s).", VALUE_NAME)
            return True
        self.backend.delete_value(RUN_KEY, VALUE_NAME)
        log.info("Startup removido de HKCU Run (%s).", VALUE_NAME)
        return True
