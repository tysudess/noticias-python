from __future__ import annotations

import os
from pathlib import Path
import sys

from monitor_noticias.platform.current import (
    linux_session_type,
)
from monitor_noticias.ui.screen_recorder_page import (
    ScreenRecorderPage,
)


_INSTALLED = False


def _write_runtime_diagnostic(page) -> None:
    try:
        log_path = (
            Path(page.logs_dir)
            / "screen_recorder_linux_runtime.log"
        )
        log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ffprobe = (
            Path(page.app_root)
            / "bin"
            / "ffprobe"
        )

        log_path.write_text(
            "\n".join(
                [
                    "Central V97 — Gravador Ubuntu",
                    f"session={linux_session_type()}",
                    f"DISPLAY={os.environ.get('DISPLAY', '')}",
                    f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')}",
                    f"bundle_root={page.app_root}",
                    f"ffmpeg={page.ffmpeg}",
                    f"ffmpeg_exists={Path(page.ffmpeg).is_file()}",
                    f"ffprobe={ffprobe}",
                    f"ffprobe_exists={ffprobe.is_file()}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def install_screen_recorder_linux_runtime_fix() -> None:
    """Reaplica os binários do bundle depois do patch A/V V95.

    No Linux, linux_boot_patch cria diretórios graváveis usando state_root e
    depois aponta FFmpeg para o bundle. A V95 voltava a resolver FFmpeg usando
    self.app_root (state_root), sobrescrevendo o caminho correto com um
    `.../bin/ffmpeg` inexistente.

    Este patch é instalado DEPOIS da V95 e corrige apenas Linux.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    cls = ScreenRecorderPage
    original_init = cls.__init__

    def patched_init(
        self,
        *args,
        **kwargs,
    ) -> None:
        original_init(
            self,
            *args,
            **kwargs,
        )

        runtime_paths = getattr(
            self,
            "_runtime_paths",
            None,
        )

        bundle_root = Path(
            getattr(
                self,
                "_bundle_root",
                args[0] if args else self.app_root,
            )
        )

        if runtime_paths is not None:
            try:
                ffmpeg = Path(
                    runtime_paths.runtime_binary(
                        "ffmpeg"
                    )
                )
            except Exception:
                ffmpeg = (
                    bundle_root
                    / "bin"
                    / "ffmpeg"
                )
        else:
            ffmpeg = (
                bundle_root
                / "bin"
                / "ffmpeg"
            )

        # Importante: os diretórios de gravação/log/temp já foram definidos
        # durante __init__ para o state_root gravável. Alterar app_root aqui
        # só corrige as consultas V95 a bin/ffmpeg e bin/ffprobe.
        self.app_root = bundle_root
        self.ffmpeg = ffmpeg

        _write_runtime_diagnostic(
            self
        )

    patched_init._central_linux_runtime_v97 = True
    cls.__init__ = patched_init

    _INSTALLED = True
