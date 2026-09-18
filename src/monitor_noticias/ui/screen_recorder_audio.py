from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from pathlib import Path

try:
    import pyaudiowpatch as pyaudio
except Exception:
    pyaudio = None


@dataclass(frozen=True, slots=True)
class AudioDevice:
    key: str
    name: str
    index: int
    channels: int
    rate: int
    kind: str  # "system" | "microphone"


def backend_available() -> bool:
    return pyaudio is not None


def list_wasapi_devices() -> tuple[list[AudioDevice], str]:
    """Lista loopback do sistema + entradas WASAPI reais.

    O primeiro dispositivo, quando disponível, é o loopback dos alto-falantes
    padrão. Isso permite capturar o áudio que está saindo no Windows mesmo
    quando o PC não possui "Stereo Mix".
    """
    if pyaudio is None:
        return [], (
            "PyAudioWPatch não está instalado. "
            "Adicione PyAudioWPatch==0.2.12.8 ao requirements.txt."
        )

    devices: list[AudioDevice] = []
    diagnostic: list[str] = []

    try:
        manager = pyaudio.PyAudio()
    except Exception as exc:
        return [], f"Falha ao iniciar WASAPI: {exc}"

    try:
        # Áudio do sistema: loopback do dispositivo de saída padrão.
        try:
            loopback = manager.get_default_wasapi_loopback()
            channels = max(
                1,
                min(
                    2,
                    int(loopback.get("maxInputChannels") or 2),
                ),
            )
            rate = int(
                float(
                    loopback.get("defaultSampleRate")
                    or 48000
                )
            )
            devices.append(
                AudioDevice(
                    key=f"system:{int(loopback['index'])}",
                    name=str(loopback.get("name") or "Áudio do sistema"),
                    index=int(loopback["index"]),
                    channels=channels,
                    rate=rate,
                    kind="system",
                )
            )
            diagnostic.append(
                "SYSTEM LOOPBACK: "
                f"{loopback.get('index')} | "
                f"{loopback.get('name')} | "
                f"{channels}ch | {rate}Hz"
            )
        except Exception as exc:
            diagnostic.append(
                f"SYSTEM LOOPBACK indisponível: {exc}"
            )

        # Microfones / entradas WASAPI.
        try:
            wasapi = manager.get_host_api_info_by_type(
                pyaudio.paWASAPI
            )
            wasapi_index = int(wasapi["index"])
        except Exception:
            wasapi_index = -1

        seen: set[int] = {
            device.index
            for device in devices
        }

        for index in range(manager.get_device_count()):
            try:
                info = manager.get_device_info_by_index(index)
            except Exception:
                continue

            try:
                if (
                    wasapi_index >= 0
                    and int(info.get("hostApi", -1))
                    != wasapi_index
                ):
                    continue
            except Exception:
                pass

            max_inputs = int(
                info.get("maxInputChannels") or 0
            )
            is_loopback = bool(
                info.get("isLoopbackDevice")
            )

            if (
                max_inputs <= 0
                or is_loopback
                or index in seen
            ):
                continue

            channels = max(
                1,
                min(2, max_inputs),
            )
            rate = int(
                float(
                    info.get("defaultSampleRate")
                    or 48000
                )
            )
            name = str(
                info.get("name")
                or f"Entrada {index}"
            )

            devices.append(
                AudioDevice(
                    key=f"mic:{index}",
                    name=name,
                    index=index,
                    channels=channels,
                    rate=rate,
                    kind="microphone",
                )
            )
            seen.add(index)
            diagnostic.append(
                "MIC: "
                f"{index} | {name} | "
                f"{channels}ch | {rate}Hz"
            )

    finally:
        try:
            manager.terminate()
        except Exception:
            pass

    if not diagnostic:
        diagnostic.append(
            "Nenhum dispositivo WASAPI encontrado."
        )

    return devices, "\n".join(diagnostic)


class WasapiSegmentRecorder:
    """Grava um segmento WAV via WASAPI/PyAudioWPatch.

    PortAudio usa seu próprio callback em tempo real, portanto não precisamos
    manter uma thread Python bloqueada lendo o dispositivo.
    """

    def __init__(
        self,
        device: AudioDevice,
        output: Path,
    ) -> None:
        if pyaudio is None:
            raise RuntimeError(
                "PyAudioWPatch não está disponível."
            )

        self.device = device
        self.output = Path(output)

        self._manager = None
        self._stream = None
        self._wave = None
        self._lock = threading.Lock()
        self._error: str | None = None
        self._started = False

    @property
    def error(self) -> str | None:
        return self._error

    def start(self) -> None:
        self.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manager = pyaudio.PyAudio()
        wav = wave.open(
            str(self.output),
            "wb",
        )

        wav.setnchannels(
            self.device.channels
        )
        wav.setsampwidth(
            manager.get_sample_size(
                pyaudio.paInt16
            )
        )
        wav.setframerate(
            self.device.rate
        )

        self._manager = manager
        self._wave = wav

        def callback(
            in_data,
            _frame_count,
            _time_info,
            _status_flags,
        ):
            try:
                with self._lock:
                    if (
                        self._wave is not None
                        and in_data
                    ):
                        self._wave.writeframesraw(
                            in_data
                        )
            except Exception as exc:
                self._error = str(exc)

            return (
                in_data,
                pyaudio.paContinue,
            )

        try:
            self._stream = manager.open(
                format=pyaudio.paInt16,
                channels=self.device.channels,
                rate=self.device.rate,
                frames_per_buffer=1024,
                input=True,
                input_device_index=self.device.index,
                stream_callback=callback,
            )
            self._stream.start_stream()
            self._started = True
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        stream = self._stream
        self._stream = None

        if stream is not None:
            try:
                if stream.is_active():
                    stream.stop_stream()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

        with self._lock:
            wav = self._wave
            self._wave = None

            if wav is not None:
                try:
                    wav.close()
                except Exception:
                    pass

        manager = self._manager
        self._manager = None

        if manager is not None:
            try:
                manager.terminate()
            except Exception:
                pass

        self._started = False
