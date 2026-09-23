from monitor_noticias.ui.linux_boot_patch import (
    runtime_platform_label,
)
from monitor_noticias.platform.current import (
    is_linux,
    is_windows,
)


def test_runtime_platform_label_is_not_empty():
    value = runtime_platform_label()

    assert value

    if is_windows():
        assert "Windows" in value

    if is_linux():
        assert (
            "Ubuntu" in value
            or "Linux" in value
        )
