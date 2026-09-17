from monitor_noticias.app.paths import AppPaths


def test_runtime_directories_can_be_created(tmp_path) -> None:
    paths = AppPaths(tmp_path)
    paths.ensure_runtime_dirs()
    assert paths.data.is_dir()
    assert paths.logs.is_dir()
    assert paths.temp.is_dir()
