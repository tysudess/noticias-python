from __future__ import annotations

from enum import Enum
import os
from pathlib import Path
import sys


class OperatingSystem(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    OTHER = "other"


def current_operating_system() -> OperatingSystem:
    if sys.platform.startswith("win"):
        return OperatingSystem.WINDOWS

    if sys.platform.startswith("linux"):
        return OperatingSystem.LINUX

    return OperatingSystem.OTHER


def is_windows() -> bool:
    return current_operating_system() is OperatingSystem.WINDOWS


def is_linux() -> bool:
    return current_operating_system() is OperatingSystem.LINUX


def is_appimage() -> bool:
    return bool(
        is_linux()
        and os.environ.get("APPIMAGE")
    )


def appimage_original_path() -> Path | None:
    value = (
        os.environ.get("APPIMAGE")
        or ""
    ).strip()

    if not value:
        return None

    try:
        return Path(value).expanduser().resolve()
    except Exception:
        return Path(value).expanduser()


def linux_session_type() -> str:
    if not is_linux():
        return "not-linux"

    explicit = (
        os.environ.get("XDG_SESSION_TYPE")
        or ""
    ).strip().lower()

    if explicit in {"wayland", "x11"}:
        return explicit

    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"

    if os.environ.get("DISPLAY"):
        return "x11"

    return "unknown"


def platform_display_name() -> str:
    system = current_operating_system()

    if system is OperatingSystem.WINDOWS:
        return "Windows"

    if system is OperatingSystem.LINUX:
        return "Ubuntu/Linux"

    return sys.platform
