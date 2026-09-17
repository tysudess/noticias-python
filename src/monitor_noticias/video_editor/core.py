from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}


@dataclass(slots=True)
class VideoInfo:
    duration_ms: int
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: Optional[str]

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_codec)


@dataclass(slots=True)
class Clip:
    path: Path
    info: VideoInfo
    start_ms: int = 0
    end_ms: int = 0

    def __post_init__(self) -> None:
        if self.end_ms <= 0:
            self.end_ms = self.info.duration_ms

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


def format_time(ms: int) -> str:
    ms = max(0, int(ms))
    total = ms // 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    r = ms % 1000
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}.{r:03d}"
    return f"{m:02d}:{s:02d}.{r:03d}"


def seconds_arg(ms: int) -> str:
    return f"{max(0, ms) / 1000.0:.3f}"


def parse_fps(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        if "/" in value:
            a, b = value.split("/", 1)
            den = float(b)
            if den == 0:
                return 0.0
            return float(a) / den
        return float(value)
    except Exception:
        return 0.0


def hide_console_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}


def probe_video(path: Path, ffprobe: Path) -> VideoInfo:
    """Equivalente a probe_video() do editor PySide6 ativo da release V8."""
    if not ffprobe.exists():
        return VideoInfo(0, 0, 0, 0.0, "video", None)
    command = [
        str(ffprobe),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, **hide_console_kwargs())
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Falha ao analisar vídeo.")
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration") or 0.0)
    width = height = 0
    fps = 0.0
    video_codec = "video"
    audio_codec: Optional[str] = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_codec == "video":
            video_codec = (stream.get("codec_name") or "video").lower()
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            fps = parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "")
            try:
                duration = max(duration, float(stream.get("duration") or 0.0))
            except Exception:
                pass
        elif stream.get("codec_type") == "audio" and not audio_codec:
            audio_codec = (stream.get("codec_name") or "audio").lower()
    return VideoInfo(int(duration * 1000), width, height, fps, video_codec, audio_codec)


def total_duration(clips: Sequence[Clip]) -> int:
    return sum(clip.duration_ms for clip in clips)


def global_start_for_clip(clips: Sequence[Clip], index: int) -> int:
    return sum(clips[i].duration_ms for i in range(max(0, index)))


def clip_at_global(clips: Sequence[Clip], global_ms: int) -> Tuple[int, int]:
    """Preserva inclusive a escolha do clipe anterior no limite exato (<=)."""
    if not clips:
        return -1, 0
    cursor = 0
    for index, clip in enumerate(clips):
        next_cursor = cursor + clip.duration_ms
        if global_ms <= next_cursor or index == len(clips) - 1:
            return index, clip.start_ms + max(0, global_ms - cursor)
        cursor = next_cursor
    return len(clips) - 1, clips[-1].start_ms


def export_output_path(exports_dir: Path, clip: Clip) -> Path:
    start = format_time(clip.start_ms).replace(":", "-").replace(".", "-")
    end = format_time(clip.end_ms).replace(":", "-").replace(".", "-")
    return exports_dir / f"{clip.path.stem}_corte_{start}_{end}.mp4"


def build_export_command(ffmpeg: Path, clip: Clip, output: Path) -> list[str]:
    return [
        str(ffmpeg),
        "-y",
        "-i", str(clip.path),
        "-ss", seconds_arg(clip.start_ms),
        "-t", seconds_arg(clip.duration_ms),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(output),
    ]
