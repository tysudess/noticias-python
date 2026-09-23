from pathlib import Path

from monitor_noticias.app.paths import (
    AppPaths,
    resolve_app_root,
)
from monitor_noticias.platform.current import (
    is_windows,
)


def test_project_root_is_repository_root() -> None:
    root = resolve_app_root()

    assert (
        root
        / "pyproject.toml"
    ).is_file()

    assert (
        root
        / "src"
        / "monitor_noticias"
    ).is_dir()


def test_expected_paths_are_relative_to_root() -> None:
    paths = AppPaths.discover()

    assert (
        paths.resources
        == paths.root
        / "resources"
    )

    assert (
        paths.bin
        == paths.root
        / "bin"
    )

    assert (
        paths.data
        == Path(paths.state_root)
        / "data"
    )

    assert (
        paths.logs
        == Path(paths.state_root)
        / "logs"
    )

    assert (
        paths.temp
        == Path(paths.state_root)
        / "temp"
    )

    assert (
        paths.news_db
        == paths.data
        / "news.db"
    )

    assert (
        paths.videos_db
        == paths.data
        / "videos.db"
    )

    ffmpeg_name = (
        "ffmpeg.exe"
        if is_windows()
        else "ffmpeg"
    )

    ffprobe_name = (
        "ffprobe.exe"
        if is_windows()
        else "ffprobe"
    )

    assert (
        paths.ffmpeg
        == paths.root
        / "bin"
        / ffmpeg_name
    )

    assert (
        paths.ffprobe
        == paths.root
        / "bin"
        / ffprobe_name
    )


def test_manual_paths_keep_portable_behavior(
    tmp_path: Path,
) -> None:
    paths = AppPaths(
        tmp_path
    )

    assert (
        paths.state_root
        == tmp_path
    )

    paths.ensure_runtime_dirs()

    assert paths.data.is_dir()
    assert paths.logs.is_dir()
    assert paths.temp.is_dir()


def test_root_does_not_depend_on_current_working_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    expected = resolve_app_root()

    monkeypatch.chdir(
        tmp_path
    )

    assert (
        resolve_app_root()
        == expected
    )
