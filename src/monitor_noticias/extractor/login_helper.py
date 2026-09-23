from __future__ import annotations

from pathlib import Path
import shutil

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.current import is_windows


MIN_HELPER_SIZE = 20_000_000


def helper_filename() -> str:
    return (
        "GloboplayLoginHelper.exe"
        if is_windows()
        else "GloboplayLoginHelper"
    )


def resource_relative() -> Path:
    return (
        Path("resources")
        / "globoplay-login-helper"
        / helper_filename()
    )


def runtime_relative() -> Path:
    return (
        Path("data")
        / "extractor"
        / "runtime"
        / helper_filename()
    )


def resolve_bundled_helper(
    app_root: Path,
) -> Path:
    """Materializa o helper do Globoplay fora do bundle somente leitura.

    Windows Portable:
        resources/.../GloboplayLoginHelper.exe
        -> data/extractor/runtime/GloboplayLoginHelper.exe

    Ubuntu/AppImage:
        resources/.../GloboplayLoginHelper
        -> Central-Inteligente-de-Midia-Data/
           data/extractor/runtime/GloboplayLoginHelper
    """

    paths = AppPaths.for_app_root(
        Path(app_root)
    )

    source = (
        paths.root
        / resource_relative()
    )

    if not source.is_file():
        raise FileNotFoundError(
            "Recurso do navegador interno do Globoplay ausente: "
            f"{source}"
        )

    if source.stat().st_size <= MIN_HELPER_SIZE:
        raise RuntimeError(
            "Navegador interno do Globoplay foi "
            "extraído de forma incompleta."
        )

    target = (
        Path(paths.state_root)
        / runtime_relative()
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with source.open(
        "rb"
    ) as input_file, target.open(
        "wb"
    ) as output_file:
        shutil.copyfileobj(
            input_file,
            output_file,
        )

    if (
        not target.is_file()
        or target.stat().st_size
        <= MIN_HELPER_SIZE
    ):
        raise RuntimeError(
            "Navegador interno do Globoplay foi "
            "materializado de forma incompleta."
        )

    if not is_windows():
        try:
            target.chmod(
                target.stat().st_mode
                | 0o111
            )
        except OSError:
            pass

    return target
