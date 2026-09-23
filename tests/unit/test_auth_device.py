from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.auth.device import (
    current_device_identity,
)


def test_device_identity_is_stable(
    tmp_path: Path,
) -> None:
    paths = AppPaths(
        tmp_path
    )

    first = current_device_identity(
        paths
    )

    second = current_device_identity(
        paths
    )

    assert first.device_id
    assert first.device_id == second.device_id
    assert len(first.device_id) == 64
