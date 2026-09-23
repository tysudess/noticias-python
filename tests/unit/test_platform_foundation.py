from pathlib import Path

from monitor_noticias.platform.binaries import (
    binary_filename,
)
from monitor_noticias.platform.current import (
    is_windows,
)
from monitor_noticias.platform.startup import (
    RUN_KEY,
    VALUE_NAME,
    startup_command,
)


def test_binary_extension_matches_platform() -> None:
    if is_windows():
        assert (
            binary_filename("ffmpeg")
            == "ffmpeg.exe"
        )
    else:
        assert (
            binary_filename("ffmpeg")
            == "ffmpeg"
        )

        assert (
            binary_filename("ffmpeg.exe")
            == "ffmpeg"
        )


def test_windows_registry_contract_is_preserved() -> None:
    assert (
        RUN_KEY
        == (
            r"Software\Microsoft\Windows"
            r"\CurrentVersion\Run"
        )
    )

    assert VALUE_NAME == "MonitorDeNoticias"

    exe = Path(
        r"C:\Apps\Monitor De Noticias"
        r"\MonitorDeNoticias.exe"
    )

    assert (
        startup_command(exe)
        == (
            '"C:\\Apps\\Monitor De Noticias'
            '\\MonitorDeNoticias.exe"'
        )
    )
