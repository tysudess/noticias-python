from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "src" / "monitor_noticias" / "ui" / "screen_recorder_linux_patch.py"
RUNTIME = ROOT / "src" / "monitor_noticias" / "ui" / "screen_recorder_linux_runtime_fix.py"
DIAG = ROOT / "portable" / "linux" / "TESTAR-PORTABLE.sh"


def test_v101_does_not_touch_display_with_ffmpeg_on_power_on():
    text = PATCH.read_text(encoding="utf-8")
    toggle_start = text.index("def _patch_toggle")
    start_segment = text.index("def _patch_start_segment")
    toggle = text[toggle_start:start_segment]

    assert "_ffmpeg_supports_libx264" in toggle
    assert "grabWindow" not in toggle
    assert "x11grab" not in toggle


def test_v101_screen_frames_come_from_qt_and_ffmpeg_only_encodes():
    text = PATCH.read_text(encoding="utf-8")

    assert "class _LinuxQtScreenPipeRecorder" in text
    assert "self.screen.grabWindow(" in text
    assert '"-f",\n            "rawvideo"' in text
    assert '"-pixel_format",\n            "bgra"' in text
    assert "pass_fds=(read_fd,)" in text
    assert "stdin=subprocess.PIPE" in text
    assert "CentralQtScreenPipe" in text


def test_v101_keeps_stdin_free_for_existing_q_stop_protocol():
    text = PATCH.read_text(encoding="utf-8")

    assert 'f"pipe:{read_fd}"' in text
    assert "pass_fds=(read_fd,)" in text
    # O vídeo usa o descritor extra; stdin permanece separado para o `q`.
    assert "stdin=subprocess.PIPE" in text


def test_v101_runtime_diagnostic_identifies_new_backend():
    text = RUNTIME.read_text(encoding="utf-8")

    assert "Central V101" in text
    assert "capture_backend=qt-screen-rawvideo-pipe" in text
    assert "ffmpeg_role=encode-only" in text


def test_v101_portable_no_longer_requires_x11grab():
    text = DIAG.read_text(encoding="utf-8")

    assert "libx264" in text
    assert "rawvideo pipe" in text
    assert "FFmpeg não precisa mais abrir o DISPLAY via x11grab" in text
    assert "timeout 8" not in text


def test_v101_post_sync_pipe_cleanup_is_installed_before_page_creation():
    integration = (
        ROOT / "src" / "monitor_noticias" / "ui" / "screen_recorder_integration.py"
    ).read_text(encoding="utf-8")
    patch = PATCH.read_text(encoding="utf-8")

    sync_pos = integration.index("install_screen_recorder_sync_patch()")
    post_pos = integration.index("install_linux_screen_recorder_post_sync_patch()")
    page_pos = integration.index("page = ScreenRecorderPage(")

    assert sync_pos < post_pos < page_pos
    assert "engine.stop()" in patch
    assert "original_finish(self)" in patch
