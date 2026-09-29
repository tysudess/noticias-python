def test_windows_startup_compatibility_module_exports_backend():
    from monitor_noticias.platform.startup import (
        WindowsStartupBackend as PlatformWindowsStartupBackend,
    )
    from monitor_noticias.windows.startup import (
        WindowsStartupBackend as CompatWindowsStartupBackend,
    )

    assert CompatWindowsStartupBackend is PlatformWindowsStartupBackend
