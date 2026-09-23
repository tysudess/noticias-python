from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from .current import (
    is_linux,
    is_windows,
)


def open_path(
    path: Path,
) -> bool:
    """Abre arquivo/pasta usando o desktop do sistema."""

    target = Path(
        path
    ).expanduser()

    try:
        if is_windows():
            os.startfile(  # type: ignore[attr-defined]
                str(target)
            )
            return True

        if is_linux():
            subprocess.Popen(
                [
                    "xdg-open",
                    str(target),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True

        if sys.platform == "darwin":
            subprocess.Popen(
                [
                    "open",
                    str(target),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True

    except Exception:
        return False

    return False
