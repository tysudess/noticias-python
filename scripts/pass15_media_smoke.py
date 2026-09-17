from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QApplication

from monitor_noticias.video_editor.core import Clip, build_export_command, probe_video


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Comando falhou ({result.returncode}): {command}\n{result.stdout}\n{result.stderr}")
    return result


def exercise_qt_player(source: Path) -> tuple[int, int]:
    app = QApplication.instance() or QApplication([])
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setVolume(0.85)
    video = QVideoWidget()
    player.setAudioOutput(audio)
    player.setVideoOutput(video)
    errors: list[str] = []
    player.errorOccurred.connect(lambda *_: errors.append(player.errorString()))
    player.setSource(QUrl.fromLocalFile(str(source)))
    player.play()

    deadline = time.monotonic() + 8
    max_position = 0
    while time.monotonic() < deadline:
        app.processEvents()
        max_position = max(max_position, player.position())
        if errors:
            raise RuntimeError("QMediaPlayer: " + " | ".join(errors))
        if max_position >= 300:
            break
        time.sleep(0.02)
    assert max_position >= 300, f"QMediaPlayer não avançou: {max_position} ms"

    player.pause()
    app.processEvents()
    assert player.playbackState() == QMediaPlayer.PlaybackState.PausedState
    player.setPosition(1000)
    seek_deadline = time.monotonic() + 3
    while time.monotonic() < seek_deadline:
        app.processEvents()
        if abs(player.position() - 1000) <= 250:
            break
        time.sleep(0.02)
    seek_position = player.position()
    assert abs(seek_position - 1000) <= 250, f"Seek fora da tolerância: {seek_position} ms"
    assert abs(audio.volume() - 0.85) < 0.01

    # O editor original era um processo separado; fechar o processo liberava a
    # mídia. O editor integrado reproduz esse teardown limpando a source.
    player.stop()
    player.setSource(QUrl())
    video.close()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)
    return max_position, seek_position


def resolve_media_tools() -> tuple[str, str]:
    own_ffmpeg = ROOT / "bin" / "ffmpeg.exe"
    own_ffprobe = ROOT / "bin" / "ffprobe.exe"
    if own_ffmpeg.is_file() and own_ffprobe.is_file():
        return str(own_ffmpeg), str(own_ffprobe)
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Gate não possui FFmpeg/FFprobe da aplicação nem ferramentas no PATH.")
    return ffmpeg, ffprobe


def main() -> int:
    ffmpeg, ffprobe = resolve_media_tools()

    with tempfile.TemporaryDirectory(prefix="pass15-media-") as temp_name:
        temp = Path(temp_name)
        source = temp / "fonte teste edição.mp4"
        output = temp / "saida corte.mp4"

        run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
            "-t", "2.0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(source),
        ])

        info = probe_video(source, Path(ffprobe))
        assert 1800 <= info.duration_ms <= 2200, info
        assert (info.width, info.height) == (320, 240), info
        assert 24.0 <= info.fps <= 26.0, info
        assert info.video_codec == "h264", info
        assert info.audio_codec == "aac", info

        player_position, seek_position = exercise_qt_player(source)

        clip = Clip(path=source, info=info)
        command = build_export_command(Path(ffmpeg), clip, output)
        run(command)
        assert output.is_file() and output.stat().st_size > 1024

        probe = run([
            ffprobe, "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(output),
        ])
        payload = json.loads(probe.stdout)
        streams = payload["streams"]
        video = next(s for s in streams if s.get("codec_type") == "video")
        audio = next(s for s in streams if s.get("codec_type") == "audio")
        assert video["codec_name"] == "h264"
        assert int(video["width"]) == 320 and int(video["height"]) == 240
        assert audio["codec_name"] == "aac"
        assert int(audio.get("sample_rate", "0")) == 44100
        assert int(audio.get("channels", 0)) >= 1
        duration = float(payload["format"]["duration"])
        assert 1.7 <= duration <= 2.3

        print(
            "MEDIA SMOKE OK "
            f"player_position={player_position}ms seek={seek_position}ms "
            f"codec={video['codec_name']} duration={duration:.3f}s "
            f"resolution={video['width']}x{video['height']} fps={video.get('avg_frame_rate')} "
            f"audio={audio['codec_name']} sample_rate={audio.get('sample_rate')} channels={audio.get('channels')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
