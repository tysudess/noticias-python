"""Compatibilidade histórica para inicialização automática.

O backend real agora é escolhido por:
    monitor_noticias.platform.startup
"""

from monitor_noticias.platform.startup import (
    LINUX_DESKTOP_FILENAME,
    RUN_KEY,
    VALUE_NAME,
    VALUE_TYPE,
    LinuxAutostartBackend,
    RegistryBackend,
    StartupManager,
    WinRegBackend,
    packaged_executable,
    startup_command,
)

__all__ = [
    "LINUX_DESKTOP_FILENAME",
    "RUN_KEY",
    "VALUE_NAME",
    "VALUE_TYPE",
    "LinuxAutostartBackend",
    "RegistryBackend",
    "StartupManager",
    "WinRegBackend",
    "packaged_executable",
    "startup_command",
]
