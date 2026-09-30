from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
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
_X11_PREFLIGHT_CACHE: dict[tuple[str, str], tuple[bool, str]] = {}


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
                f"[LINUX V98] {datetime.now().isoformat()} | {message}\n"
            )
    except Exception:
        pass


def _display_input(rect: QRect) -> str:
    display = (os.environ.get("DISPLAY") or "").strip()

    if not display:
        raise RuntimeError(
            "DISPLAY não está definido para a sessão X11."
        )

    return f"{display}+{rect.x()},{rect.y()}"


def _ffmpeg_supports_x11grab(ffmpeg: Path) -> tuple[bool, str]:
    try:
        cp = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-devices",
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
        return False, f"não foi possível consultar FFmpeg: {exc}"

    output = cp.stdout or ""

    if cp.returncode != 0:
        return False, (
            f"FFmpeg -devices retornou código {cp.returncode}: "
            + " ".join(output.split())[-500:]
        )

    if "x11grab" not in output.lower():
        return False, (
            "o FFmpeg incluído no portable não possui o dispositivo x11grab"
        )

    return True, "x11grab disponível"


def _probe_x11_capture(ffmpeg: Path) -> tuple[bool, str]:
    """Executa uma captura real de 1 frame para validar DISPLAY/Xauthority."""

    display = (os.environ.get("DISPLAY") or "").strip()
    key = (str(ffmpeg), display)

    cached = _X11_PREFLIGHT_CACHE.get(key)
    if cached is not None:
        return cached

    supported, detail = _ffmpeg_supports_x11grab(ffmpeg)
    if not supported:
        result = (False, detail)
        _X11_PREFLIGHT_CACHE[key] = result
        return result

    if not display:
        result = (False, "DISPLAY não está definido")
        _X11_PREFLIGHT_CACHE[key] = result
        return result

    command = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "x11grab",
        "-framerate",
        "1",
        "-video_size",
        "16x16",
        "-i",
        f"{display}+0,0",
        "-frames:v",
        "1",
        "-f",
        "null",
        "-",
    ]

    try:
        cp = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=6,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result = (
            False,
            "o teste x11grab excedeu 6 s ao acessar o DISPLAY",
        )
        _X11_PREFLIGHT_CACHE[key] = result
        return result
    except Exception as exc:
        result = (
            False,
            f"falha ao executar o teste x11grab: {exc}",
        )
        _X11_PREFLIGHT_CACHE[key] = result
        return result

    if cp.returncode != 0:
        tail = " ".join((cp.stdout or "").split())[-700:]
        result = (
            False,
            f"x11grab não conseguiu ler {display} (código {cp.returncode}): {tail}",
        )
        _X11_PREFLIGHT_CACHE[key] = result
        return result

    result = (True, f"x11grab validado em {display}")
    _X11_PREFLIGHT_CACHE[key] = result
    return result


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
            "ativação: "
            f"session={session} DISPLAY={display!r} "
            f"WAYLAND_DISPLAY={wayland_display!r} ffmpeg={self.ffmpeg}",
        )

        if session == "wayland":
            _set_toggle_off(
                self,
                "Wayland detectado. O backend x11grab não pode gravar "
                "com segurança a área de trabalho Wayland completa.",
            )

            QMessageBox.information(
                self,
                "Gravador de Tela — Wayland",
                "Esta sessão usa Wayland. O x11grab do FFmpeg só captura "
                "uma sessão X11 real; usar o DISPLAY do XWayland poderia "
                "gerar vídeo incompleto ou preto.\n\n"
                "Para gravação completa no Ubuntu, entre em uma sessão "
                "‘Ubuntu on Xorg’. O diagnóstico foi gravado em "
                "logs/screen_recorder.log.",
            )
            return

        if session != "x11" or not display:
            _set_toggle_off(
                self,
                "Não foi possível identificar uma sessão X11 com DISPLAY.",
            )
            return

        if not Path(self.ffmpeg).is_file():
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

        ok, diagnostic = _probe_x11_capture(
            Path(self.ffmpeg)
        )
        _append_log(self, "preflight x11: " + diagnostic)

        if not ok:
            _set_toggle_off(
                self,
                "FFmpeg/x11grab não conseguiu acessar a sessão gráfica.",
            )
            QMessageBox.critical(
                self,
                "Falha no x11grab",
                diagnostic
                + "\n\nDetalhes: logs/screen_recorder.log",
            )
            return

        self._module_enabled = True
        self.power_button.setText("⏻  DESLIGAR")

        self._refresh_screens()
        self._load_audio_devices()

        self._apply_state(
            self.IDLE,
            "Gravador Ubuntu X11 ligado e validado pelo FFmpeg.",
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
                "Captura Linux requer sessão X11."
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
                # Áudio não pode impedir uma captura de vídeo válida. Mantém
                # o erro visível/logado e segue em vídeo-only neste segmento.
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
            input_name = _display_input(rect)
        except Exception as exc:
            self._stop_audio_engine()
            self.status_text.setText(str(exc))
            _append_log(
                self,
                f"DISPLAY inválido: {exc}",
            )
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
            self._capture_overlay.hide()
            QApplication.processEvents()

            log_path = Path(self.logs_dir) / "screen_recorder.log"
            self._log_handle = open(log_path, "ab", buffering=0)

            self._log_handle.write(
                (
                    "\n\n=== "
                    + datetime.now().isoformat()
                    + " | VIDEO X11 V98 ===\n"
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

            # Captura erros de abertura do DISPLAY/codec que normalmente surgem
            # logo depois do Popen e antes do primeiro frame.
            deadline = time.monotonic() + 0.30
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    break
                QApplication.processEvents()
                time.sleep(0.025)

        except Exception as exc:
            self._stop_audio_engine()
            self._close_log()
            self._update_capture_overlay()
            self.status_text.setText(
                f"Falha ao iniciar: {exc}"
            )
            _append_log(
                self,
                f"Popen vídeo falhou: {exc.__class__.__name__}: {exc}",
            )
            return False

        if self._process.poll() is not None:
            code = self._process.returncode
            self._process = None
            self._stop_audio_engine()
            self._close_log()
            self._update_capture_overlay()
            self.status_text.setText(
                "FFmpeg encerrou ao abrir x11grab "
                f"(código {code}). Consulte screen_recorder.log."
            )
            _append_log(
                self,
                f"FFmpeg vídeo encerrou na partida; código={code}",
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
            "segmento iniciado: "
            f"DISPLAY={os.environ.get('DISPLAY', '')} "
            f"rect={rect.x()},{rect.y()} {rect.width()}x{rect.height()} "
            f"fps={fps} audio={'sim' if active_audio_device else 'não'}",
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
