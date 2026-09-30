from __future__ import annotations

import os
from pathlib import Path
import sys

from monitor_noticias.platform.current import linux_session_type
from monitor_noticias.ui.screen_recorder_page import ScreenRecorderPage


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

        ffmpeg = Path(page.ffmpeg)
        runtime_paths = getattr(page, "_runtime_paths", None)

        if runtime_paths is not None:
            try:
                ffprobe = Path(
                    runtime_paths.runtime_binary("ffprobe")
                )
            except Exception:
                ffprobe = Path(page.app_root) / "bin" / "ffprobe"
        else:
            ffprobe = Path(page.app_root) / "bin" / "ffprobe"

        log_path.write_text(
            "\n".join(
                [
                    "Central V98 — Gravador Ubuntu",
                    f"session={linux_session_type()}",
                    f"DISPLAY={os.environ.get('DISPLAY', '')}",
                    f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')}",
                    f"XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', '')}",
                    f"bundle_root={page.app_root}",
                    f"logs_dir={page.logs_dir}",
                    f"ffmpeg={ffmpeg}",
                    f"ffmpeg_exists={ffmpeg.is_file()}",
                    f"ffmpeg_executable={os.access(ffmpeg, os.X_OK)}",
                    f"ffprobe={ffprobe}",
                    f"ffprobe_exists={ffprobe.is_file()}",
                    f"ffprobe_executable={os.access(ffprobe, os.X_OK)}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def install_screen_recorder_linux_runtime_fix() -> None:
    """Reaplica os binários do bundle depois do patch A/V V95.

    A implementação original da página recebe no Linux a raiz gravável para os
    diretórios de dados. O patch A/V V95 voltava a resolver ``bin/ffmpeg`` a
    partir dessa raiz e podia apontar para um arquivo inexistente. O bundle real
    continua sendo a fonte de FFmpeg/FFprobe; logs/temp/vídeos permanecem no
    state_root gravável.
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
                ffmpeg = bundle_root / "bin" / "ffmpeg"
        else:
            ffmpeg = bundle_root / "bin" / "ffmpeg"

        self.app_root = bundle_root
        self.ffmpeg = ffmpeg

        _write_runtime_diagnostic(self)

    patched_init._central_linux_runtime_v98 = True
    cls.__init__ = patched_init

    _INSTALLED = True
