from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import time
import wave

from monitor_noticias.ui import screen_recorder_audio
from monitor_noticias.ui import screen_recorder_linux
from monitor_noticias.ui import screen_recorder_page


_INSTALLED = False

MIN_CLOCK_SAMPLE_SECONDS = 12.0
MAX_VALID_CLOCK_ERROR = 0.02
MAX_APPLIED_CLOCK_CORRECTION = 0.005
SYNC_WARNING_SECONDS = 0.180


def _ffprobe_for(app_root: Path) -> Path:
    root = Path(app_root)
    candidates = (
        root / "bin" / "ffprobe.exe",
        root / "bin" / "ffprobe",
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return candidates[0] if sys.platform.startswith("win") else candidates[1]


def _ffmpeg_for(app_root: Path) -> Path:
    root = Path(app_root)
    candidates = (
        root / "bin" / "ffmpeg.exe",
        root / "bin" / "ffmpeg",
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return candidates[0] if sys.platform.startswith("win") else candidates[1]


def _wav_duration(path: Path | None) -> float:
    if path is None:
        return 0.0

    path = Path(path)

    if not path.is_file():
        return 0.0

    try:
        with wave.open(str(path), "rb") as wav:
            rate = float(wav.getframerate() or 0)
            frames = float(wav.getnframes() or 0)

        if rate <= 0:
            return 0.0

        return max(0.0, frames / rate)

    except Exception:
        return 0.0


def _bounded_clock_factor(
    sample_duration: float,
    wall_duration: float,
) -> float:
    """Retorna uma correção minúscula de clock, nunca um 'encaixe' forçado.

    O código antigo comparava o WAV inteiro com a duração final do vídeo.
    Como o áudio continuava capturando enquanto o FFmpeg encerrava, a sobra
    no final fazia toda a faixa ser acelerada. Isso produzia drift progressivo.

    Aqui comparamos SOMENTE:
      duração real em amostras / duração de parede da captura de áudio.

    Segmentos curtos e medições anômalas não recebem atempo.
    """

    sample = float(sample_duration or 0.0)
    wall = float(wall_duration or 0.0)

    if (
        not math.isfinite(sample)
        or not math.isfinite(wall)
        or sample < MIN_CLOCK_SAMPLE_SECONDS
        or wall < MIN_CLOCK_SAMPLE_SECONDS
    ):
        return 1.0

    ratio = sample / wall

    if (
        not math.isfinite(ratio)
        or abs(ratio - 1.0) > MAX_VALID_CLOCK_ERROR
    ):
        return 1.0

    return max(
        1.0 - MAX_APPLIED_CLOCK_CORRECTION,
        min(
            1.0 + MAX_APPLIED_CLOCK_CORRECTION,
            ratio,
        ),
    )


def _atempo_parts(factor: float) -> list[str]:
    factor = float(factor or 1.0)

    if abs(factor - 1.0) < 0.00015:
        return []

    # Nesta V95 o fator é deliberadamente limitado a ±0,5%, então uma única
    # etapa sempre fica dentro do intervalo aceito pelo FFmpeg.
    return [f"atempo={factor:.8f}"]


def _audio_filters(
    *,
    video_duration: float,
    audio_offset: float,
    clock_factor: float,
    channels: int,
) -> list[str]:
    duration = max(0.001, float(video_duration or 0.0))
    offset = float(audio_offset or 0.0)

    # offset < 0: o áudio começou antes do vídeo -> remove apenas esse início.
    # offset > 0: o áudio começou depois -> adiciona silêncio no início.
    lead_trim = max(0.0, -offset)
    delay = max(0.0, offset)

    filters: list[str] = []

    if lead_trim > 0.0005:
        filters.append(
            f"atrim=start={lead_trim:.6f}"
        )

    filters.append("asetpts=PTS-STARTPTS")
    filters.extend(
        _atempo_parts(clock_factor)
    )

    # Mantém saída em 48 kHz e corrige apenas pequenas irregularidades de PTS.
    filters.append(
        "aresample=48000:async=1:first_pts=0"
    )

    if delay > 0.0005:
        delay_ms = max(
            0,
            int(round(delay * 1000.0)),
        )
        delay_values = "|".join(
            [str(delay_ms)]
            * max(1, min(2, int(channels or 2)))
        )
        filters.append(
            f"adelay={delay_values}"
        )

    # O conteúdo termina no mesmo ponto do vídeo. Se o áudio real terminar
    # alguns milissegundos antes, apad preenche com silêncio; nunca esticamos
    # o conteúdo inteiro para ocupar a sobra.
    filters.extend(
        [
            "apad",
            f"atrim=duration={duration:.6f}",
            "asetpts=PTS-STARTPTS",
        ]
    )

    return filters


def _probe_stream_durations(
    app_root: Path,
    path: Path,
) -> tuple[float, float]:
    ffprobe = _ffprobe_for(app_root)

    if (
        not ffprobe.is_file()
        or not Path(path).is_file()
    ):
        return 0.0, 0.0

    creationflags = (
        0x08000000
        if sys.platform.startswith("win")
        else 0
    )

    try:
        result = subprocess.run(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,duration",
                "-of",
                "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=20,
            creationflags=creationflags,
        )

        data = json.loads(
            result.stdout or "{}"
        )

        video_duration = 0.0
        audio_duration = 0.0

        for stream in data.get("streams") or []:
            try:
                duration = float(
                    stream.get("duration") or 0.0
                )
            except Exception:
                duration = 0.0

            if duration <= 0:
                continue

            if stream.get("codec_type") == "video":
                video_duration = max(
                    video_duration,
                    duration,
                )
            elif stream.get("codec_type") == "audio":
                audio_duration = max(
                    audio_duration,
                    duration,
                )

        return video_duration, audio_duration

    except Exception:
        return 0.0, 0.0


def _append_sync_log(
    recorder_page,
    message: str,
) -> None:
    try:
        path = (
            Path(recorder_page.logs_dir)
            / "screen_recorder.log"
        )
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "a",
            encoding="utf-8",
            errors="ignore",
        ) as log:
            log.write(
                "[A/V SYNC V95] "
                + str(message)
                + "\n"
            )
    except Exception:
        pass


def _install_audio_stop_request() -> None:
    wasapi_cls = (
        screen_recorder_audio
        .WasapiSegmentRecorder
    )

    if not hasattr(
        wasapi_cls,
        "request_stop",
    ):
        def request_stop(self) -> None:
            if getattr(
                self,
                "_sync_stop_requested_at",
                None,
            ) is not None:
                return

            stream = getattr(
                self,
                "_stream",
                None,
            )

            try:
                if (
                    stream is not None
                    and stream.is_active()
                ):
                    # Para a entrada primeiro. O timestamp é marcado DEPOIS
                    # que PortAudio confirma a parada, correspondendo melhor
                    # ao último sample efetivamente escrito no WAV.
                    stream.stop_stream()
            except Exception:
                pass

            self._sync_stop_requested_at = (
                time.perf_counter()
            )

        wasapi_cls.request_stop = request_stop
        wasapi_cls.stop_requested_at = property(
            lambda self: getattr(
                self,
                "_sync_stop_requested_at",
                None,
            )
        )

    linux_cls = (
        screen_recorder_linux
        .LinuxPulseSegmentRecorder
    )

    if not hasattr(
        linux_cls,
        "request_stop",
    ):
        def linux_request_stop(self) -> None:
            if getattr(
                self,
                "_sync_stop_requested_at",
                None,
            ) is None:
                self._sync_stop_requested_at = (
                    time.perf_counter()
                )

            process = getattr(
                self,
                "_process",
                None,
            )

            if (
                process is None
                or process.poll() is not None
            ):
                return

            try:
                if process.stdin is not None:
                    # Envia o stop sem aguardar aqui. Logo em seguida o mesmo
                    # método de finalização envia "q" para o vídeo.
                    process.stdin.write(b"q\n")
                    process.stdin.flush()
            except Exception:
                pass

        linux_cls.request_stop = (
            linux_request_stop
        )
        linux_cls.stop_requested_at = property(
            lambda self: getattr(
                self,
                "_sync_stop_requested_at",
                None,
            )
        )


def install_screen_recorder_sync_patch() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    _install_audio_stop_request()

    cls = screen_recorder_page.ScreenRecorderPage

    original_init = cls.__init__
    original_begin = cls._begin_session
    original_start_segment = cls._start_segment
    original_cleanup = cls._cleanup_session
    original_run_finalize = (
        cls._run_finalize_command
    )
    original_finalize = (
        cls._finalize_session
    )

    def patched_init(
        self,
        *args,
        **kwargs,
    ) -> None:
        original_init(
            self,
            *args,
            **kwargs,
        )

        # Corrige também o nome do binário no Ubuntu. No Windows continua
        # ffmpeg.exe/ffprobe.exe.
        self.ffmpeg = _ffmpeg_for(
            self.app_root
        )
        self._segment_audio_clock_factors = []

    def patched_begin_session(
        self,
    ) -> None:
        self._segment_audio_clock_factors = []
        original_begin(self)

    def patched_start_segment(
        self,
    ) -> bool:
        before = len(
            self._segments
        )

        ok = original_start_segment(
            self
        )

        if not ok:
            return False

        if len(self._segments) <= before:
            return True

        while (
            len(
                self._segment_audio_clock_factors
            )
            < len(self._segments)
        ):
            self._segment_audio_clock_factors.append(
                1.0
            )

        # PyAudio entrega o primeiro bloco de 1024 frames e o callback é
        # marcado no instante em que esse bloco chega. O WAV, porém, começa no
        # PRIMEIRO sample desse bloco. Compensar ~21 ms em 48 kHz elimina um
        # pequeno deslocamento constante que existia no início.
        recorder = self._audio_engine

        if (
            recorder is not None
            and isinstance(
                recorder,
                screen_recorder_audio.WasapiSegmentRecorder,
            )
            and self._segment_audio_offsets
            and recorder.first_callback_at is not None
        ):
            try:
                buffer_seconds = (
                    1024.0
                    / max(
                        8000.0,
                        float(
                            recorder.device.rate
                        ),
                    )
                )

                self._segment_audio_offsets[-1] -= (
                    buffer_seconds
                )
            except Exception:
                pass

        return True

    def patched_finish_current_segment(
        self,
    ) -> None:
        if self._segment_started_at is not None:
            self._elapsed_before_segment += max(
                0.0,
                time.monotonic()
                - self._segment_started_at,
            )

        self._segment_started_at = None

        recorder = self._audio_engine

        # PRIMEIRO solicita o fim do áudio, mas não espera sua finalização.
        # Em seguida solicita o fim do vídeo. Isso remove a janela em que o
        # áudio continuava gravando enquanto o FFmpeg de vídeo fechava.
        if recorder is not None:
            try:
                request_stop = getattr(
                    recorder,
                    "request_stop",
                    None,
                )
                if callable(request_stop):
                    request_stop()
            except Exception:
                pass

        process = self._process
        self._process = None

        if (
            process is not None
            and process.poll() is None
        ):
            try:
                if process.stdin is not None:
                    process.stdin.write(
                        b"q\n"
                    )
                    process.stdin.flush()
            except Exception:
                pass

            try:
                process.wait(
                    timeout=12
                )
            except subprocess.TimeoutExpired:
                try:
                    process.terminate()
                    process.wait(
                        timeout=4
                    )
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass

        # Agora fecha WAV/PortAudio ou aguarda o FFmpeg/Pulse já solicitado.
        self._stop_audio_engine()
        self._close_log()

        if (
            recorder is not None
            and self._segments
            and self._session_audio_device is not None
        ):
            index = (
                len(self._segments)
                - 1
            )

            audio_path = (
                self._audio_segments[index]
                if index < len(
                    self._audio_segments
                )
                else None
            )

            sample_duration = _wav_duration(
                audio_path
            )

            try:
                if isinstance(
                    recorder,
                    screen_recorder_audio.WasapiSegmentRecorder,
                ):
                    callback_at = (
                        recorder.first_callback_at
                        or recorder.started_at
                    )
                    if callback_at is not None:
                        first_sample_at = (
                            callback_at
                            - (
                                1024.0
                                / max(
                                    8000.0,
                                    float(
                                        recorder.device.rate
                                    ),
                                )
                            )
                        )
                    else:
                        first_sample_at = None
                else:
                    first_sample_at = (
                        recorder.first_callback_at
                        or recorder.started_at
                    )

                stop_requested_at = getattr(
                    recorder,
                    "stop_requested_at",
                    None,
                )

                wall_duration = (
                    max(
                        0.0,
                        float(
                            stop_requested_at
                            - first_sample_at
                        ),
                    )
                    if (
                        stop_requested_at is not None
                        and first_sample_at is not None
                    )
                    else 0.0
                )
            except Exception:
                wall_duration = 0.0

            # No Windows/WASAPI temos o instante do primeiro buffer e a
            # confirmação síncrona de stop_stream(). No Linux/Pulse o áudio é
            # outro processo FFmpeg e o comando "q" é assíncrono; por isso não
            # inferimos clock drift a partir do tempo de encerramento Linux.
            if isinstance(
                recorder,
                screen_recorder_audio.WasapiSegmentRecorder,
            ):
                factor = _bounded_clock_factor(
                    sample_duration,
                    wall_duration,
                )
            else:
                factor = 1.0

            while (
                len(
                    self._segment_audio_clock_factors
                )
                < len(self._segments)
            ):
                self._segment_audio_clock_factors.append(
                    1.0
                )

            self._segment_audio_clock_factors[
                index
            ] = factor

            offset = (
                self._segment_audio_offsets[index]
                if index < len(
                    self._segment_audio_offsets
                )
                else 0.0
            )

            _append_sync_log(
                self,
                (
                    f"segmento={index + 1} "
                    f"offset_inicio={offset:+.6f}s "
                    f"wav={sample_duration:.6f}s "
                    f"relogio={wall_duration:.6f}s "
                    f"clock_factor={factor:.8f}"
                ),
            )

        # Preserva o comportamento do patch Linux: após fechar um segmento a
        # moldura volta a aparecer fora da gravação.
        if (
            sys.platform.startswith("linux")
            and self._module_enabled
            and not self._closing
        ):
            try:
                self._update_capture_overlay()
            except Exception:
                pass

    def patched_probe_duration(
        self,
        path: Path,
    ) -> float:
        ffprobe = _ffprobe_for(
            self.app_root
        )

        if not ffprobe.is_file():
            return 0.0

        creationflags = (
            0x08000000
            if sys.platform.startswith("win")
            else 0
        )

        try:
            result = subprocess.run(
                [
                    str(ffprobe),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20,
                creationflags=creationflags,
            )

            return max(
                0.0,
                float(
                    result.stdout.strip()
                    or 0.0
                ),
            )
        except Exception:
            return 0.0

    def patched_mux_audio_segment(
        self,
        video: Path,
        audio: Path | None,
        output: Path,
        *,
        audio_offset: float = 0.0,
    ) -> bool:
        device = self._session_audio_device

        if device is None:
            return False

        video_duration = (
            patched_probe_duration(
                self,
                video,
            )
        )

        if video_duration <= 0:
            # Nunca usa a duração total da sessão para um segmento específico.
            # Se ffprobe falhar, recusar é mais seguro do que distorcer áudio.
            _append_sync_log(
                self,
                (
                    "Falha ao obter duração do segmento "
                    f"{Path(video).name}; mux A/V cancelado."
                ),
            )
            return False

        has_audio = (
            audio is not None
            and Path(audio).is_file()
            and Path(audio).stat().st_size > 64
        )

        try:
            segment_index = self._segments.index(
                Path(video)
            )
        except ValueError:
            segment_index = -1

        clock_factor = 1.0

        if (
            segment_index >= 0
            and segment_index
            < len(
                self._segment_audio_clock_factors
            )
        ):
            clock_factor = (
                self._segment_audio_clock_factors[
                    segment_index
                ]
            )

        if has_audio:
            filters = _audio_filters(
                video_duration=video_duration,
                audio_offset=audio_offset,
                clock_factor=clock_factor,
                channels=device.channels,
            )

            command = [
                str(self.ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-i",
                str(video),
                "-i",
                str(audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-af",
                ",".join(filters),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-movflags",
                "+faststart",
                "-avoid_negative_ts",
                "make_zero",
                str(output),
            ]

        else:
            layout = (
                "mono"
                if device.channels == 1
                else "stereo"
            )

            command = [
                str(self.ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-i",
                str(video),
                "-f",
                "lavfi",
                "-i",
                (
                    "anullsrc="
                    f"channel_layout={layout}:"
                    "sample_rate=48000"
                ),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-t",
                f"{video_duration:.6f}",
                "-movflags",
                "+faststart",
                str(output),
            ]

        ok = self._run_finalize_command(
            command,
            output_path=output,
        )

        if ok:
            video_out, audio_out = (
                _probe_stream_durations(
                    self.app_root,
                    output,
                )
            )

            if (
                video_out > 0
                and audio_out > 0
            ):
                delta = (
                    audio_out
                    - video_out
                )

                _append_sync_log(
                    self,
                    (
                        f"mux={Path(output).name} "
                        f"video={video_out:.6f}s "
                        f"audio={audio_out:.6f}s "
                        f"delta={delta:+.6f}s"
                    ),
                )

        return ok

    def patched_run_finalize_command(
        self,
        command: list[str],
        *,
        output_path: Path | None = None,
    ) -> bool:
        command = list(command)

        # Concatenação de vários segmentos com áudio:
        # NÃO copia AAC de segmento em segmento. Decodifica e gera uma única
        # faixa AAC contínua, evitando somar priming/timestamps em cada pausa.
        if (
            self._session_audio_device is not None
            and "concat" in command
        ):
            for index in range(
                len(command) - 1
            ):
                if (
                    command[index] == "-c"
                    and command[index + 1] == "copy"
                ):
                    command[
                        index:index + 2
                    ] = [
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-ar",
                        "48000",
                        "-af",
                        "aresample=48000:async=1:first_pts=0",
                    ]
                    break

        return original_run_finalize(
            self,
            command,
            output_path=output_path,
        )

    def _repair_final_duration(
        self,
        final_path: Path,
        video_duration: float,
    ) -> bool:
        repaired = (
            final_path.with_name(
                final_path.stem
                + ".sync-repair"
                + final_path.suffix
            )
        )

        try:
            repaired.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        command = [
            str(self.ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            str(final_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c:v",
            "copy",
            "-af",
            (
                "aresample=48000:async=1:first_pts=0,"
                "apad,"
                f"atrim=duration={video_duration:.6f},"
                "asetpts=PTS-STARTPTS"
            ),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(repaired),
        ]

        if not original_run_finalize(
            self,
            command,
            output_path=repaired,
        ):
            return False

        repaired_video, repaired_audio = (
            _probe_stream_durations(
                self.app_root,
                repaired,
            )
        )

        if (
            repaired_video <= 0
            or repaired_audio <= 0
            or abs(
                repaired_audio
                - repaired_video
            ) > SYNC_WARNING_SECONDS
        ):
            return False

        try:
            repaired.replace(
                final_path
            )
            return True
        except Exception:
            return False

    def patched_finalize_session(
        self,
    ) -> bool:
        ok = original_finalize(
            self
        )

        if (
            not ok
            or self._session_audio_device is None
            or self._final_path is None
            or not Path(
                self._final_path
            ).is_file()
        ):
            return ok

        final_path = Path(
            self._final_path
        )

        video_duration, audio_duration = (
            _probe_stream_durations(
                self.app_root,
                final_path,
            )
        )

        if (
            video_duration <= 0
            or audio_duration <= 0
        ):
            _append_sync_log(
                self,
                (
                    "Arquivo final salvo, mas ffprobe não forneceu "
                    "durações de ambas as faixas."
                ),
            )
            return ok

        delta = (
            audio_duration
            - video_duration
        )

        _append_sync_log(
            self,
            (
                f"FINAL video={video_duration:.6f}s "
                f"audio={audio_duration:.6f}s "
                f"delta={delta:+.6f}s"
            ),
        )

        if abs(delta) <= SYNC_WARNING_SECONDS:
            return True

        _append_sync_log(
            self,
            (
                "Diferença final acima do limite; executando "
                "normalização de duração sem alterar a velocidade "
                "do conteúdo."
            ),
        )

        repaired = _repair_final_duration(
            self,
            final_path,
            video_duration,
        )

        _append_sync_log(
            self,
            (
                "Reparo final: "
                + (
                    "OK"
                    if repaired
                    else "não aplicado"
                )
            ),
        )

        # O arquivo original já é válido. Se o reparo não puder ser feito,
        # preserva-o em vez de transformar uma gravação utilizável em erro.
        return True

    def patched_cleanup(
        self,
    ) -> None:
        original_cleanup(
            self
        )
        self._segment_audio_clock_factors = []

    cls.__init__ = patched_init
    cls._begin_session = (
        patched_begin_session
    )
    cls._start_segment = (
        patched_start_segment
    )
    cls._finish_current_segment = (
        patched_finish_current_segment
    )
    cls._probe_duration = (
        patched_probe_duration
    )
    cls._mux_audio_segment = (
        patched_mux_audio_segment
    )
    cls._run_finalize_command = (
        patched_run_finalize_command
    )
    cls._finalize_session = (
        patched_finalize_session
    )
    cls._cleanup_session = (
        patched_cleanup
    )

    _INSTALLED = True
