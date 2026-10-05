from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
import threading
import time

from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QPolygon
from PySide6.QtWidgets import QApplication, QMessageBox

from monitor_noticias.platform.current import (
    is_linux,
    linux_session_type,
)
from monitor_noticias.ui.screen_recorder_linux import (
    LinuxPulseSegmentRecorder,
    list_linux_audio_devices,
)


_INSTALLED = False
_POST_SYNC_INSTALLED = False


def _append_log(page, message: str) -> None:
    try:
        path = Path(page.logs_dir) / "screen_recorder.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open(
            "a",
            encoding="utf-8",
            errors="ignore",
        ) as handle:
            handle.write(
                f"[LINUX V101] {datetime.now().isoformat()} | {message}\n"
            )
    except Exception:
        pass


def _ffmpeg_supports_libx264(ffmpeg: Path) -> tuple[bool, str]:
    """Valida somente o codificador; não toca no DISPLAY do usuário."""

    try:
        cp = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-encoders",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return False, f"não foi possível consultar o FFmpeg: {exc}"

    output = cp.stdout or ""

    if cp.returncode != 0:
        return False, (
            f"FFmpeg -encoders retornou código {cp.returncode}: "
            + " ".join(output.split())[-500:]
        )

    if "libx264" not in output.lower():
        return False, "o FFmpeg incluído no portable não possui libx264"

    return True, "libx264 disponível"


def _screen_local_rect(
    screen_geometry: QRect,
    capture_global: QRect,
) -> QRect:
    """Converte uma área global Qt para coordenadas locais do QScreen."""

    visible = QRect(capture_global).normalized().intersected(
        QRect(screen_geometry)
    )

    if visible.isEmpty():
        return QRect()

    return QRect(
        visible.x() - screen_geometry.x(),
        visible.y() - screen_geometry.y(),
        visible.width(),
        visible.height(),
    )


def _logical_capture_geometry(page):
    screen = page._selected_screen()

    if screen is None:
        raise RuntimeError("Nenhum monitor foi detectado pelo Qt.")

    screen_geometry = QRect(screen.geometry())

    if (
        page.mode_combo.currentText() == "Área personalizada"
        and page._region is not None
    ):
        capture_global = QRect(page._region).normalized()
    else:
        capture_global = QRect(screen_geometry)

    capture_global = capture_global.intersected(screen_geometry)

    if capture_global.isEmpty():
        raise RuntimeError(
            "A área selecionada não pertence ao monitor escolhido."
        )

    local_rect = _screen_local_rect(
        screen_geometry,
        capture_global,
    )

    if local_rect.isEmpty():
        raise RuntimeError("A área de captura ficou vazia.")

    return screen, screen_geometry, capture_global, local_rect


class _LinuxQtScreenPipeRecorder:
    """Captura QScreen e entrega BGRA ao FFmpeg por um pipe dedicado.

    V98 deixava o próprio FFmpeg abrir o DISPLAY via x11grab. No computador
    real isso travava antes da gravação começar. A Central, porém, já possui
    acesso válido ao monitor através do Qt/XCB. V101 reutiliza esse acesso e
    deixa o FFmpeg responsável apenas pela codificação H.264.

    O vídeo entra por um descritor extra (pipe:N). O stdin do FFmpeg continua
    livre para o comando ``q`` usado pelo fluxo existente de pausa/finalização.
    """

    def __init__(
        self,
        *,
        screen,
        screen_geometry: QRect,
        capture_global: QRect,
        local_rect: QRect,
        output: Path,
        ffmpeg: Path,
        fps: int,
        crf: int,
        target_size: tuple[int, int],
        draw_mouse: bool,
        log_handle,
    ) -> None:
        self.screen = screen
        self.screen_geometry = QRect(screen_geometry)
        self.capture_global = QRect(capture_global)
        self.local_rect = QRect(local_rect)
        self.output = Path(output)
        self.ffmpeg = Path(ffmpeg)
        self.fps = max(1, min(60, int(fps)))
        self.crf = int(crf)
        self.target_size = target_size
        self.draw_mouse = bool(draw_mouse)
        self.log_handle = log_handle

        self.process: subprocess.Popen[bytes] | None = None
        self.started_at: float | None = None
        self.error: str | None = None

        self._source_width = 0
        self._source_height = 0
        self._latest_frame: bytes | None = None
        self._frame_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._writer_thread: threading.Thread | None = None
        self._write_fd: int | None = None
        self._capture_failures = 0

        self._timer = QTimer()
        # Atualizar a imagem no máximo a 30 fps evita travar a GUI em 60 fps.
        # O writer mantém a cadência escolhida e repete o último frame quando
        # necessário, preservando a duração real da gravação.
        refresh_fps = min(self.fps, 30)
        self._timer.setInterval(
            max(10, int(round(1000.0 / max(1, refresh_fps))))
        )
        self._timer.timeout.connect(self._capture_tick)

    def _log(self, message: str) -> None:
        try:
            self.log_handle.write(
                ("[QT SCREEN PIPE] " + message + "\n").encode(
                    "utf-8",
                    errors="ignore",
                )
            )
        except Exception:
            pass

    def _grab_image(self) -> QImage:
        rect = self.local_rect

        pixmap = self.screen.grabWindow(
            0,
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
        )

        if pixmap.isNull():
            raise RuntimeError(
                "O Qt não conseguiu capturar o monitor X11 selecionado."
            )

        image = pixmap.toImage().convertToFormat(
            QImage.Format.Format_RGB32
        )

        if image.isNull() or image.width() <= 0 or image.height() <= 0:
            raise RuntimeError("O Qt retornou um frame de tela vazio.")

        if self._source_width and self._source_height:
            if (
                image.width() != self._source_width
                or image.height() != self._source_height
            ):
                image = image.scaled(
                    self._source_width,
                    self._source_height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )

        if self.draw_mouse:
            self._draw_cursor(image)

        return image

    def _draw_cursor(self, image: QImage) -> None:
        cursor = QCursor.pos()

        if not self.capture_global.contains(cursor):
            return

        logical_w = max(1, self.capture_global.width())
        logical_h = max(1, self.capture_global.height())

        x = int(
            (cursor.x() - self.capture_global.x())
            * image.width()
            / logical_w
        )
        y = int(
            (cursor.y() - self.capture_global.y())
            * image.height()
            / logical_h
        )

        # Seta simples e legível. O QScreen normalmente não inclui o cursor.
        points = QPolygon(
            [
                QPoint(x, y),
                QPoint(x, y + 18),
                QPoint(x + 5, y + 13),
                QPoint(x + 10, y + 22),
                QPoint(x + 14, y + 20),
                QPoint(x + 9, y + 11),
                QPoint(x + 17, y + 11),
            ]
        )

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#101010"), 2))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPolygon(points)
        painter.end()

    @staticmethod
    def _image_bytes(image: QImage) -> bytes:
        width = int(image.width())
        row_size = width * 4
        stride = int(image.bytesPerLine())
        size = int(image.sizeInBytes())

        raw = bytes(image.constBits()[:size])

        if stride == row_size:
            return raw

        return b"".join(
            raw[offset:offset + row_size]
            for offset in range(0, stride * image.height(), stride)
        )

    def _capture_frame(self) -> tuple[bytes, int, int]:
        image = self._grab_image()
        return (
            self._image_bytes(image),
            int(image.width()),
            int(image.height()),
        )

    @staticmethod
    def _write_all(fd: int, payload: bytes) -> None:
        view = memoryview(payload)
        sent = 0

        while sent < len(view):
            written = os.write(fd, view[sent:])
            if written <= 0:
                raise BrokenPipeError("pipe de vídeo fechado")
            sent += written

    def _writer_loop(self) -> None:
        frame_period = 1.0 / float(self.fps)
        next_frame = time.perf_counter()
        fd = self._write_fd

        try:
            while (
                not self._stop_event.is_set()
                and fd is not None
            ):
                process = self.process

                if process is None or process.poll() is not None:
                    break

                with self._frame_lock:
                    frame = self._latest_frame

                if frame:
                    self._write_all(fd, frame)

                next_frame += frame_period
                delay = next_frame - time.perf_counter()

                if delay > 0:
                    self._stop_event.wait(delay)
                elif delay < -(frame_period * 2.0):
                    # Se o encoder atrasar, volta ao relógio real sem criar
                    # uma fila crescente de frames antigos.
                    next_frame = time.perf_counter()

        except (BrokenPipeError, OSError) as exc:
            if not self._stop_event.is_set():
                self.error = f"{exc.__class__.__name__}: {exc}"
                self._log("writer encerrado: " + self.error)

        except Exception as exc:
            self.error = f"{exc.__class__.__name__}: {exc}"
            self._log("writer falhou: " + self.error)

        finally:
            self._close_write_fd()

    def _capture_tick(self) -> None:
        process = self.process

        if process is None or process.poll() is not None:
            self.stop()
            return

        try:
            frame, width, height = self._capture_frame()

            if (
                width != self._source_width
                or height != self._source_height
            ):
                raise RuntimeError(
                    "O tamanho do frame Qt mudou durante a gravação."
                )

            with self._frame_lock:
                self._latest_frame = frame

            self._capture_failures = 0

        except Exception as exc:
            self._capture_failures += 1
            self._log(
                "falha ao atualizar frame "
                f"({self._capture_failures}/3): "
                f"{exc.__class__.__name__}: {exc}"
            )

            if self._capture_failures >= 3:
                self.error = f"{exc.__class__.__name__}: {exc}"
                self.stop()

    def _close_write_fd(self) -> None:
        fd = self._write_fd
        self._write_fd = None

        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def start(self) -> None:
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
            "-thread_queue_size",
            "1024",
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

        self._log("comando: " + " ".join(command))
        self._log(
            "captura Qt: "
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

        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            name="CentralQtScreenPipe",
            daemon=True,
        )
        self._writer_thread.start()
        self._timer.start()

        # O writer já está entregando frames; esta janela curta detecta erro
        # imediato de codec/pipe sem executar qualquer acesso x11grab.
        deadline = time.monotonic() + 0.25
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            QApplication.processEvents()
            time.sleep(0.015)

        if self.process.poll() is not None:
            code = self.process.returncode
            self.stop()
            raise RuntimeError(
                "FFmpeg encerrou ao iniciar a codificação Qt "
                f"(código {code}); consulte screen_recorder.log."
            )

    def stop(self) -> None:
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass

        self._stop_event.set()
        self._close_write_fd()


def _patch_audio(cls) -> None:
    original = cls._load_audio_devices

    def patched(self) -> None:
        if not is_linux():
            return original(self)

        previous = self.audio_combo.currentData()

        self.audio_combo.blockSignals(True)
        self.audio_combo.clear()
        self.audio_combo.addItem("Sem áudio", "none")
        self._audio_devices = {}

        devices, diagnostic = list_linux_audio_devices()

        try:
            (
                self.logs_dir
                / "screen_recorder_audio_devices.log"
            ).write_text(
                diagnostic,
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            pass

        system_index = -1
        first_mic_index = -1

        for device in devices:
            self._audio_devices[device.key] = device

            if device.kind == "system":
                label = (
                    "Áudio do sistema • PipeWire/PulseAudio "
                    f"({device.name})"
                )
            else:
                label = f"Microfone • {device.name}"

            self.audio_combo.addItem(label, device.key)
            index = self.audio_combo.count() - 1

            if device.kind == "system" and system_index < 0:
                system_index = index

            if device.kind == "microphone" and first_mic_index < 0:
                first_mic_index = index

        self.audio_combo.blockSignals(False)
        self._audio_loaded = True

        old_index = (
            self.audio_combo.findData(previous)
            if previous and previous != "none"
            else -1
        )

        if old_index >= 1:
            selected = old_index
        elif system_index >= 1:
            selected = system_index
        elif first_mic_index >= 1:
            selected = first_mic_index
        else:
            selected = 0

        self.audio_combo.setCurrentIndex(selected)

        if system_index >= 0:
            self.audio_status.setText(
                "Áudio do sistema detectado via PipeWire/PulseAudio."
            )
        elif first_mic_index >= 0:
            self.audio_status.setText(
                "Microfone detectado. Nenhuma fonte monitor "
                "de áudio do sistema foi encontrada."
            )
        else:
            self.audio_status.setText(
                "Nenhuma fonte de áudio Linux foi detectada. "
                "O vídeo pode ser gravado sem áudio."
            )

        self._audio_selection_changed(
            self.audio_combo.currentIndex()
        )

    patched._central_linux_qt_capture_v101 = True
    cls._load_audio_devices = patched


def _set_toggle_off(self, message: str) -> None:
    self.power_button.blockSignals(True)
    self.power_button.setChecked(False)
    self.power_button.blockSignals(False)
    self._module_enabled = False
    self._apply_state(self.OFF, message)


def _patch_toggle(cls) -> None:
    original = cls._toggle_module

    def patched(self, enabled: bool) -> None:
        if not is_linux():
            return original(self, enabled)

        if enabled == self._module_enabled:
            return

        if not enabled and self.is_active:
            answer = QMessageBox.question(
                self,
                "Desligar Gravador de Tela",
                "Existe uma gravação em andamento. "
                "Deseja finalizar a gravação e desligar o módulo?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                self.power_button.blockSignals(True)
                self.power_button.setChecked(True)
                self.power_button.blockSignals(False)
                return

        if not enabled:
            self._module_enabled = False
            self._close_region_editor()

            if self._state in {
                self.RECORDING,
                self.PAUSED,
                self.STARTING,
            }:
                self.stop_recording()

            engine = getattr(self, "_linux_video_engine", None)
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
                self._linux_video_engine = None

            self._capture_overlay.hide()
            self.floating.hide()

            self.power_button.setText("⏻  LIGAR")
            self._apply_state(
                self.OFF,
                "Gravador de Tela desligado.",
            )
            return

        session = linux_session_type()
        display = (os.environ.get("DISPLAY") or "").strip()
        wayland_display = (
            os.environ.get("WAYLAND_DISPLAY") or ""
        ).strip()

        _append_log(
            self,
            "ativação V101: "
            f"session={session} DISPLAY={display!r} "
            f"WAYLAND_DISPLAY={wayland_display!r} ffmpeg={self.ffmpeg}",
        )

        if session == "wayland":
            _set_toggle_off(
                self,
                "Wayland detectado. Esta versão do gravador usa a captura "
                "Qt/X11 da sessão gráfica.",
            )

            QMessageBox.information(
                self,
                "Gravador de Tela — Wayland",
                "Esta sessão usa Wayland. A captura completa da área de "
                "trabalho exige autorização pelo portal ScreenCast/PipeWire.\n\n"
                "Para usar o gravador desta versão, entre em uma sessão "
                "‘Ubuntu on Xorg’.",
            )
            return

        if session != "x11" or not display:
            _set_toggle_off(
                self,
                "Não foi possível identificar uma sessão X11 com DISPLAY.",
            )
            return

        ffmpeg = Path(self.ffmpeg)

        if not ffmpeg.is_file():
            _set_toggle_off(
                self,
                "FFmpeg do Ubuntu não foi encontrado.",
            )

            QMessageBox.critical(
                self,
                "FFmpeg não encontrado",
                f"O binário FFmpeg não foi encontrado em:\n{self.ffmpeg}",
            )
            return

        ok, diagnostic = _ffmpeg_supports_libx264(ffmpeg)
        _append_log(self, "validação codec: " + diagnostic)

        if not ok:
            _set_toggle_off(
                self,
                "FFmpeg não possui o codificador H.264 necessário.",
            )
            QMessageBox.critical(
                self,
                "FFmpeg incompatível",
                diagnostic + "\n\nDetalhes: logs/screen_recorder.log",
            )
            return

        # V101: LIGAR não tenta mais abrir DISPLAY pelo FFmpeg. O frame real
        # só é capturado quando REC é pressionado, via QScreen/Qt.
        self._module_enabled = True
        self.power_button.setText("⏻  DESLIGAR")

        self._refresh_screens()
        self._load_audio_devices()

        self._apply_state(
            self.IDLE,
            "Gravador Ubuntu X11 pronto — captura Qt + codificação FFmpeg.",
        )

        self._update_capture_labels()
        self._update_capture_overlay()

        self.floating.show()
        self.floating.raise_()

    patched._central_linux_qt_capture_v101 = True
    cls._toggle_module = patched


def _patch_start_segment(cls) -> None:
    original = cls._start_segment

    def patched(self) -> bool:
        if not is_linux():
            return original(self)

        if linux_session_type() != "x11":
            self.status_text.setText(
                "Captura Linux desta versão requer sessão X11/Xorg."
            )
            _append_log(
                self,
                "segmento recusado: sessão não é X11",
            )
            return False

        if self._session_dir is None:
            _append_log(
                self,
                "segmento recusado: _session_dir ausente",
            )
            return False

        previous_engine = getattr(
            self,
            "_linux_video_engine",
            None,
        )
        if previous_engine is not None:
            try:
                previous_engine.stop()
            except Exception:
                pass

        segment_number = len(self._segments) + 1
        segment = (
            self._session_dir
            / f"segment_{segment_number:03d}.mp4"
        )
        audio_path = (
            self._session_dir
            / f"audio_{segment_number:03d}.wav"
        )

        fps = self._fps()
        crf = self._crf()

        audio_started_at = None
        self._audio_engine = None
        active_audio_device = self._session_audio_device

        if active_audio_device is not None:
            try:
                recorder = LinuxPulseSegmentRecorder(
                    active_audio_device,
                    audio_path,
                    Path(self.ffmpeg),
                    Path(self.logs_dir) / "screen_recorder.log",
                )
                recorder.start()

                self._audio_engine = recorder
                audio_started_at = (
                    recorder.first_callback_at
                    or recorder.started_at
                    or time.perf_counter()
                )
            except Exception as exc:
                _append_log(
                    self,
                    "áudio falhou; continuando sem áudio: "
                    f"{exc.__class__.__name__}: {exc}",
                )
                self.audio_status.setText(
                    "Áudio Linux falhou; gravação seguirá sem áudio. "
                    "Consulte screen_recorder.log."
                )
                self._stop_audio_engine()
                active_audio_device = None

        try:
            (
                screen,
                screen_geometry,
                capture_global,
                local_rect,
            ) = _logical_capture_geometry(self)
        except Exception as exc:
            self._stop_audio_engine()
            self.status_text.setText(str(exc))
            _append_log(
                self,
                f"geometria Qt inválida: {exc}",
            )
            return False

        target_size = (
            self._session_output_size
            or (
                max(2, capture_global.width()),
                max(2, capture_global.height()),
            )
        )

        engine = None

        try:
            self._capture_overlay.hide()
            QApplication.processEvents()

            log_path = Path(self.logs_dir) / "screen_recorder.log"
            self._log_handle = open(log_path, "ab", buffering=0)

            self._log_handle.write(
                (
                    "\n\n=== "
                    + datetime.now().isoformat()
                    + " | VIDEO QT/X11 V101 ===\n"
                ).encode(
                    "utf-8",
                    errors="ignore",
                )
            )

            engine = _LinuxQtScreenPipeRecorder(
                screen=screen,
                screen_geometry=screen_geometry,
                capture_global=capture_global,
                local_rect=local_rect,
                output=segment,
                ffmpeg=Path(self.ffmpeg),
                fps=fps,
                crf=crf,
                target_size=target_size,
                draw_mouse=self.draw_mouse.isChecked(),
                log_handle=self._log_handle,
            )
            engine.start()

            self._linux_video_engine = engine
            self._process = engine.process

            video_started_at = (
                engine.started_at
                or time.perf_counter()
            )
            self._segment_started_at = time.monotonic()

        except Exception as exc:
            self._stop_audio_engine()

            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass

            self._linux_video_engine = None
            self._process = None
            self._close_log()
            self._update_capture_overlay()
            self.status_text.setText(
                f"Falha ao iniciar captura Qt: {exc}"
            )
            _append_log(
                self,
                "captura Qt falhou: "
                f"{exc.__class__.__name__}: {exc}",
            )
            return False

        audio_offset = 0.0

        if (
            active_audio_device is not None
            and audio_started_at is not None
        ):
            audio_offset = audio_started_at - video_started_at

        self._segments.append(segment)
        self._audio_segments.append(
            audio_path
            if active_audio_device is not None
            else None
        )
        self._segment_audio_offsets.append(audio_offset)

        if active_audio_device is None:
            self.audio_value.setText("Sem áudio")
        else:
            self.audio_value.setText(
                "Sistema"
                if active_audio_device.kind == "system"
                else "Microfone"
            )

        _append_log(
            self,
            "segmento Qt iniciado: "
            f"monitor={screen.name()} "
            f"area={capture_global.x()},{capture_global.y()} "
            f"{capture_global.width()}x{capture_global.height()} "
            f"fps={fps} audio={'sim' if active_audio_device else 'não'}",
        )
        return True

    patched._central_linux_qt_capture_v101 = True
    cls._start_segment = patched


def _patch_runtime(cls) -> None:
    original = cls._update_runtime

    def patched(self) -> None:
        original(self)

        if not is_linux():
            return

        engine = getattr(
            self,
            "_linux_video_engine",
            None,
        )

        if engine is None:
            return

        process = getattr(engine, "process", None)

        if process is None or process.poll() is not None:
            try:
                engine.stop()
            except Exception:
                pass

            if getattr(self, "_process", None) is not process:
                self._linux_video_engine = None

            if getattr(engine, "error", None):
                _append_log(
                    self,
                    "engine Qt encerrou com erro: "
                    + str(engine.error),
                )

    patched._central_linux_qt_capture_v101 = True
    cls._update_runtime = patched



def install_linux_screen_recorder_post_sync_patch() -> None:
    """Fecha o pipe de frames antes de o patch V95 aguardar o FFmpeg.

    O V95 envia ``q`` e espera o processo terminar. No backend V101 o fluxo de
    vídeo vem de um pipe separado; fechá-lo primeiro entrega EOF ao demuxer e
    garante que pausa, troca de área e STOP não fiquem aguardando um read.
    """

    global _POST_SYNC_INSTALLED

    if _POST_SYNC_INSTALLED:
        return

    if not is_linux():
        _POST_SYNC_INSTALLED = True
        return

    from monitor_noticias.ui.screen_recorder_page import ScreenRecorderPage

    cls = ScreenRecorderPage
    original_finish = cls._finish_current_segment
    original_cleanup = cls._cleanup_session

    def patched_finish(self) -> None:
        engine = getattr(
            self,
            "_linux_video_engine",
            None,
        )

        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

        try:
            original_finish(self)
        finally:
            if getattr(self, "_linux_video_engine", None) is engine:
                self._linux_video_engine = None

    def patched_cleanup(self) -> None:
        engine = getattr(
            self,
            "_linux_video_engine",
            None,
        )

        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

        self._linux_video_engine = None
        original_cleanup(self)

    patched_finish._central_linux_qt_post_sync_v101 = True
    patched_cleanup._central_linux_qt_post_sync_v101 = True

    cls._finish_current_segment = patched_finish
    cls._cleanup_session = patched_cleanup

    _POST_SYNC_INSTALLED = True

def install_linux_screen_recorder_patch() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    from monitor_noticias.ui.screen_recorder_page import ScreenRecorderPage

    _patch_audio(ScreenRecorderPage)
    _patch_toggle(ScreenRecorderPage)
    _patch_start_segment(ScreenRecorderPage)
    _patch_runtime(ScreenRecorderPage)

    _INSTALLED = True
