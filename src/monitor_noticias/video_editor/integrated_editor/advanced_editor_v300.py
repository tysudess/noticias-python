from copy import deepcopy

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from PySide6.QtMultimedia import QMediaPlayer

from . import advanced_editor as base


class AdvancedVideoEditorWidget300(base.AdvancedVideoEditorWidget):
    """Editor v3.0 com histórico de desfazer para ações destrutivas da timeline."""

    UNDO_LIMIT = 50

    def __init__(self, videos_dir, ffmpeg_exe, ffprobe_exe, parent=None):
        self._undo_stack = []
        # Estado criado antes do super porque a classe-base conecta os sinais
        # do QMediaPlayer durante a própria inicialização.
        self._transitioning_clip = False
        super().__init__(videos_dir, ffmpeg_exe, ffprobe_exe, parent)

        # Botão visível que executa exatamente a mesma ação do Ctrl+Z.
        self.btn_undo = QPushButton('↶  VOLTAR / DESFAZER  (Ctrl+Z)')
        self.btn_undo.setToolTip('Desfazer a última exclusão, corte ou ajuste de trecho da timeline (Ctrl+Z).')
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

    def _finish_continuous_sequence(self):
        self._transitioning_clip = False
        self.sequence_playing = False
        self.player.pause()
        self.global_playhead_ms = self.total_duration_ms()
        self._update_global_ui(auto_scroll=True)
        self.btn_play.setText('▶ PLAY')

    def _release_transition_guard(self):
        # Fallback para mídia que não emite LoadedMedia/BufferedMedia.
        self._transitioning_clip = False

    def _advance_continuous_sequence(self):
        """Avança para o próximo clipe sem transformar a troca em PAUSA."""

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

        self._transitioning_clip = True

        # Mantém a sequência logicamente em reprodução enquanto o backend Qt
        # troca o arquivo. Assim um StoppedState/EndOfMedia intermediário não
        # derruba a timeline.
        self.sequence_playing = True
        self.selected_index = next_index
        self.timeline.set_selected_index(next_index)

        self.global_playhead_ms = self.clip_global_start(next_index)

        self.load_selected_clip(False)
        self.seek_sequence(
            self.global_playhead_ms,
            True,
        )

        self.btn_play.setText('⏸ PAUSAR')
        self.status.setText(
            f'Reprodução contínua • clipe {next_index + 1}/{len(self.clips)}'
        )

        # Caso algum codec/backend não envie LoadedMedia, não deixamos o
        # bloqueio de transição preso indefinidamente.
        QTimer.singleShot(
            3000,
            self._release_transition_guard,
        )

    def _monitor_playback(self):
        if (
            not self.sequence_playing
            or not (
                0 <= self.preview_clip_index
                < len(self.clips)
            )
        ):
            return

        clip = self.clips[
            self.preview_clip_index
        ]

        # Antecipação pequena evita cair primeiro em EndOfMedia, principalmente
        # em arquivos MP4/H.264 que arredondam a última posição do player.
        if (
            self.player.position()
            >= int(clip['end_ms']) - 90
        ):
            self._advance_continuous_sequence()

    def _media_status_changed(self, status):
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            # A classe-base aplica seek pendente e autoplay.
            super()._media_status_changed(status)
            self._transitioning_clip = False
            return

        if (
            status == QMediaPlayer.MediaStatus.EndOfMedia
            and self.sequence_playing
        ):
            # Se o monitor de 55 ms não pegou o limite antes, EndOfMedia é a
            # segunda garantia de que a sequência vai continuar.
            QTimer.singleShot(
                0,
                self._advance_continuous_sequence,
            )
            return

        super()._media_status_changed(status)

    def _playback_state_changed(self, state):
        playing = (
            state
            == QMediaPlayer.PlaybackState.PlayingState
        )

        # Durante a troca de arquivos, o QMediaPlayer passa brevemente por
        # StoppedState. Isso NÃO significa que a sequência foi pausada.
        if self.sequence_playing:
            self.btn_play.setText('⏸ PAUSAR')
        else:
            self.btn_play.setText(
                '⏸ PAUSAR'
                if playing
                else '▶ PLAY'
            )

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
            self.btn_undo.setText(f'↶  VOLTAR / DESFAZER  (Ctrl+Z)  •  {self._undo_stack[-1][0]}')
        else:
            self.btn_undo.setText('↶  VOLTAR / DESFAZER  (Ctrl+Z)')

    def _update_controls(self):
        super()._update_controls()
        self._update_undo_control()

    def _undo_shortcut_activated(self):
        # Em campos de texto, Ctrl+Z continua desfazendo a digitação do próprio campo.
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
            self.global_playhead_ms = max(0, min(self.global_playhead_ms, self.total_duration_ms()))
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
