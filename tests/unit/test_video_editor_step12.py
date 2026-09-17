from __future__ import annotations

import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QApplication, QPushButton

from monitor_noticias.video_editor import (
    Clip, SUPPORTED_EXTENSIONS, VideoInfo, build_export_command, clip_at_global,
    export_output_path, format_time, global_start_for_clip, parse_fps, probe_video,
    seconds_arg, total_duration,
)
from monitor_noticias.video_editor.timeline import TimelineWidget
from monitor_noticias.video_editor.window import VideoEditorWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def info(duration: int, audio: str | None = "aac") -> VideoInfo:
    return VideoInfo(duration, 1920, 1080, 29.97, "h264", audio)


def test_supported_extensions_are_exactly_the_release_contract():
    assert SUPPORTED_EXTENSIONS == {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


def test_time_format_seconds_and_fps_contract():
    assert format_time(0) == "00:00.000"
    assert format_time(61_234) == "01:01.234"
    assert format_time(3_661_007) == "01:01:01.007"
    assert seconds_arg(1234) == "1.234"
    assert parse_fps("30000/1001") == pytest.approx(29.97002997)
    assert parse_fps("0/0") == 0.0


def test_clip_defaults_to_entire_source_and_duration_is_milliseconds(tmp_path):
    clip = Clip(tmp_path / "a.mp4", info(12_345))
    assert clip.start_ms == 0
    assert clip.end_ms == 12_345
    assert clip.duration_ms == 12_345


def test_global_local_mapping_preserves_release_boundary_rule(tmp_path):
    clips = [Clip(tmp_path / "a.mp4", info(1_000)), Clip(tmp_path / "b.mp4", info(2_000))]
    assert total_duration(clips) == 3_000
    assert global_start_for_clip(clips, 0) == 0
    assert global_start_for_clip(clips, 1) == 1_000
    assert clip_at_global(clips, 0) == (0, 0)
    assert clip_at_global(clips, 999) == (0, 999)
    # O source ativo usa <=: o limite exato ainda pertence ao clipe anterior.
    assert clip_at_global(clips, 1_000) == (0, 1_000)
    assert clip_at_global(clips, 1_001) == (1, 1)
    assert clip_at_global(clips, 3_000) == (1, 2_000)


def test_probe_video_uses_exact_ffprobe_shape(monkeypatch, tmp_path):
    video = tmp_path / "a.mp4"; video.write_bytes(b"x")
    ffprobe = tmp_path / "ffprobe.exe"; ffprobe.write_bytes(b"x")
    payload = {"format": {"duration": "2.5"}, "streams": [
        {"codec_type":"video","codec_name":"h264","width":1280,"height":720,"avg_frame_rate":"25/1","duration":"2.4"},
        {"codec_type":"audio","codec_name":"aac"},
    ]}
    seen = {}
    def fake_run(command, **kwargs):
        seen["command"] = command; seen["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
    monkeypatch.setattr("monitor_noticias.video_editor.core.subprocess.run", fake_run)
    result = probe_video(video, ffprobe)
    assert seen["command"] == [str(ffprobe), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video)]
    assert seen["kwargs"]["timeout"] == 60
    assert result.duration_ms == 2500 and result.width == 1280 and result.height == 720
    assert result.fps == 25.0 and result.video_codec == "h264" and result.audio_codec == "aac"


def test_probe_without_ffprobe_preserves_original_zero_info(tmp_path):
    result = probe_video(tmp_path / "a.mp4", tmp_path / "missing.exe")
    assert result == VideoInfo(0, 0, 0, 0.0, "video", None)


def test_export_command_is_literal_release_pipeline(tmp_path):
    clip = Clip(tmp_path / "input.mkv", info(20_000), start_ms=1_250, end_ms=8_750)
    out = export_output_path(tmp_path / "VideoEditorExports", clip)
    assert out.name == "input_corte_00-01-250_00-08-750.mp4"
    cmd = build_export_command(tmp_path / "bin" / "ffmpeg.exe", clip, out)
    assert cmd == [
        str(tmp_path / "bin" / "ffmpeg.exe"), "-y", "-i", str(clip.path),
        "-ss", "1.250", "-t", "7.500", "-map", "0:v:0", "-map", "0:a?",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out),
    ]


def test_timeline_math_is_proportional_and_click_only(app, tmp_path):
    widget = TimelineWidget(); widget.resize(1000, 170)
    widget.set_clips([Clip(tmp_path/"a.mp4", info(1000)), Clip(tmp_path/"b.mp4", info(3000))])
    left = widget._timeline_rect().left(); right = widget._timeline_rect().right()
    assert widget._x_for_time(0) == pytest.approx(left)
    assert widget._x_for_time(4000) == pytest.approx(right)
    assert widget._time_for_x(widget._x_for_time(1000)) == pytest.approx(1000, abs=1)
    widget.deleteLater()


def test_window_uses_qmediaplayer_qvideowidget_audio_085_and_active_controls(app, tmp_path):
    window = VideoEditorWindow(tmp_path)
    assert isinstance(window.player, QMediaPlayer)
    assert isinstance(window.video_widget, QVideoWidget)
    assert window.audio.volume() == pytest.approx(0.85, abs=.01)
    texts = {b.text() for b in window.findChildren(QPushButton)}
    for required in {"▭  Abrir Vídeo", "▶", "◀ 5s", "5s ▶", "🔊", "✂  Exportar trecho", "Cortar Vídeo"}:
        assert required in texts
    # Recursos visíveis mas deliberadamente placeholder no motor aprovado.
    for placeholder in {"Unir Vídeos", "Extrair", "Compactar", "Converter"}:
        assert placeholder in texts
    # Recursos que não existem no editor ativo não são inventados pela migração.
    assert not any(x in texts for x in {"Dividir", "Duplicar", "Excluir clipe", "Desfazer", "Refazer", "Stop"})
    window.close(); window.deleteLater()
