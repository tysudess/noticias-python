from __future__ import annotations

import platform
import sys


APP_DISPLAY_NAME = "Central Inteligente de Mídia"
APP_VERSION = "4.0.2"


def platform_name() -> str:
    if sys.platform.startswith("win"):
        return "Windows Portable"
    if sys.platform.startswith("linux"):
        return "Ubuntu Portable"

    name = platform.system().strip() or "Desktop"
    return f"{name} Portable"


def platform_version_label() -> str:
    return f"{platform_name()} v{APP_VERSION}"
