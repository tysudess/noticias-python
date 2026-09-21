from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from PySide6.QtMultimedia import QMediaPlayer

from . import advanced_editor as base


class AdvancedVideoEditorWidget300(base.AdvancedVideoEditorWidget):
    """Editor v3.0 com undo e reprodução contínua robusta da timeline."""

    UNDO_LIMIT = 50

    def __init__(self, videos_dir, ffmpeg_exe, ffprobe_exe, parent=None):
        self._undo_stack = []
        self._transitioning_clip = False
        self._transition_serial = 0
        self._transition_target_index = -1
        self._transition_retry_count = 0
        super().__init__(videos_dir, ffmpeg_exe, ffprobe_exe, parent)

        self.btn_undo = QPushButton('↶  VOLTAR / DESFAZER  (Ctrl+Z)')
        self.btn_undo.setToolTip(
            'Desfazer a última exclusão, corte ou ajuste de trecho da timeline (Ctrl+Z).'
        )
        try:
            self.btn_undo.setStyleSheet(self.btn_reset_visual.styleSheet())
            header = self.btn_reset_visual.parentWidget()
            if header and header.layout():
                header.layout().addWidget(self.btn_undo)
        except Exception:
            pass
        self.btn_undo.clicked.connect(self.undo_last_action)

        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.undo_shortcut.activated.connect(self._undo_shortcut_activated)
        self._update_undo_control()

    # --------------------------------------------------------------
    # Reprodução contínua da timeline
    # --------------------------------------------------------------

    @staticmethod
    def _same_media_path(first, second):
        try:
            return Path(first).resolve() == Path(second).resolve()
        except Exception:
            return str(first) == str(second)

    def _invalidate_transition(self):
        # Invalida callbacks antigos para que nunca retomem a reprodução após
        # uma pausa manual ou depois do fim da timeline.
        self._transition_serial += 1
        self._transitioning_clip = False
        self._transition_target_index = -1
        self._transition_retry_count = 0

    def pause_sequence(self):
        self._invalidate_transition()
        self.sequence_playing = False
        self._pending_autoplay = False
        self.player.pause()
        self.btn_play.setText('▶ PLAY')

    def _finish_continuous_sequence(self):
        self._invalidate_transition()
        self.sequence_playing = False
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self.player.pause()
        self.global_playhead_ms = self.total_duration_ms()
        self._update_global_ui(auto_scroll=True)
        self.btn_play.setText('▶ PLAY')
        self.status.setText('Fim da timeline.')

    def _prepare_transition_target(self, next_index):
        if not (0 <= next_index < len(self.clips)):
            return None

        clip = self.clips[next_index]
        target_path = str(clip['path'])
        source_ms = int(clip['start_ms'])

        self.selected_index = next_index
        self.timeline.set_selected_index(next_index)
        self.global_playhead_ms = self.clip_global_start(next_index)

        # Atualiza os controles sem transformar a transição em pausa.
        self.load_selected_clip(False)

        self.preview_clip_index = next_index
        self.preview_clip_end_source_ms = int(clip['end_ms'])
        self._pending_seek_ms = source_ms
        self._pending_autoplay = True
        self._update_global_ui(auto_scroll=True)

        return target_path, source_ms

    def _advance_continuous_sequence(self):
        """Avança do vídeo N para N+1 sem parar a timeline.

        A implementação anterior dependia de LoadedMedia/BufferedMedia. Em
        alguns backends do Windows esse evento pode não chegar a tempo na troca
        de source. O fallback antigo apenas soltava o bloqueio, mas não chamava
        PLAY novamente. Agora há watchdog ativo de source + seek + play.
        """
        if (
            not self.sequence_playing
            or self._transitioning_clip
            or not self.clips
        ):
            return

        current = int(self.preview_clip_index)
        if not (0 <= current < len(self.clips)):
            mapped = self.map_global(self.global_playhead_ms)
            if not mapped:
                return
            current = int(mapped[0])

        next_index = current + 1
        if next_index >= len(self.clips):
            self._finish_continuous_sequence()
            return

        self._transition_serial += 1
        serial = self._transition_serial
        self._transitioning_clip = True
        self._transition_target_index = next_index
        self._transition_retry_count = 0
        self.sequence_playing = True

        prepared = self._prepare_transition_target(next_index)
        if prepared is None:
            self._finish_continuous_sequence()
            return

        target_path, source_ms = prepared
        self.btn_play.setText('⏸ PAUSAR')
        self.status.setText(
            f'Reprodução contínua • carregando clipe {next_index + 1}/{len(self.clips)}...'
        )

        current_path = (
            self.player.source().toLocalFile()
            if not self.player.source().isEmpty()
            else ''
        )

        # Dois cortes do mesmo arquivo não geram nova carga; fazemos seek/play.
        if current_path and self._same_media_path(current_path, target_path):
            self.player.setPosition(source_ms)
            self.player.play()
        else:
            self.player.setSource(QUrl.fromLocalFile(target_path))

        # Não dependemos somente de mediaStatusChanged. Cada callback verifica
        # o serial atual, então retries antigos são inofensivos.
        for delay in (0, 80, 180, 350, 700, 1200, 2000, 3200):
            QTimer.singleShot(
                delay,
                lambda s=serial: self._ensure_transition_playing(s),
            )

    def _ensure_transition_playing(self, serial):
        if (
            serial != self._transition_serial
            or not self.sequence_playing
            or not self._transitioning_clip
        ):
            return

        index = int(self._transition_target_index)
        if not (0 <= index < len(self.clips)):
            return

        clip = self.clips[index]
        target_path = str(clip['path'])
        source_ms = int(clip['start_ms'])
        end_ms = int(clip['end_ms'])

        current_path = (
            self.player.source().toLocalFile()
            if not self.player.source().isEmpty()
            else ''
        )

        if not current_path or not self._same_media_path(current_path, target_path):
            self.player.setSource(QUrl.fromLocalFile(target_path))
            return

        self.preview_clip_index = index
        self.preview_clip_end_source_ms = end_ms

        pos = int(self.player.position())
        near_target = (
            abs(pos - source_ms) <= 350
            or source_ms <= pos < end_ms
        )
        if not near_target:
            self.player.setPosition(source_ms)

        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.player.play()

        self._transition_retry_count += 1

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._complete_transition(serial)

    def _complete_transition(self, serial):
        if serial != self._transition_serial or not self.sequence_playing:
            return

        index = int(self._transition_target_index)
        if not (0 <= index < len(self.clips)):
            return

        self._transitioning_clip = False
        self._transition_target_index = -1
        self._transition_retry_count = 0
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self.btn_play.setText('⏸ PAUSAR')
        self.status.setText(
            f'Reprodução contínua • clipe {index + 1}/{len(self.clips)}'
        )

    def _monitor_playback(self):
        if (
            not self.sequence_playing
            or not (0 <= self.preview_clip_index < len(self.clips))
        ):
            return

        # Durante a troca, somente o watchdog cuida do player. Assim não há
        # avanço duplo por causa de EndOfMedia do arquivo anterior.
        if self._transitioning_clip:
            return

        clip = self.clips[self.preview_clip_index]
        if self.player.position() >= int(clip['end_ms']) - 140:
            self._advance_continuous_sequence()

    def _media_status_changed(self, status):
        if (
            self._transitioning_clip
            and status == QMediaPlayer.MediaStatus.EndOfMedia
        ):
            # EndOfMedia residual do vídeo anterior não significa fim da
            # timeline. Reforça o PLAY do alvo atual.
            serial = self._transition_serial
            QTimer.singleShot(
                0,
                lambda s=serial: self._ensure_transition_playing(s),
            )
            return

        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            super()._media_status_changed(status)
            if self._transitioning_clip:
                serial = self._transition_serial
                QTimer.singleShot(
                    0,
                    lambda s=serial: self._ensure_transition_playing(s),
                )
            return

        if (
            status == QMediaPlayer.MediaStatus.EndOfMedia
            and self.sequence_playing
        ):
            QTimer.singleShot(0, self._advance_continuous_sequence)
            return

        if (
            status == QMediaPlayer.MediaStatus.InvalidMedia
            and self.sequence_playing
            and self._transitioning_clip
        ):
            self.status.setText('Aguardando o próximo clipe carregar...')
            serial = self._transition_serial
            QTimer.singleShot(
                180,
                lambda s=serial: self._ensure_transition_playing(s),
            )
            return

        super()._media_status_changed(status)

    def _playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState

        if playing and self.sequence_playing and self._transitioning_clip:
            self._complete_transition(self._transition_serial)

        # StoppedState durante setSource é normal e não vira PAUSA.
        if self.sequence_playing:
            self.btn_play.setText('⏸ PAUSAR')
            if not playing and self._transitioning_clip:
                serial = self._transition_serial
                QTimer.singleShot(
                    60,
                    lambda s=serial: self._ensure_transition_playing(s),
                )
            return

        self.btn_play.setText('⏸ PAUSAR' if playing else '▶ PLAY')

    # --------------------------------------------------------------
    # Undo
    # --------------------------------------------------------------

    def _clone_clips(self):
        return deepcopy(self.clips)

    def _snapshot(self):
        return {
            'clips': self._clone_clips(),
            'selected_index': int(self.selected_index),
            'global_playhead_ms': int(self.global_playhead_ms),
        }

    @staticmethod
    def _signature_from_snapshot(snapshot):
        data = []
        for clip in snapshot.get('clips') or []:
            data.append((
                str(clip.get('path') or ''),
                int(clip.get('start_ms') or 0),
                int(clip.get('end_ms') or 0),
                bool(clip.get('cut_before')),
            ))
        return tuple(data), int(snapshot.get('selected_index', -1))

    def _current_signature(self):
        return self._signature_from_snapshot(self._snapshot())

    def _commit_undo_if_changed(self, snapshot, label):
        if self._signature_from_snapshot(snapshot) == self._current_signature():
            return
        self._undo_stack.append((str(label), snapshot))
        if len(self._undo_stack) > self.UNDO_LIMIT:
            self._undo_stack = self._undo_stack[-self.UNDO_LIMIT:]
        self._update_undo_control()

    def _update_undo_control(self):
        if not hasattr(self, 'btn_undo'):
            return
        busy = bool(self.export_worker and self.export_worker.isRunning())
        self.btn_undo.setEnabled(bool(self._undo_stack) and not busy)
        if self._undo_stack:
            self.btn_undo.setText(
                f'↶  VOLTAR / DESFAZER  (Ctrl+Z)  •  {self._undo_stack[-1][0]}'
            )
        else:
            self.btn_undo.setText('↶  VOLTAR / DESFAZER  (Ctrl+Z)')

    def _update_controls(self):
        super()._update_controls()
        self._update_undo_control()

    def _undo_shortcut_activated(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            try:
                focus.undo()
            except Exception:
                pass
            return
        self.undo_last_action()

    def undo_last_action(self):
        if not self._undo_stack:
            self.status.setText('Nada para desfazer na timeline.')
            self._update_undo_control()
            return

        label, snapshot = self._undo_stack.pop()
        self.pause_sequence()
        self.clips = deepcopy(snapshot.get('clips') or [])
        self.selected_index = int(snapshot.get('selected_index', -1))
        self.global_playhead_ms = int(snapshot.get('global_playhead_ms', 0))

        for clip in self.clips:
            try:
                self._queue_thumbnail(clip)
            except Exception:
                pass

        if not self.clips:
            self.selected_index = -1
            self.global_playhead_ms = 0
            self.player.stop()
            self.player.setSource(QUrl())
            self._refresh_timeline(False)
            self.load_selected_clip(False)
        else:
            self.selected_index = max(0, min(self.selected_index, len(self.clips) - 1))
            self.global_playhead_ms = max(
                0,
                min(self.global_playhead_ms, self.total_duration_ms()),
            )
            self._refresh_timeline(True)
            self.load_selected_clip(False)
            self.seek_sequence(self.global_playhead_ms, False)

        self.status.setText(f'Desfeito: {label}.')
        self._update_undo_control()

    def cut_at_playhead(self):
        before = self._snapshot()
        super().cut_at_playhead()
        self._commit_undo_if_changed(before, 'corte')

    def remove_selected(self):
        before = self._snapshot()
        super().remove_selected()
        self._commit_undo_if_changed(before, 'exclusão de trecho')

    def apply_times_from_fields(self, show_message):
        before = self._snapshot()
        result = super().apply_times_from_fields(show_message)
        if result:
            self._commit_undo_if_changed(before, 'ajuste de início/fim')
        return result

    def mark_start_here(self):
        before = self._snapshot()
        super().mark_start_here()
        self._commit_undo_if_changed(before, 'marcação de início')

    def mark_end_here(self):
        before = self._snapshot()
        super().mark_end_here()
        self._commit_undo_if_changed(before, 'marcação de fim')
