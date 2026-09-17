def test_base_modules_import() -> None:
    import monitor_noticias
    from monitor_noticias.app.config import AppConfig
    from monitor_noticias.app.paths import AppPaths

    assert monitor_noticias.__version__ == "0.0.1"
    assert AppConfig() is not None
    assert AppPaths.discover().root.is_dir()
