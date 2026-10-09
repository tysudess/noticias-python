from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "monitor_noticias" / "ui"


def test_v102_rebuilds_linux_audio_and_video_commands_without_rejected_queue_option():
    source = (UI / "screen_recorder_linux_ffmpeg_fix.py").read_text(encoding="utf-8")

    assert "def _fixed_linux_pulse_start" in source
    assert "def _fixed_linux_qt_pipe_start" in source
    assert '"-f",\n        "pulse"' in source
    assert '"-f",\n        "rawvideo"' in source
    assert '"-thread_queue_size"' not in source
    assert "install_linux_ffmpeg_input_option_fix" in source


def test_v102_fix_is_installed_before_screen_recorder_page_is_created():
    source = (UI / "screen_recorder_integration.py").read_text(encoding="utf-8")

    fix_pos = source.index("install_linux_ffmpeg_input_option_fix()")
    page_pos = source.index("page = ScreenRecorderPage(")

    assert fix_pos < page_pos
    assert "screen_recorder_linux_ffmpeg_fix" in source


def test_v102_preserves_the_linux_rawvideo_pipe_and_audio_fallback():
    source = (UI / "screen_recorder_linux_ffmpeg_fix.py").read_text(encoding="utf-8")

    assert '"-pixel_format",\n        "bgra"' in source
    assert 'f"pipe:{read_fd}"' in source
    assert "pass_fds=(read_fd,)" in source
    assert "self._first_callback_at = now" in source
