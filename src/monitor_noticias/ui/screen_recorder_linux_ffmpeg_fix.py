from __future__ import annotations

"""V102: corrige a montagem dos comandos FFmpeg usados pelo gravador Linux.

Os logs reais do Ubuntu mostram que o FFmpeg aborta imediatamente com código
234 ao receber a opção de fila usada anteriormente tanto no input PulseAudio
quanto no input rawvideo. Este patch substitui apenas os dois métodos de start
Linux, sem mudar o backend do Windows e sem modificar o binário FFmpeg.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

_INSTALLED = False


def _fixed_linux_pulse_start(self) -> None:
    """Inicia a captura PulseAudio sem a opção de fila rejeitada pelo bundle."""
    from monitor_noticias.ui.screen_recorder_linux import pulse_source_for

    if not self.ffmpeg.is_file():
        raise RuntimeError("FFmpeg não encontrado para captura de áudio.")

    source = pulse_source_for(self.device)
    if not source:
        raise RuntimeError("Fonte de áudio Linux inválida.")

    self.output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(self.ffmpeg),
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "pulse",
        "-i",
        source,
        "-ac",
        str(max(1, min(2, self.device.channels))),
        "-ar",
        str(max(8000, self.device.rate)),
        "-c:a",
        "pcm_s16le",
        str(self.output),
    ]

    try:
        stderr_target = subprocess.DEVNULL

        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_handle = self.log_path.open("ab", buffering=0)
            self._log_handle.write(
                (
                    "\n[AUDIO LINUX V102] comando: "
                    + " ".join(command)
                    + "\n"
                ).encode("utf-8", errors="ignore")
            )
            stderr_target = self._log_handle

        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=stderr_target,
            start_new_session=True,
        )

        now = time.perf_counter()
        self._started_at = now
        self._first_callback_at = now

        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                break
            time.sleep(0.025)

        if self._process.poll() is not None:
            code = self._process.returncode
            self._process = None
            self._close_log()
            raise RuntimeError(
                "FFmpeg/Pulse encerrou ao iniciar "
                f"(código {code}); consulte screen_recorder.log."
            )

    except Exception as exc:
        self._error = f"{exc.__class__.__name__}: {exc}"
        self.stop()
        raise


def _fixed_linux_qt_pipe_start(self) -> None:
    """Inicia rawvideo BGRA pelo descritor dedicado sem a opção incompatível."""
    if not self.ffmpeg.is_file():
        raise RuntimeError("FFmpeg não encontrado para codificar a tela.")

    frame, width, height = self._capture_frame()
    self._source_width = width
    self._source_height = height

    with self._frame_lock:
        self._latest_frame = frame

    target_w = max(2, int(self.target_size[0]))
    target_h = max(2, int(self.target_size[1]))

    if target_w % 2:
        target_w -= 1
    if target_h % 2:
        target_h -= 1

    self.output.parent.mkdir(parents=True, exist_ok=True)

    read_fd, write_fd = os.pipe()
    os.set_inheritable(read_fd, True)
    self._write_fd = write_fd

    command = [
        str(self.ffmpeg),
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "rawvideo",
        "-pixel_format",
        "bgra",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(self.fps),
        "-i",
        f"pipe:{read_fd}",
        "-map",
        "0:v:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-crf",
        str(self.crf),
        "-vf",
        (
            f"scale={target_w}:{target_h}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:"
            "(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(self.fps),
        "-movflags",
        "+faststart",
        str(self.output),
    ]

    self._log("V102 comando: " + " ".join(command))
    self._log(
        "V102 captura Qt: "
        f"global={self.capture_global.x()},{self.capture_global.y()} "
        f"{self.capture_global.width()}x{self.capture_global.height()} "
        f"frame={width}x{height} fps={self.fps}"
    )

    try:
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=self.log_handle,
            pass_fds=(read_fd,),
            start_new_session=True,
        )
    except Exception:
        self._close_write_fd()
        raise
    finally:
        try:
            os.close(read_fd)
        except OSError:
            pass

    self.started_at = time.perf_counter()
    self._stop_event.clear()

    import threading

    self._writer_thread = threading.Thread(
        target=self._writer_loop,
        name="CentralQtScreenPipe",
        daemon=True,
    )
    self._writer_thread.start()
    self._timer.start()

    deadline = time.monotonic() + 0.25
    while time.monotonic() < deadline:
        if self.process.poll() is not None:
            break
        # Processa eventos apenas na thread Qt que criou o QTimer.
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
        time.sleep(0.015)

    if self.process.poll() is not None:
        code = self.process.returncode
        self.stop()
        raise RuntimeError(
            "FFmpeg encerrou ao iniciar a codificação Qt "
            f"(código {code}); consulte screen_recorder.log."
        )


def install_linux_ffmpeg_input_option_fix() -> None:
    """Instala a correção V102 apenas no Linux e antes da criação da página."""
    global _INSTALLED

    if _INSTALLED:
        return

    if not sys.platform.startswith("linux"):
        _INSTALLED = True
        return

    from monitor_noticias.ui.screen_recorder_linux import LinuxPulseSegmentRecorder
    from monitor_noticias.ui.screen_recorder_linux_patch import (
        _LinuxQtScreenPipeRecorder,
    )

    LinuxPulseSegmentRecorder.start = _fixed_linux_pulse_start
    _LinuxQtScreenPipeRecorder.start = _fixed_linux_qt_pipe_start

    _fixed_linux_pulse_start._central_v102_ffmpeg_input_fix = True
    _fixed_linux_qt_pipe_start._central_v102_ffmpeg_input_fix = True
    _INSTALLED = True
