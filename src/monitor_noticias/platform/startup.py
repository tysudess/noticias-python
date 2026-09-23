from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import sys
from typing import Protocol

from .current import (
    appimage_original_path,
    is_linux,
    is_windows,
)


log = logging.getLogger(__name__)


RUN_KEY = (
    r"Software\Microsoft\Windows"
    r"\CurrentVersion\Run"
)
VALUE_NAME = "MonitorDeNoticias"
VALUE_TYPE = "REG_SZ"

LINUX_DESKTOP_FILENAME = (
    "central-inteligente-de-midia.desktop"
)


class StartupBackend(Protocol):
    def configure(
        self,
        enabled: bool,
        *,
        executable: Path | None = None,
    ) -> bool:
        ...


class RegistryBackend(Protocol):
    def set_string(
        self,
        path: str,
        name: str,
        value: str,
    ) -> None:
        ...

    def delete_value(
        self,
        path: str,
        name: str,
    ) -> None:
        ...


class WinRegBackend:
    def set_string(
        self,
        path: str,
        name: str,
        value: str,
    ) -> None:
        if not is_windows():
            return

        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(
                key,
                name,
                0,
                winreg.REG_SZ,
                value,
            )

    def delete_value(
        self,
        path: str,
        name: str,
    ) -> None:
        if not is_windows():
            return

        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                path,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(
                    key,
                    name,
                )
        except FileNotFoundError:
            pass


def startup_command(
    executable: Path,
) -> str:
    return f'"{Path(executable)}"'


def packaged_executable() -> Path | None:
    if is_linux():
        appimage = appimage_original_path()

        if appimage is not None:
            return appimage

    if not getattr(
        sys,
        "frozen",
        False,
    ):
        return None

    return Path(
        sys.executable
    ).resolve()


@dataclass(slots=True)
class WindowsStartupBackend:
    registry: RegistryBackend

    def configure(
        self,
        enabled: bool,
        *,
        executable: Path | None = None,
    ) -> bool:
        if not is_windows():
            return False

        if enabled:
            exe = (
                Path(executable)
                if executable is not None
                else packaged_executable()
            )

            if exe is None:
                log.info(
                    "Startup não alterado: executável "
                    "empacotado ainda não existe."
                )
                return False

            self.registry.set_string(
                RUN_KEY,
                VALUE_NAME,
                startup_command(
                    exe
                ),
            )

            log.info(
                "Startup habilitado em HKCU Run (%s).",
                VALUE_NAME,
            )

            return True

        self.registry.delete_value(
            RUN_KEY,
            VALUE_NAME,
        )

        log.info(
            "Startup removido de HKCU Run (%s).",
            VALUE_NAME,
        )

        return True


def _linux_autostart_dir() -> Path:
    config_home = (
        os.environ.get(
            "XDG_CONFIG_HOME"
        )
        or ""
    ).strip()

    if config_home:
        return (
            Path(config_home)
            .expanduser()
            / "autostart"
        )

    return (
        Path.home()
        / ".config"
        / "autostart"
    )


def _desktop_exec(
    executable: Path,
) -> str:
    value = str(
        Path(executable)
    ).replace(
        '"',
        '\"',
    )

    return f'"{value}"'


@dataclass(slots=True)
class LinuxAutostartBackend:
    desktop_file: Path | None = None

    def _path(self) -> Path:
        return (
            Path(self.desktop_file)
            if self.desktop_file is not None
            else (
                _linux_autostart_dir()
                / LINUX_DESKTOP_FILENAME
            )
        )

    def configure(
        self,
        enabled: bool,
        *,
        executable: Path | None = None,
    ) -> bool:
        if not is_linux():
            return False

        target = self._path()

        if not enabled:
            try:
                target.unlink()
            except FileNotFoundError:
                pass

            log.info(
                "Autostart Linux removido: %s",
                target,
            )

            return True

        exe = (
            Path(executable)
            if executable is not None
            else packaged_executable()
        )

        if exe is None:
            log.info(
                "Autostart Linux não alterado: "
                "AppImage/executável empacotado "
                "ainda não existe."
            )
            return False

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                "Name=Central Inteligente de Mídia",
                (
                    "Comment=Inicia a Central Inteligente "
                    "de Mídia automaticamente"
                ),
                "Exec=" + _desktop_exec(exe),
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        )

        target.write_text(
            content,
            encoding="utf-8",
        )

        try:
            target.chmod(
                0o644
            )
        except OSError:
            pass

        log.info(
            "Autostart Linux habilitado: %s",
            target,
        )

        return True


@dataclass(slots=True)
class UnsupportedStartupBackend:
    def configure(
        self,
        enabled: bool,
        *,
        executable: Path | None = None,
    ) -> bool:
        _ = (
            enabled,
            executable,
        )
        return False


@dataclass(slots=True)
class StartupManager:
    backend: StartupBackend

    @classmethod
    def default(
        cls,
    ) -> "StartupManager":
        if is_windows():
            return cls(
                WindowsStartupBackend(
                    WinRegBackend()
                )
            )

        if is_linux():
            return cls(
                LinuxAutostartBackend()
            )

        return cls(
            UnsupportedStartupBackend()
        )

    def configure(
        self,
        enabled: bool,
        *,
        executable: Path | None = None,
    ) -> bool:
        return self.backend.configure(
            enabled,
            executable=executable,
        )
