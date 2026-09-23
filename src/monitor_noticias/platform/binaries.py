from __future__ import annotations

from pathlib import Path
import shutil

from .current import is_windows


def binary_filename(name: str) -> str:
    clean = str(name or "").strip()

    if not clean:
        raise ValueError("Nome de binário vazio.")

    if is_windows():
        if not clean.lower().endswith(".exe"):
            return clean + ".exe"
        return clean

    if clean.lower().endswith(".exe"):
        return clean[:-4]

    return clean


def bundled_binary(
    app_root: Path,
    name: str,
) -> Path:
    return (
        Path(app_root)
        / "bin"
        / binary_filename(name)
    )


def resolve_binary(
    app_root: Path,
    name: str,
    *,
    allow_system: bool = True,
) -> Path:
    bundled = bundled_binary(
        app_root,
        name,
    )

    if bundled.is_file():
        return bundled

    if allow_system:
        found = shutil.which(
            binary_filename(name)
        )

        if found:
            return Path(found)

    return bundled
