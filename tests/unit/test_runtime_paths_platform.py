from pathlib import Path

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.binaries import (
    binary_filename,
)


def test_explicit_root_keeps_portable_layout(
    tmp_path: Path,
) -> None:
    paths = AppPaths.for_app_root(
        tmp_path
    )

    assert paths.root == tmp_path
    assert paths.state_root == tmp_path
    assert paths.videos == tmp_path / "Videos"
    assert (
        paths.video_editor_exports
        == tmp_path
        / "VideoEditorExports"
    )


def test_user_binary_overrides_bundled_binary(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    state = tmp_path / "state"

    bundle_bin = bundle / "bin"
    state_bin = state / "bin"

    bundle_bin.mkdir(
        parents=True
    )
    state_bin.mkdir(
        parents=True
    )

    name = binary_filename(
        "yt-dlp"
    )

    bundled = bundle_bin / name
    override = state_bin / name

    bundled.write_bytes(b"bundle")

    paths = AppPaths(
        bundle,
        state,
    )

    assert (
        paths.runtime_binary(
            "yt-dlp",
            allow_system=False,
        )
        == bundled
    )

    override.write_bytes(
        b"override"
    )

    assert (
        paths.runtime_binary(
            "yt-dlp",
            allow_system=False,
        )
        == override
    )

    assert (
        paths.writable_binary(
            "yt-dlp"
        )
        == override
    )
