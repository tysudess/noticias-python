from __future__ import annotations

from datetime import datetime
import os
import subprocess
import time

from PySide6.QtCore import QRect
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


def _display_input(rect: QRect) -> str:
    display = (os.environ.get("DISPLAY") or "").strip()

    if not display:
        raise RuntimeError(
            "DISPLAY não está definido para a sessão X11."
        )

    return f"{display}+{rect.x()},{rect.y()}"


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

    patched._central_linux_x11 = True
    cls._load_audio_devices = patched


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

            self._capture_overlay.hide()
            self.floating.hide()

            self.power_button.setText("⏻  LIGAR")
            self._apply_state(
                self.OFF,
                "Gravador de Tela desligado.",
            )
            return

        session = linux_session_type()

        if session == "wayland":
            self.power_button.blockSignals(True)
            self.power_button.setChecked(False)
            self.power_button.blockSignals(False)
            self._module_enabled = False

            self._apply_state(
                self.OFF,
                "Wayland detectado. A captura requer "
                "autorização pelo portal ScreenCast/PipeWire.",
            )

            QMessageBox.information(
                self,
                "Gravador de Tela — Wayland",
                "Esta sessão usa Wayland.\n\n"
                "A captura precisa passar pelo portal ScreenCast "
                "do sistema, com autorização explícita do usuário.\n\n"
                "O backend X11 já está ativo nesta versão; "
                "o portal Wayland será conectado na próxima etapa.",
            )
            return

        if session != "x11" or not os.environ.get("DISPLAY"):
            self.power_button.blockSignals(True)
            self.power_button.setChecked(False)
            self.power_button.blockSignals(False)
            self._module_enabled = False

            self._apply_state(
                self.OFF,
                "Não foi possível identificar uma sessão X11 "
                "compatível para captura.",
            )
            return

        if not self.ffmpeg.is_file():
            self.power_button.blockSignals(True)
            self.power_button.setChecked(False)
            self.power_button.blockSignals(False)
            self._module_enabled = False

            QMessageBox.critical(
                self,
                "FFmpeg não encontrado",
                "O binário FFmpeg do Ubuntu não foi encontrado.",
            )
            return

        self._module_enabled = True
        self.power_button.setText("⏻  DESLIGAR")

        self._refresh_screens()
        self._load_audio_devices()

        self._apply_state(
            self.IDLE,
            "Gravador Ubuntu X11 ligado e pronto.",
        )

        self._update_capture_labels()
        self._update_capture_overlay()

        self.floating.show()
        self.floating.raise_()

    patched._central_linux_x11 = True
    cls._toggle_module = patched


def _patch_start_segment(cls) -> None:
    original = cls._start_segment

    def patched(self) -> bool:
        if not is_linux():
            return original(self)

        if linux_session_type() != "x11":
            self.status_text.setText(
                "Captura de vídeo Linux disponível somente "
                "para X11 nesta versão."
            )
            return False

        if self._session_dir is None:
            return False

        segment_number = len(self._segments) + 1
        segment = (
            self._session_dir
            / f"segment_{segment_number:03d}.mp4"
        )
        audio_path = (
            self._session_dir
            / f"audio_{segment_number:03d}.wav"
        )

        rect = self._capture_rect()
        fps = self._fps()
        crf = self._crf()

        audio_started_at = None
        self._audio_engine = None

        if self._session_audio_device is not None:
            try:
                recorder = LinuxPulseSegmentRecorder(
                    self._session_audio_device,
                    audio_path,
                    self.ffmpeg,
                )
                recorder.start()

                self._audio_engine = recorder
                audio_started_at = (
                    recorder.first_callback_at
                    or recorder.started_at
                    or time.perf_counter()
                )
            except Exception as exc:
                self.audio_status.setText(
                    f"Falha ao iniciar áudio Linux: {exc}"
                )
                self.status_text.setText(
                    "A gravação não iniciou porque "
                    "o áudio selecionado falhou."
                )
                return False

        try:
            input_name = _display_input(rect)
        except Exception as exc:
            self._stop_audio_engine()
            self.status_text.setText(str(exc))
            return False

        command = [
            str(self.ffmpeg),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-thread_queue_size",
            "1024",
            "-f",
            "x11grab",
            "-framerate",
            str(fps),
            "-draw_mouse",
            "1" if self.draw_mouse.isChecked() else "0",
            "-video_size",
            f"{rect.width()}x{rect.height()}",
            "-i",
            input_name,
            "-map",
            "0:v:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
        ]

        target_size = (
            self._session_output_size
            or (rect.width(), rect.height())
        )

        target_w = max(2, int(target_size[0]))
        target_h = max(2, int(target_size[1]))

        if target_w % 2:
            target_w -= 1
        if target_h % 2:
            target_h -= 1

        command += [
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
            str(fps),
            "-movflags",
            "+faststart",
            str(segment),
        ]

        try:
            # No X11 a moldura é escondida para não aparecer no vídeo.
            self._capture_overlay.hide()
            QApplication.processEvents()

            log_path = self.logs_dir / "screen_recorder.log"
            self._log_handle = open(log_path, "ab", buffering=0)

            self._log_handle.write(
                (
                    "\n\n=== "
                    + datetime.now().isoformat()
                    + " ===\n"
                    + " ".join(command)
                    + "\n"
                ).encode(
                    "utf-8",
                    errors="ignore",
                )
            )

            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self._log_handle,
                start_new_session=True,
            )

            video_started_at = time.perf_counter()
            self._segment_started_at = time.monotonic()

        except Exception as exc:
            self._stop_audio_engine()
            self._close_log()
            self._update_capture_overlay()
            self.status_text.setText(
                f"Falha ao iniciar: {exc}"
            )
            return False

        if self._process.poll() is not None:
            self._stop_audio_engine()
            self._close_log()
            self._update_capture_overlay()
            return False

        audio_offset = 0.0

        if (
            self._session_audio_device is not None
            and audio_started_at is not None
        ):
            audio_offset = audio_started_at - video_started_at

        self._segments.append(segment)
        self._audio_segments.append(
            audio_path
            if self._session_audio_device is not None
            else None
        )
        self._segment_audio_offsets.append(audio_offset)

        if self._session_audio_device is None:
            self.audio_value.setText("Sem áudio")
        else:
            self.audio_value.setText(
                "Sistema"
                if self._session_audio_device.kind == "system"
                else "Microfone"
            )

        return True

    patched._central_linux_x11 = True
    cls._start_segment = patched


def _patch_finish_segment(cls) -> None:
    original = cls._finish_current_segment

    def patched(self) -> None:
        original(self)

        if (
            is_linux()
            and self._module_enabled
            and not self._closing
        ):
            try:
                self._update_capture_overlay()
            except Exception:
                pass

    patched._central_linux_x11 = True
    cls._finish_current_segment = patched


def install_linux_screen_recorder_patch() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    from monitor_noticias.ui.screen_recorder_page import ScreenRecorderPage

    _patch_audio(ScreenRecorderPage)
    _patch_toggle(ScreenRecorderPage)
    _patch_start_segment(ScreenRecorderPage)
    _patch_finish_segment(ScreenRecorderPage)

    _INSTALLED = True
