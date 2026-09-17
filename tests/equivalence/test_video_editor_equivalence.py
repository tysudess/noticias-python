from __future__ import annotations

from pathlib import Path

from monitor_noticias.video_editor import (
    Clip, SUPPORTED_EXTENSIONS, VideoInfo, build_export_command, clip_at_global,
    format_time, total_duration,
)


def _info(ms: int, audio: str | None = "aac") -> VideoInfo:
    return VideoInfo(ms, 1280, 720, 30.0, "h264", audio)


def test_active_editor_formats_match_baseline_exactly():
    assert SUPPORTED_EXTENSIONS == {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


def test_active_clip_model_has_only_proven_temporal_semantics(tmp_path):
    clip = Clip(tmp_path / "sample.mp4", _info(10_000))
    assert (clip.start_ms, clip.end_ms, clip.duration_ms) == (0, 10_000, 10_000)
    # O editor ativo não cria ID, thumbnail, track, efeitos ou projeto persistente.
    assert set(clip.__slots__) == {"path", "info", "start_ms", "end_ms"}


def test_multiclip_global_local_mapping_matches_baseline(tmp_path):
    clips = [
        Clip(tmp_path / "a.mp4", _info(1_500)),
        Clip(tmp_path / "b.mp4", _info(2_500)),
        Clip(tmp_path / "c.mp4", _info(500)),
    ]
    assert total_duration(clips) == 4_500
    assert clip_at_global(clips, 1_500) == (0, 1_500)
    assert clip_at_global(clips, 1_501) == (1, 1)
    assert clip_at_global(clips, 4_500) == (2, 500)


def test_export_pipeline_matches_active_pyside_baseline(tmp_path):
    ffmpeg = tmp_path / "bin" / "ffmpeg.exe"
    clip = Clip(tmp_path / "source.webm", _info(12_000, None), start_ms=500, end_ms=11_250)
    output = tmp_path / "VideoEditorExports" / "result.mp4"
    command = build_export_command(ffmpeg, clip, output)
    assert command == [
        str(ffmpeg), "-y", "-i", str(clip.path), "-ss", "0.500", "-t", "10.750",
        "-map", "0:v:0", "-map", "0:a?",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(output),
    ]


def test_format_time_matches_active_display_precision():
    assert format_time(9) == "00:00.009"
    assert format_time(10_999) == "00:10.999"
    assert format_time(3_600_001) == "01:00:00.001"


def test_absent_features_are_not_smuggled_into_core_contract():
    # A baseline ativa não possui estas operações; o teste impede que sejam
    # introduzidas silenciosamente sob o rótulo de migração equivalente.
    forbidden = {
        "split_clip", "delete_clip", "duplicate_clip", "reorder_clip",
        "undo", "redo", "timeline_zoom", "target_size", "compress",
        "set_in", "set_out", "generate_thumbnails",
    }
    import monitor_noticias.video_editor.core as core
    assert not any(hasattr(core, name) for name in forbidden)
