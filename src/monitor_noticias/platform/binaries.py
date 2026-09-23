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


def writable_binary(
    app_root: Path,
    state_root: Path,
    name: str,
) -> Path:
    """Caminho onde um binário atualizável pode ser gravado.

    Windows Portable:
        state_root == app_root, portanto continua em bin/.

    AppImage:
        o bundle é somente leitura; atualizações ficam em
        Central-Inteligente-de-Midia-Data/bin/.
    """

    app_root = Path(app_root)
    state_root = Path(state_root)

    if state_root == app_root:
        return bundled_binary(
            app_root,
            name,
        )

    return (
        state_root
        / "bin"
        / binary_filename(name)
    )


def resolve_binary(
    app_root: Path,
    name: str,
    *,
    state_root: Path | None = None,
    allow_system: bool = True,
) -> Path:
    """Resolve binário pela ordem:

    1. override gravável do usuário (AppImage);
    2. binário incluído no bundle;
    3. PATH do sistema, apenas como fallback de desenvolvimento.
    """

    app_root = Path(app_root)

    if state_root is not None:
        override = writable_binary(
            app_root,
            Path(state_root),
            name,
        )

        bundled = bundled_binary(
            app_root,
            name,
        )

        if (
            override != bundled
            and override.is_file()
        ):
            return override

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


def platform_tool_name(
    windows_name: str,
    linux_name: str | None = None,
) -> str:
    if is_windows():
        return windows_name

    if linux_name:
        return linux_name

    if windows_name.lower().endswith(".exe"):
        return windows_name[:-4]

    return windows_name
