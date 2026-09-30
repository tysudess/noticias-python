from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(
        encoding="utf-8"
    )


def test_v95_is_installed_before_screen_recorder_page_is_created():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_integration.py"
    )

    install_pos = source.index(
        "install_screen_recorder_sync_patch()"
    )
    page_pos = source.index(
        "page = ScreenRecorderPage("
    )

    assert install_pos < page_pos


def test_v95_stops_audio_before_waiting_for_video_shutdown():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    start = source.index(
        "def patched_finish_current_segment("
    )
    end = source.index(
        "def patched_probe_duration("
    )
    block = source[start:end]

    audio_stop = block.index(
        "request_stop()"
    )
    video_stop = block.index(
        'process.stdin.write(\n                        b"q\\n"'
    )
    wait_video = block.index(
        "process.wait("
    )
    close_audio = block.index(
        "self._stop_audio_engine()"
    )

    assert audio_stop < video_stop
    assert video_stop < wait_video
    assert wait_video < close_audio


def test_v95_does_not_fit_audio_to_video_using_whole_wav_duration():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    # Regressão antiga:
    # tempo_factor = effective_audio / desired_content
    assert "effective_audio / desired_content" not in source
    assert "audio_duration - lead_trim" not in source

    # A correção de clock passa a comparar amostras com relógio real.
    assert "sample / wall" in source
    assert "MAX_APPLIED_CLOCK_CORRECTION = 0.005" in source


def test_v95_aligns_start_then_pads_or_trims_without_stretching_tail():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    assert 'f"atrim=start={lead_trim:.6f}"' in source
    assert 'f"adelay={delay_values}"' in source
    assert '"apad"' in source
    assert 'f"atrim=duration={duration:.6f}"' in source


def test_v95_reencodes_only_audio_when_concatenating_segments():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    assert '"-c:v",\n                        "copy"' in source
    assert '"-c:a",\n                        "aac"' in source
    assert (
        '"aresample=48000:async=1:first_pts=0"'
        in source
    )


def test_v95_uses_ffprobe_on_windows_and_linux():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    assert 'root / "bin" / "ffprobe.exe"' in source
    assert 'root / "bin" / "ffprobe"' in source
    assert 'root / "bin" / "ffmpeg.exe"' in source
    assert 'root / "bin" / "ffmpeg"' in source


def test_v95_has_final_av_quality_control_and_repair():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    assert "SYNC_WARNING_SECONDS = 0.180" in source
    assert "_probe_stream_durations" in source
    assert "_repair_final_duration" in source
    assert "[A/V SYNC V95]" in source


def test_v95_first_wasapi_buffer_is_accounted_for_only_when_callback_exists():
    source = _read(
        "src/monitor_noticias/ui/screen_recorder_sync_patch.py"
    )

    assert "recorder.first_callback_at is not None" in source
    assert "1024.0" in source
    assert "recorder.device.rate" in source
