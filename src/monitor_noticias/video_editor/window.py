from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .core import (
    Clip,
    SUPPORTED_EXTENSIONS,
    build_export_command,
    clip_at_global,
    export_output_path,
    format_time,
    global_start_for_clip,
    hide_console_kwargs,
    probe_video,
    total_duration,
)
from .timeline import TimelineWidget

BG = "#07111f"
TOP = "#0b1524"
PANEL = "#0d1828"
PANEL_3 = "#18263a"
BORDER = "#243650"
TEXT = "#f1f5ff"
MUTED = "#a8b4c7"
FADED = "#66758d"
BLUE = "#168fff"
BLUE_2 = "#37a6ff"


class VideoEditorWindow(QMainWindow):
    """Janela nativa equivalente a video_editor_pyside/main.py da release V8."""

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self.bin_dir = self.app_root / "bin"
        self.ffmpeg = self.bin_dir / "ffmpeg.exe"
        self.ffprobe = self.bin_dir / "ffprobe.exe"
        self.exports_dir = self.app_root / "VideoEditorExports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("VideoMaster PRO - Editor de Vídeo")
        self.resize(1600, 920)
        self.clips: list[Clip] = []
        self.selected_index = -1
        self.sequence_mode = False
        self.updating_slider = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.85)
        self.player.setAudioOutput(self.audio)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background: black; border: 1px solid #243650; border-radius: 6px;")
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_player_error)

        self.build_ui()
        self.apply_theme()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Pronto. Abra um ou mais vídeos.")

    def apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; color: {TEXT}; }}
            QWidget {{ color: {TEXT}; font-family: Segoe UI, Arial; font-size: 13px; }}
            QPushButton {{ background: {PANEL_3}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 10px 14px; font-weight: 600; }}
            QPushButton:hover {{ background: #1d314d; }}
            QPushButton:disabled {{ color: {FADED}; background: #101a29; }}
            QListWidget {{ background: #0a1320; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px; }}
            QListWidget::item {{ padding: 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {BLUE}; color: white; }}
            QSlider::groove:horizontal {{ height: 10px; background: #33435a; border-radius: 5px; }}
            QSlider::handle:horizontal {{ width: 16px; height: 16px; background: {BLUE_2}; margin: -4px 0; border-radius: 8px; }}
            QSlider::sub-page:horizontal {{ background: {BLUE}; border-radius: 5px; }}
            QStatusBar {{ background: #06101d; color: {MUTED}; border-top: 1px solid {BORDER}; }}
        """)

    def panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setStyleSheet(f"QFrame#panel {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; }}")
        shadow = QGraphicsDropShadowEffect(frame)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        frame.setGraphicsEffect(shadow)
        return frame

    def build_ui(self) -> None:
        root = QWidget(); main = QVBoxLayout(root)
        main.setContentsMargins(8, 8, 8, 8); main.setSpacing(8); self.setCentralWidget(root)

        top = self.panel(); top_l = QHBoxLayout(top); top_l.setContentsMargins(18, 10, 18, 10)
        logo = QLabel("▥"); logo.setStyleSheet(f"color:{BLUE_2}; font-size:42px; font-weight:300;")
        title_box = QVBoxLayout(); title = QLabel("VideoMaster PRO"); title.setStyleSheet("font-size:26px; font-weight:800;")
        subtitle = QLabel("Editor PySide6 • QtMultimedia QMediaPlayer • QVideoWidget • QAudioOutput"); subtitle.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        title_box.addWidget(title); title_box.addWidget(subtitle); top_l.addWidget(logo); top_l.addLayout(title_box); top_l.addStretch(1)
        self.btn_open = QPushButton("▭  Abrir Vídeo"); self.btn_open.clicked.connect(self.open_files); top_l.addWidget(self.btn_open)
        self.btn_save = QPushButton("▣  Salvar Projeto"); self.btn_save.clicked.connect(lambda: self.info_box("Esta função não existe no motor atual: Salvar Projeto.")); top_l.addWidget(self.btn_save)
        self.btn_settings = QPushButton("⚙  Configurações"); self.btn_settings.clicked.connect(lambda: self.info_box("Esta função não existe no motor atual: Configurações.")); top_l.addWidget(self.btn_settings)
        main.addWidget(top, 0)

        center = QHBoxLayout(); center.setSpacing(8); main.addLayout(center, 1)
        rail = self.panel(); rail.setFixedWidth(210); rail_l = QVBoxLayout(rail); rail_l.setContentsMargins(10, 10, 10, 10)
        for label, active in [
            ("✂  Editor de Vídeo", True), ("⇩  Extração", False), ("▤  Compactação", False),
            ("✄  Corte", False), ("▣  Unir Vídeos", False), ("↻  Converter", False),
        ]:
            button = QPushButton(label); button.setMinimumHeight(54)
            if active:
                button.setStyleSheet(f"background:{BLUE}; color:white; border:1px solid {BLUE_2}; border-radius:8px; font-weight:800;")
            else:
                button.clicked.connect(lambda _=False, name=label: self.info_box(f"Esta função não existe no motor atual: {name[3:]} dentro do Editor."))
            rail_l.addWidget(button)
        rail_l.addStretch(1)
        current = QLabel("Funcional agora\n\n• Abrir vários vídeos\n• Preview QMediaPlayer\n• Áudio QAudioOutput\n• Timeline visual\n• Exportar trecho")
        current.setStyleSheet(f"color:{MUTED}; background:#0a1320; border:1px solid {BORDER}; border-radius:8px; padding:12px;")
        rail_l.addWidget(current); center.addWidget(rail)

        media_panel = self.panel(); media_panel.setFixedWidth(405); media_l = QVBoxLayout(media_panel); media_l.setContentsMargins(14, 14, 14, 14)
        header = QHBoxLayout(); h = QLabel("Mídia do Projeto"); h.setStyleSheet("font-size:20px; font-weight:800;")
        self.media_count = QLabel("0 clipes"); self.media_count.setStyleSheet(f"color:{FADED};"); header.addWidget(h); header.addStretch(1); header.addWidget(self.media_count); media_l.addLayout(header)
        media_buttons = QHBoxLayout(); import_btn = QPushButton("⇩  Importar"); import_btn.clicked.connect(self.open_files); add_btn = QPushButton("＋  Adicionar"); add_btn.clicked.connect(self.open_files)
        media_buttons.addWidget(import_btn); media_buttons.addWidget(add_btn); media_l.addLayout(media_buttons)
        tabs = QHBoxLayout()
        for name in ["Todos", "Vídeos", "Imagens", "Áudios"]:
            button = QPushButton(name)
            if name not in ("Todos", "Vídeos"):
                button.setEnabled(False); button.setToolTip("Esta função não existe no motor atual.")
            tabs.addWidget(button)
        media_l.addLayout(tabs)
        self.media_list = QListWidget(); self.media_list.itemSelectionChanged.connect(self.on_media_selection); media_l.addWidget(self.media_list, 1)
        self.info_label = QLabel("Nenhuma mídia importada."); self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(f"color:{MUTED}; background:#0a1320; border:1px solid {BORDER}; border-radius:8px; padding:10px;"); media_l.addWidget(self.info_label)
        center.addWidget(media_panel)

        work = QVBoxLayout(); work.setSpacing(8); center.addLayout(work, 1)
        preview_panel = self.panel(); preview_l = QVBoxLayout(preview_panel); preview_l.setContentsMargins(14, 14, 14, 14)
        prev_header = QHBoxLayout(); prev_title = QLabel("Pré-visualização"); prev_title.setStyleSheet("font-size:22px; font-weight:800;")
        self.preview_meta = QLabel("QtMultimedia"); self.preview_meta.setStyleSheet(f"color:{MUTED};")
        prev_header.addWidget(prev_title); prev_header.addWidget(self.preview_meta); prev_header.addStretch(1)
        self.engine_badge = QLabel("QMediaPlayer"); self.engine_badge.setStyleSheet(f"color:{MUTED}; background:#09121f; border:1px solid {BORDER}; border-radius:6px; padding:7px 12px;")
        prev_header.addWidget(self.engine_badge); preview_l.addLayout(prev_header)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); preview_l.addWidget(self.video_widget, 1)
        seek_row = QHBoxLayout(); self.current_label = QLabel("00:00.000"); self.duration_label = QLabel("00:00.000")
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setRange(0, 1)
        self.slider.sliderPressed.connect(lambda: setattr(self, "updating_slider", True)); self.slider.sliderReleased.connect(self.slider_seek_released)
        seek_row.addWidget(self.current_label); seek_row.addWidget(self.slider, 1); seek_row.addWidget(self.duration_label); preview_l.addLayout(seek_row)
        controls = QHBoxLayout(); controls.addStretch(1)
        back = QPushButton("◀ 5s"); back.clicked.connect(lambda: self.seek_global(self.global_position() - 5000))
        self.play_btn = QPushButton("▶"); self.play_btn.setMinimumWidth(70); self.play_btn.clicked.connect(self.toggle_play)
        forward = QPushButton("5s ▶"); forward.clicked.connect(lambda: self.seek_global(self.global_position() + 5000))
        self.mute_btn = QPushButton("🔊"); self.mute_btn.clicked.connect(self.toggle_mute)
        controls.addWidget(back); controls.addWidget(self.play_btn); controls.addWidget(forward); controls.addWidget(self.mute_btn); controls.addStretch(1)
        preview_l.addLayout(controls); work.addWidget(preview_panel, 1)

        timeline_panel = self.panel(); timeline_l = QVBoxLayout(timeline_panel); timeline_l.setContentsMargins(14, 14, 14, 14)
        tool_row = QHBoxLayout(); tl_title = QLabel("Timeline"); tl_title.setStyleSheet("font-size:20px; font-weight:800;"); tool_row.addWidget(tl_title); tool_row.addStretch(1)
        cut_btn = QPushButton("✂  Exportar trecho"); cut_btn.clicked.connect(self.export_selected); tool_row.addWidget(cut_btn); timeline_l.addLayout(tool_row)
        self.timeline = TimelineWidget(); self.timeline.seekRequested.connect(self.seek_global); self.timeline.clipSelected.connect(self.select_clip); timeline_l.addWidget(self.timeline)
        work.addWidget(timeline_panel, 0)

        quick = QHBoxLayout()
        for label in ["Cortar Vídeo", "Unir Vídeos", "Extrair", "Compactar", "Converter"]:
            button = QPushButton(label)
            if label == "Cortar Vídeo": button.clicked.connect(self.export_selected)
            else: button.clicked.connect(lambda _=False, name=label: self.info_box(f"Esta função não existe no motor atual: {name}."))
            quick.addWidget(button)
        main.addLayout(quick)

    def info_box(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def open_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Abrir vídeos", str(Path.home()), "Vídeos (*.mp4 *.mkv *.webm *.mov *.avi *.m4v)")
        if not files: return
        added = 0; errors: list[str] = []
        for name in files:
            path = Path(name)
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                errors.append(f"Formato não suportado: {path.name}"); continue
            try:
                info = probe_video(path, self.ffprobe)
                if info.duration_ms <= 0: raise RuntimeError("Não foi possível determinar a duração.")
                self.clips.append(Clip(path=path, info=info)); added += 1
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.refresh_media()
        if added and self.selected_index < 0:
            self.select_clip(0); self.seek_global(0)
        self.statusBar().showMessage(f"{added} vídeo(s) adicionado(s)." if added else "Nenhum vídeo adicionado.")
        if errors: QMessageBox.warning(self, "Arquivos não adicionados", "\n".join(errors[:6]))

    def refresh_media(self) -> None:
        self.media_list.clear()
        for index, clip in enumerate(self.clips):
            item = QListWidgetItem(f"{index + 1}. {clip.path.name}\n{clip.info.width}×{clip.info.height} • {format_time(clip.duration_ms)} • {'áudio' if clip.info.has_audio else 'sem áudio'}")
            item.setData(Qt.ItemDataRole.UserRole, index); self.media_list.addItem(item)
        self.media_count.setText(f"{len(self.clips)} clipe(s)"); self.timeline.set_clips(self.clips)
        self.slider.setRange(0, max(1, self.total_duration())); self.duration_label.setText(format_time(self.total_duration()))

    def on_media_selection(self) -> None:
        items = self.media_list.selectedItems()
        if items: self.select_clip(int(items[0].data(Qt.ItemDataRole.UserRole)))

    def select_clip(self, index: int) -> None:
        if not (0 <= index < len(self.clips)): return
        self.selected_index = index; self.timeline.set_selected(index)
        if self.media_list.currentRow() != index: self.media_list.setCurrentRow(index)
        clip = self.clips[index]
        self.preview_meta.setText(f"{clip.info.width}×{clip.info.height} • {clip.info.fps:.2f} fps")
        self.info_label.setText(
            f"Arquivo: {clip.path.name}\nDuração: {format_time(clip.duration_ms)}\nResolução: {clip.info.width}×{clip.info.height}\n"
            f"FPS: {clip.info.fps:.2f}\nCodec: {clip.info.video_codec.upper()}\nÁudio: {'Sim - ' + clip.info.audio_codec.upper() if clip.info.audio_codec else 'Não'}"
        )
        self.load_clip(index, autoplay=False)

    def total_duration(self) -> int:
        return total_duration(self.clips)

    def clip_at_global(self, global_ms: int) -> tuple[int, int]:
        return clip_at_global(self.clips, global_ms)

    def global_start_for_clip(self, index: int) -> int:
        return global_start_for_clip(self.clips, index)

    def global_position(self) -> int:
        if self.selected_index < 0: return 0
        clip = self.clips[self.selected_index]
        return self.global_start_for_clip(self.selected_index) + max(0, self.player.position() - clip.start_ms)

    def load_clip(self, index: int, autoplay: bool) -> None:
        if not (0 <= index < len(self.clips)): return
        self.selected_index = index; clip = self.clips[index]; self.timeline.set_selected(index)
        self.player.setSource(QUrl.fromLocalFile(str(clip.path))); self.player.setPosition(clip.start_ms)
        if autoplay:
            self.player.play(); self.play_btn.setText("Ⅱ")
        else:
            self.play_btn.setText("▶")

    def seek_global(self, global_ms: int) -> None:
        if not self.clips: return
        global_ms = max(0, min(int(global_ms), self.total_duration())); index, local = self.clip_at_global(global_ms)
        if index != self.selected_index:
            self.load_clip(index, autoplay=self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        self.player.setPosition(local); self.timeline.set_playhead(global_ms); self.current_label.setText(format_time(global_ms))
        if not self.updating_slider: self.slider.setValue(global_ms)

    def slider_seek_released(self) -> None:
        value = self.slider.value(); self.updating_slider = False; self.seek_global(value)

    def toggle_play(self) -> None:
        if not self.clips:
            self.statusBar().showMessage("Abra um vídeo antes de reproduzir."); return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause(); self.play_btn.setText("▶"); return
        index, local = self.clip_at_global(self.global_position())
        if index < 0: index = 0; local = self.clips[0].start_ms
        if index != self.selected_index: self.load_clip(index, autoplay=False)
        self.player.setPosition(local); self.player.play(); self.play_btn.setText("Ⅱ")
        self.statusBar().showMessage("Reproduzindo com PySide6 QtMultimedia QMediaPlayer.")

    def on_position_changed(self, local_ms: int) -> None:
        if self.selected_index < 0 or self.updating_slider: return
        clip = self.clips[self.selected_index]
        if local_ms >= clip.end_ms:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.play_next_clip()
            return
        global_ms = self.global_start_for_clip(self.selected_index) + max(0, local_ms - clip.start_ms)
        self.timeline.set_playhead(global_ms); self.current_label.setText(format_time(global_ms)); self.slider.setValue(global_ms)

    def on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.play_next_clip()

    def play_next_clip(self) -> None:
        next_index = self.selected_index + 1
        if next_index >= len(self.clips):
            self.player.pause(); self.play_btn.setText("▶"); self.seek_global(self.total_duration()); return
        self.load_clip(next_index, autoplay=True); self.media_list.setCurrentRow(next_index)

    def on_player_error(self, error, error_string: str) -> None:
        if error_string: self.statusBar().showMessage(f"Erro do player QtMultimedia: {error_string}")

    def toggle_mute(self) -> None:
        muted = self.audio.isMuted(); self.audio.setMuted(not muted); self.mute_btn.setText("🔇" if not muted else "🔊")

    def export_selected(self) -> None:
        if self.selected_index < 0 or not self.clips:
            self.statusBar().showMessage("Selecione um clipe antes de exportar."); return
        if not self.ffmpeg.exists():
            QMessageBox.warning(self, "FFmpeg ausente", f"ffmpeg.exe não encontrado em {self.bin_dir}"); return
        clip = self.clips[self.selected_index]; out = export_output_path(self.exports_dir, clip)
        command = build_export_command(self.ffmpeg, clip, out)
        self.statusBar().showMessage("Exportando trecho selecionado...")
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3600, **hide_console_kwargs())
            if result.returncode != 0: raise RuntimeError((result.stderr or result.stdout).strip()[-900:])
            self.statusBar().showMessage(f"Exportado: {out}"); QMessageBox.information(self, "Exportação concluída", f"Arquivo exportado:\n{out}")
        except Exception as exc:
            QMessageBox.critical(self, "Falha na exportação", str(exc)); self.statusBar().showMessage("Falha na exportação.")
