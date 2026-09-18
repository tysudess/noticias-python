from copy import deepcopy

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from . import advanced_editor as base


class AdvancedVideoEditorWidget300(base.AdvancedVideoEditorWidget):
    """Editor v3.0 com histórico de desfazer para ações destrutivas da timeline."""

    UNDO_LIMIT = 50

    def __init__(self, videos_dir, ffmpeg_exe, ffprobe_exe, parent=None):
        self._undo_stack = []
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
