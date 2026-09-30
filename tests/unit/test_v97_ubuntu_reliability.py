from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(
        encoding="utf-8"
    )


def test_linux_chromium_flags_are_set_before_qt_import():
    source = _read(
        "src/monitor_noticias/app/application.py"
    )

    call_pos = source.index(
        "_install_linux_runtime_environment()"
    )
    qt_pos = source.index(
        "from PySide6.QtWidgets import"
    )

    assert call_pos < qt_pos
    assert "--disable-gpu" in source
    assert "--disable-gpu-compositing" in source
    assert "--disable-dev-shm-usage" in source
    assert "QTWEBENGINE_DISABLE_SANDBOX" not in source


def test_covers_linux_browser_is_offscreen_without_negative_geometry():
    source = _read(
        "src/monitor_noticias/ui/covers_linux_stability_patch.py"
    )

    assert "WA_DontShowOnScreen" in source
    assert "ParallelCentralClippingResolver" in source
    assert "MAX_CONCURRENT_NEWSPAPERS = 1" in source
    assert "WebGLEnabled" in source
    assert "Accelerated2dCanvasEnabled" in source

    # Regressão anterior usava uma janela top-level gigante em x=-5000.
    assert "QRect(-5000" not in source


def test_covers_linux_stability_is_installed_before_proxy_browser_wrapper():
    source = _read(
        "src/monitor_noticias/app/application.py"
    )

    stable_pos = source.index(
        "install_covers_linux_stability_patch()"
    )
    proxy_pos = source.index(
        "install_covers_web_proxy_patch()"
    )

    assert stable_pos < proxy_pos


def test_linux_auth_warmup_is_restricted_to_corporate_proxy():
    source = _read(
        "src/monitor_noticias/auth/linux_auth_transport_patch.py"
    )

    assert 'sys.platform.startswith("linux")' in source
    assert "corporate_tls_compatibility(cfg)" in source
    assert "_linux_auth_warm_attempted" in source
    assert "timeout=(2.5, 4.0)" in source

    # O warm-up não pode enviar identidade, senha ou token.
    warm_start = source.index(
        "def _warm_auth_server_once("
    )
    warm_end = source.index(
        "def install_linux_auth_transport_patch("
    )
    warm = source[warm_start:warm_end]

    assert '"username"' not in warm
    assert '"password"' not in warm
    assert '"token"' not in warm


def test_linux_auth_patch_keeps_real_login_and_validate_after_warmup():
    source = _read(
        "src/monitor_noticias/auth/linux_auth_transport_patch.py"
    )

    assert "original_login(" in source
    assert "original_validate(" in source
    assert "_warm_auth_server_once(self)" in source


def test_v97_installs_runtime_fix_after_v95_and_before_page_creation():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_integration.py"
    )

    sync_pos = source.index(
        "install_screen_recorder_sync_patch()"
    )
    runtime_pos = source.index(
        "install_screen_recorder_linux_runtime_fix()"
    )
    page_pos = source.index(
        "page = ScreenRecorderPage("
    )

    assert sync_pos < runtime_pos < page_pos


def test_linux_recorder_restores_bundle_ffmpeg_after_v95():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_linux_runtime_fix.py"
    )

    assert 'runtime_paths.runtime_binary(' in source
    assert '"ffmpeg"' in source
    assert "self.app_root = bundle_root" in source
    assert "self.ffmpeg = ffmpeg" in source

    # O diagnóstico permite confirmar X11/Wayland e os binários no PC real.
    assert "screen_recorder_linux_runtime.log" in source
    assert "linux_session_type()" in source
    assert "WAYLAND_DISPLAY" in source
    assert "ffprobe_exists" in source


def test_v97_does_not_claim_or_force_wayland_as_x11():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_linux_runtime_fix.py"
    )

    assert 'XDG_SESSION_TYPE' not in source
    assert 'os.environ["XDG_SESSION_TYPE"]' not in source
