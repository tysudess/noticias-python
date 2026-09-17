from pathlib import Path
from monitor_noticias.app.paths import AppPaths, resolve_app_root

def test_project_root_is_repository_root() -> None:
    root = resolve_app_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "monitor_noticias").is_dir()
def test_expected_paths_are_relative_to_root() -> None:
    paths = AppPaths.discover()
    assert paths.resources == paths.root / "resources"
    assert paths.data == paths.root / "data"
    assert paths.bin == paths.root / "bin"
    assert paths.logs == paths.root / "logs"
    assert paths.temp == paths.root / "temp"
    assert paths.news_db == paths.root / "data" / "news.db"
    assert paths.videos_db == paths.root / "data" / "videos.db"
    assert paths.ffmpeg == paths.root / "bin" / "ffmpeg.exe"
    assert paths.ffprobe == paths.root / "bin" / "ffprobe.exe"
def test_root_does_not_depend_on_current_working_directory(tmp_path: Path, monkeypatch) -> None:
    expected = resolve_app_root()
    monkeypatch.chdir(tmp_path)
    assert resolve_app_root() == expected
