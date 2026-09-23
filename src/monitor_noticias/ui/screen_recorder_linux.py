from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import time

from monitor_noticias.ui.screen_recorder_audio import AudioDevice


def _run_text(command: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        cp = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return int(cp.returncode), cp.stdout or ""
    except Exception as exc:
        return -1, f"{exc.__class__.__name__}: {exc}"


def pactl_available() -> bool:
    return shutil.which("pactl") is not None


def _pactl_value(*args: str) -> str:
    if not pactl_available():
        return ""

    code, output = _run_text(["pactl", *args])
    if code != 0 or not output.strip():
        return ""

    return output.strip().splitlines()[0].strip()


def _pulse_sources() -> list[str]:
    if not pactl_available():
        return []

    code, output = _run_text(
        ["pactl", "list", "short", "sources"]
    )

    if code != 0:
        return []

    result: list[str] = []

    for raw in output.splitlines():
        fields = raw.strip().split()
        if len(fields) < 2:
            continue

        name = fields[1].strip()
        if name and name not in result:
            result.append(name)

    return result


def _pretty_name(source: str) -> str:
    value = source

    for token in (
        ".monitor",
        "alsa_output.",
        "alsa_input.",
        "bluez_output.",
        "bluez_input.",
    ):
        value = value.replace(token, "")

    value = value.replace("_", " ")
    return value[:90] or source


def list_linux_audio_devices() -> tuple[list[AudioDevice], str]:
    """Detecta áudio Linux pela camada PulseAudio/PipeWire-Pulse."""

    if not pactl_available():
        return [], (
            "pactl não encontrado. A gravação de vídeo pode continuar "
            "sem áudio."
        )

    sources = _pulse_sources()
    default_sink = _pactl_value("get-default-sink")
    default_source = _pactl_value("get-default-source")

    diagnostic = [
        f"Fontes Pulse encontradas: {len(sources)}",
        f"Default sink: {default_sink or '(não informado)'}",
        f"Default source: {default_source or '(não informado)'}",
    ]

    devices: list[AudioDevice] = []

    preferred_monitor = (
        f"{default_sink}.monitor"
        if default_sink
        else ""
    )

    if preferred_monitor in sources:
        system_source = preferred_monitor
    else:
        system_source = next(
            (s for s in sources if s.endswith(".monitor")),
            "",
        )

    if system_source:
        devices.append(
            AudioDevice(
                key=f"pulse:{system_source}",
                name=f"Áudio do sistema — {_pretty_name(system_source)}",
                index=-1,
                channels=2,
                rate=48000,
                kind="system",
            )
        )
        diagnostic.append(f"SYSTEM: {system_source}")
    else:
        diagnostic.append("SYSTEM: nenhuma fonte monitor encontrada.")

    microphone_sources: list[str] = []

    if (
        default_source
        and default_source in sources
        and not default_source.endswith(".monitor")
    ):
        microphone_sources.append(default_source)

    for source in sources:
        if source.endswith(".monitor"):
            continue
        if source not in microphone_sources:
            microphone_sources.append(source)

    for source in microphone_sources:
        devices.append(
            AudioDevice(
                key=f"pulse:{source}",
                name=f"Microfone — {_pretty_name(source)}",
                index=-1,
                channels=2,
                rate=48000,
                kind="microphone",
            )
        )
        diagnostic.append(f"MIC: {source}")

    return devices, "\n".join(diagnostic)


def pulse_source_for(device: AudioDevice) -> str:
    key = str(device.key or "")
    return key[len("pulse:"):] if key.startswith("pulse:") else key


class LinuxPulseSegmentRecorder:
    """Grava uma fonte PulseAudio/PipeWire-Pulse em WAV usando FFmpeg."""

    def __init__(
        self,
        device: AudioDevice,
        output: Path,
        ffmpeg: Path,
    ) -> None:
        self.device = device
        self.output = Path(output)
        self.ffmpeg = Path(ffmpeg)

        self._process: subprocess.Popen[bytes] | None = None
        self._error: str | None = None
        self._started_at: float | None = None
        self._first_callback_at: float | None = None
        self._stopped_at: float | None = None

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def started_at(self) -> float | None:
        return self._started_at

    @property
    def first_callback_at(self) -> float | None:
        return self._first_callback_at

    @property
    def stopped_at(self) -> float | None:
        return self._stopped_at

    def start(self) -> None:
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
            "-thread_queue_size",
            "1024",
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
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            now = time.perf_counter()
            self._started_at = now
            self._first_callback_at = now

            time.sleep(0.08)

            if self._process.poll() is not None:
                code = self._process.returncode
                self._process = None
                raise RuntimeError(
                    f"FFmpeg/Pulse encerrou ao iniciar (código {code})."
                )

        except Exception as exc:
            self._error = f"{exc.__class__.__name__}: {exc}"
            self.stop()
            raise

    def stop(self) -> None:
        process = self._process
        self._process = None

        if process is not None and process.poll() is None:
            try:
                if process.stdin is not None:
                    process.stdin.write(b"q\n")
                    process.stdin.flush()
            except Exception:
                pass

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

        self._stopped_at = time.perf_counter()
