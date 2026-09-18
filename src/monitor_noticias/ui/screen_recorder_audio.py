from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from pathlib import Path

_BACKEND_IMPORT_ERROR = ""

try:
    import pyaudiowpatch as pyaudio
except Exception as exc:
    pyaudio = None
    _BACKEND_IMPORT_ERROR = (
        f"{exc.__class__.__name__}: {exc}"
    )


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


def backend_error() -> str:
    return _BACKEND_IMPORT_ERROR


def _clean_channels(value: object) -> int:
    try:
        channels = int(value or 0)
    except Exception:
        channels = 0

    # 1 ou 2 canais tornam a gravação mais previsível na junção com MP4.
    return max(1, min(2, channels or 2))


def _clean_rate(value: object) -> int:
    try:
        return max(8000, int(float(value or 48000)))
    except Exception:
        return 48000


def _device_from_info(
    info: dict,
    *,
    kind: str,
) -> AudioDevice:
    index = int(info["index"])
    return AudioDevice(
        key=f"{kind}:{index}",
        name=str(
            info.get("name")
            or (
                "Áudio do sistema"
                if kind == "system"
                else f"Microfone {index}"
            )
        ),
        index=index,
        channels=_clean_channels(
            info.get("maxInputChannels")
        ),
        rate=_clean_rate(
            info.get("defaultSampleRate")
        ),
        kind=kind,
    )


def list_wasapi_devices() -> tuple[list[AudioDevice], str]:
    """Lista áudio do sistema por WASAPI loopback e microfones.

    O áudio do sistema NÃO depende de Stereo Mix. PyAudioWPatch cria
    dispositivos de loopback WASAPI para as saídas do Windows.
    """
    if pyaudio is None:
        detail = (
            f" ({_BACKEND_IMPORT_ERROR})"
            if _BACKEND_IMPORT_ERROR
            else ""
        )
        return [], (
            "PyAudioWPatch não pôde ser carregado"
            f"{detail}. "
            "O portable deve conter pyaudiowpatch e _portaudiowpatch.pyd."
        )

    devices: list[AudioDevice] = []
    diagnostic: list[str] = []

    try:
        manager = pyaudio.PyAudio()
    except Exception as exc:
        return [], (
            "Falha ao iniciar o backend WASAPI: "
            f"{exc.__class__.__name__}: {exc}"
        )

    try:
        loopback_info = None

        # Caminho preferencial suportado pelo PyAudioWPatch.
        try:
            loopback_info = (
                manager.get_default_wasapi_loopback()
            )
            diagnostic.append(
                "DEFAULT WASAPI LOOPBACK localizado."
            )
        except Exception as exc:
            diagnostic.append(
                "get_default_wasapi_loopback falhou: "
                f"{exc.__class__.__name__}: {exc}"
            )

        # Fallback documentado: localizar o loopback análogo ao
        # dispositivo de saída WASAPI padrão.
        if loopback_info is None:
            try:
                wasapi = (
                    manager.get_host_api_info_by_type(
                        pyaudio.paWASAPI
                    )
                )
                default_output = (
                    manager.get_device_info_by_index(
                        int(
                            wasapi[
                                "defaultOutputDevice"
                            ]
                        )
                    )
                )

                if bool(
                    default_output.get(
                        "isLoopbackDevice"
                    )
                ):
                    loopback_info = default_output
                else:
                    output_name = str(
                        default_output.get(
                            "name"
                        )
                        or ""
                    )

                    for candidate in (
                        manager.get_loopback_device_info_generator()
                    ):
                        candidate_name = str(
                            candidate.get("name")
                            or ""
                        )

                        if (
                            output_name
                            and output_name
                            in candidate_name
                        ):
                            loopback_info = candidate
                            break
            except Exception as exc:
                diagnostic.append(
                    "Fallback WASAPI padrão falhou: "
                    f"{exc.__class__.__name__}: {exc}"
                )

        # Último fallback: primeiro loopback disponível.
        if loopback_info is None:
            try:
                loopbacks = list(
                    manager.get_loopback_device_info_generator()
                )

                if loopbacks:
                    loopback_info = loopbacks[0]
            except Exception as exc:
                diagnostic.append(
                    "Enumeração de loopbacks falhou: "
                    f"{exc.__class__.__name__}: {exc}"
                )

        seen: set[int] = set()

        if loopback_info is not None:
            system = _device_from_info(
                loopback_info,
                kind="system",
            )
            devices.append(system)
            seen.add(system.index)

            diagnostic.append(
                "SYSTEM: "
                f"{system.index} | "
                f"{system.name} | "
                f"{system.channels}ch | "
                f"{system.rate}Hz"
            )
        else:
            diagnostic.append(
                "SYSTEM: nenhum loopback WASAPI encontrado."
            )

        # Entradas reais do WASAPI (microfones/interface).
        try:
            wasapi = (
                manager.get_host_api_info_by_type(
                    pyaudio.paWASAPI
                )
            )
            wasapi_index = int(
                wasapi["index"]
            )
        except Exception:
            wasapi_index = -1

        for index in range(
            manager.get_device_count()
        ):
            try:
                info = (
                    manager.get_device_info_by_index(
                        index
                    )
                )
            except Exception:
                continue

            if index in seen:
                continue

            try:
                if (
                    wasapi_index >= 0
                    and int(
                        info.get(
                            "hostApi",
                            -1,
                        )
                    )
                    != wasapi_index
                ):
                    continue
            except Exception:
                continue

            if bool(
                info.get(
                    "isLoopbackDevice"
                )
            ):
                continue

            try:
                max_inputs = int(
                    info.get(
                        "maxInputChannels"
                    )
                    or 0
                )
            except Exception:
                max_inputs = 0

            if max_inputs <= 0:
                continue

            mic = _device_from_info(
                info,
                kind="microphone",
            )
            devices.append(mic)
            seen.add(mic.index)

            diagnostic.append(
                "MIC: "
                f"{mic.index} | "
                f"{mic.name} | "
                f"{mic.channels}ch | "
                f"{mic.rate}Hz"
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
    """Grava um WAV via callback PortAudio/WASAPI."""

    def __init__(
        self,
        device: AudioDevice,
        output: Path,
    ) -> None:
        if pyaudio is None:
            raise RuntimeError(
                "PyAudioWPatch indisponível: "
                + (
                    _BACKEND_IMPORT_ERROR
                    or "backend não carregado"
                )
            )

        self.device = device
        self.output = Path(output)

        self._manager = None
        self._stream = None
        self._wave = None
        self._lock = threading.Lock()
        self._error: str | None = None

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
                self._error = (
                    f"{exc.__class__.__name__}: {exc}"
                )

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
