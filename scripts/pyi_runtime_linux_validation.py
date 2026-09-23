from __future__ import annotations

import json
import os
from pathlib import Path
import sys


if os.environ.get(
    "CENTRAL_LINUX_SMOKE"
) == "1":
    result = {
        "python": sys.version,
        "platform": sys.platform,
        "imports": {},
    }

    modules = [
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtMultimedia",
        "PySide6.QtWebEngineCore",
        "requests",
        "bs4",
        "lxml",
        "pypdf",
        "pypdfium2",
        "PIL",
        "keyring",
        "secretstorage",
        "monitor_noticias.app.paths",
        "monitor_noticias.networking.proxy",
        "monitor_noticias.ui.screen_recorder_linux",
    ]

    ok = True

    for name in modules:
        try:
            __import__(name)
            result["imports"][name] = "ok"
        except Exception as exc:
            ok = False
            result["imports"][name] = (
                f"{exc.__class__.__name__}: {exc}"
            )

    output = (
        os.environ.get(
            "CENTRAL_LINUX_SMOKE_OUTPUT"
        )
        or ""
    ).strip()

    if output:
        try:
            path = Path(output)
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            ok = False

    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )

    os._exit(
        0 if ok else 91
    )
