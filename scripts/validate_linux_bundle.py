from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def fail(
    message: str,
) -> None:
    print(
        "ERRO:",
        message,
        file=sys.stderr,
    )
    raise SystemExit(1)


def check_executable(
    path: Path,
) -> None:
    if not path.is_file():
        fail(
            f"Arquivo ausente: {path}"
        )

    if not os.access(
        path,
        os.X_OK,
    ):
        fail(
            f"Arquivo sem permissão de execução: {path}"
        )


def main() -> int:
    if len(sys.argv) != 2:
        fail(
            "Uso: validate_linux_bundle.py <raiz>"
        )

    root = Path(
        sys.argv[1]
    ).resolve()

    check_executable(
        root
        / "CentralInteligenteDeMidia"
    )

    for name in (
        "ffmpeg",
        "ffprobe",
        "yt-dlp",
        "deno",
    ):
        check_executable(
            root
            / "bin"
            / name
        )

    helper = (
        root
        / "resources"
        / "globoplay-login-helper"
        / "GloboplayLoginHelper"
    )
    check_executable(
        helper
    )

    news_launcher = (
        root
        / "tools"
        / "news_extractor"
        / "ExtratorMateriasPortable-V1.25.19"
    )
    check_executable(
        news_launcher
    )

    runtime = (
        root
        / "tools"
        / "news_extractor"
        / "runtime"
    )

    if (
        not runtime.is_dir()
        or not any(
            runtime.iterdir()
        )
    ):
        fail(
            "Runtime Electron Linux ausente."
        )

    version_commands = [
        (
            root
            / "bin"
            / "ffmpeg",
            ["-version"],
        ),
        (
            root
            / "bin"
            / "ffprobe",
            ["-version"],
        ),
        (
            root
            / "bin"
            / "yt-dlp",
            ["--version"],
        ),
        (
            root
            / "bin"
            / "deno",
            ["--version"],
        ),
    ]

    for executable, args in version_commands:
        cp = subprocess.run(
            [
                str(
                    executable
                ),
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

        if cp.returncode != 0:
            fail(
                f"Falha ao executar {executable.name}: "
                f"{cp.stdout[-1200:]}"
            )

        print(
            executable.name,
            "OK",
        )

    print(
        "Bundle Linux validado."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
