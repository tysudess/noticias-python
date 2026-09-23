from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import socket
import uuid

from monitor_noticias.app.paths import AppPaths


APP_NAMESPACE = (
    "CentralInteligenteDeMidia"
)


@dataclass(
    frozen=True,
    slots=True,
)
class DeviceIdentity:
    device_id: str
    device_name: str
    os_name: str


def _windows_machine_guid() -> str:
    if os.name != "nt":
        return ""

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            (
                r"SOFTWARE\Microsoft"
                r"\Cryptography"
            ),
        ) as key:
            value, _ = (
                winreg.QueryValueEx(
                    key,
                    "MachineGuid",
                )
            )

        return str(
            value
            or ""
        ).strip()

    except Exception:
        return ""


def _linux_machine_id() -> str:
    for candidate in (
        Path(
            "/etc/machine-id"
        ),
        Path(
            "/var/lib/dbus/machine-id"
        ),
    ):
        try:
            value = (
                candidate.read_text(
                    encoding="utf-8"
                )
                .strip()
            )

            if value:
                return value

        except Exception:
            pass

    return ""


def _fallback_id(
    paths: AppPaths,
) -> str:
    target = (
        paths.data
        / "auth"
        / "device_id.txt"
    )

    try:
        if target.is_file():
            value = (
                target.read_text(
                    encoding="utf-8"
                )
                .strip()
            )

            if value:
                return value

        value = uuid.uuid4().hex

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            value,
            encoding="utf-8",
        )

        return value

    except Exception:
        return (
            socket.gethostname()
            + "|"
            + platform.platform()
        )


def _raw_machine_id(
    paths: AppPaths,
) -> str:
    return (
        _windows_machine_guid()
        or _linux_machine_id()
        or _fallback_id(
            paths
        )
    )


def current_device_identity(
    paths: AppPaths,
) -> DeviceIdentity:
    raw = _raw_machine_id(
        paths
    )

    digest = hashlib.sha256(
        (
            APP_NAMESPACE
            + "|"
            + raw
        ).encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()

    name = (
        socket.gethostname()
        or platform.node()
        or "Computador"
    )

    return DeviceIdentity(
        device_id=digest,
        device_name=name[:120],
        os_name=(
            platform.platform()
            or platform.system()
            or os.name
        )[:120],
    )
