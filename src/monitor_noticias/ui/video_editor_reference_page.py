from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.video_editor.integrated_editor import (
    AdvancedVideoEditorWidget300,
)


class ReferenceAdvancedVideoEditorWidget(
    AdvancedVideoEditorWidget300
):
    """Mesmo motor do editor v3.0, com a interface clara da referência."""

    def __init__(
        self,
        videos_dir,
        ffmpeg_exe,
        ffprobe_exe,
        parent=None,
    ):
        super().__init__(
            videos_dir,
            ffmpeg_exe,
            ffprobe_exe,
            parent,
        )

        # A função Ctrl+Z continua existindo; apenas o botão adicional é ocultado
        # para manter fidelidade com o layout aprovado.
        try:
            self.btn_undo.hide()
        except Exception:
            pass

        self._apply_reference_style()

    def _apply_reference_style(self) -> None:
        card_css = (
            "background:#FFFFFF;"
            "border:1px solid #D4E4F5;"
            "border-radius:12px;"
        )

        ghost_css = (
            "QPushButton{"
            "background:#FFFFFF;"
            "border:1px solid #C9DDF2;"
            "color:#0C3974;"
            "border-radius:8px;"
            "padding:8px 13px;"
            "font-weight:750;"
            "}"
            "QPushButton:hover{background:#EEF6FF;}"
        )

        primary_css = (
            "QPushButton{"
            "background:qlineargradient("
            "x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #7737F6,"
            "stop:1 #087AF7"
            ");"
            "border:0;"
            "color:#FFFFFF;"
            "border-radius:9px;"
            "padding:9px 15px;"
            "font-weight:850;"
            "}"
        )

        blue_css = (
            "QPushButton{"
            "background:#087AF7;"
            "border:0;"
            "color:#FFFFFF;"
            "border-radius:9px;"
            "padding:9px 15px;"
            "font-weight:850;"
            "}"
        )

        danger_css = (
            "QPushButton{"
            "background:#FFF1F4;"
            "border:1px solid #FFB3C5;"
            "color:#D62852;"
            "border-radius:9px;"
            "padding:9px 14px;"
            "font-weight:800;"
            "}"
        )

        field_css = (
            "QLineEdit{"
            "background:#FFFFFF;"
            "border:1px solid #C9DDF2;"
            "border-radius:8px;"
            "padding:8px 10px;"
            "color:#08245F;"
            "font-family:Consolas;"
            "font-size:10pt;"
            "}"
            "QLineEdit:focus{border:1px solid #087AF7;}"
        )

        # Cards principais (os widgets existem, só recebem o tema final).
        cards = set()

        for child in (
            self.btn_add,
            self.video,
            self.start_edit,
            self.timeline_scroll,
            self.output_name,
        ):
            try:
                parent = child.parentWidget()
                if parent is not None:
                    cards.add(parent)
            except Exception:
                pass

        for card in cards:
            card.setStyleSheet(card_css)

        for button in (
            self.btn_add,
            self.btn_reset_visual,
            self.btn_back5,
            self.btn_forward5,
            self.btn_mark_start,
            self.btn_mark_end,
            self.btn_zoom_out,
            self.btn_zoom_in,
            *self.nudge_buttons,
            self.btn_duplicate,
            self.btn_up,
            self.btn_down,
            self.btn_folder,
        ):
            button.setStyleSheet(ghost_css)

        self.btn_play.setStyleSheet(blue_css)
        self.btn_apply.setStyleSheet(primary_css)
        self.btn_cut.setStyleSheet(primary_css)
        self.btn_export.setStyleSheet(primary_css)
        self.btn_remove.setStyleSheet(danger_css)

        for field in (
            self.start_edit,
            self.end_edit,
            self.output_name,
        ):
            field.setStyleSheet(field_css)

        self.duration_value.setStyleSheet(
            "background:#FFFFFF;"
            "border:1px solid #C9DDF2;"
            "border-radius:8px;"
            "padding:8px 10px;"
            "color:#08245F;"
            "font-family:Consolas;"
        )

        self.selected_label.setStyleSheet(
            "color:#6079A5;"
            "font-size:10pt;"
            "background:transparent;"
            "border:none;"
        )

        self.seq_current.setStyleSheet(
            "color:#315A8C;"
            "font-family:Consolas;"
            "background:transparent;"
            "border:none;"
            "padding-left:8px;"
        )

        self.info_label.setStyleSheet(
            "color:#6079A5;"
            "background:transparent;"
            "border:none;"
            "font-size:9.5pt;"
        )

        self.clip_count.setStyleSheet(
            "color:#6079A5;"
            "background:transparent;"
            "border:none;"
        )

        self.local_position.setStyleSheet(
            "color:#057C9B;"
            "background:#EFFBFF;"
            "border:1px solid #AFE3EE;"
            "border-radius:8px;"
            "padding:4px 8px;"
            "font-family:Consolas;"
            "font-weight:800;"
        )

        self.zoom_label.setStyleSheet(
            "color:#08245F;"
            "background:transparent;"
            "border:none;"
            "font-weight:800;"
        )

        self.estimate_label.setStyleSheet(
            "color:#6079A5;"
            "background:transparent;"
            "border:none;"
        )

        self.status.setStyleSheet(
            "color:#6079A5;"
            "background:transparent;"
            "border:none;"
        )

        self.video.setStyleSheet(
            "background:#000000;border:0;"
        )

        self.video.setMinimumHeight(260)
        self.video.setMaximumHeight(340)

        self.timeline_scroll.setMinimumHeight(128)
        self.timeline_scroll.setMaximumHeight(155)

        palette = QPalette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor("#FFFFFF"),
        )
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor("#FBFDFF"),
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor("#EAF4FF"),
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor("#08245F"),
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor("#08245F"),
        )
        palette.setColor(
            QPalette.ColorRole.Mid,
            QColor("#B9CEE6"),
        )
        palette.setColor(
            QPalette.ColorRole.Midlight,
            QColor("#7FA5CE"),
        )
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor("#087AF7"),
        )

        self.timeline.setPalette(palette)
        self.timeline.setAutoFillBackground(True)
        self.range.setPalette(palette)

        self.timeline_scroll.setStyleSheet(
            """
            QScrollArea {
                background:#FBFDFF;
                border:1px solid #D4E4F5;
                border-radius:8px;
            }
            QScrollBar:horizontal {
                background:#EDF4FC;
                height:9px;
            }
            QScrollBar::handle:horizontal {
                background:#8BB9E8;
                min-width:45px;
                border-radius:4px;
            }
            """
        )

        self.resolution.setStyleSheet(
            "background:#FFFFFF;"
            "color:#08245F;"
            "border:1px solid #C9DDF2;"
            "border-radius:8px;"
            "padding:6px 9px;"
        )
        self.codec.setStyleSheet(
            self.resolution.styleSheet()
        )

        self.progress.setStyleSheet(
            """
            QProgressBar {
                border:1px solid #D4E4F5;
                border-radius:5px;
                background:#EEF4FB;
                text-align:center;
                color:#6079A5;
                min-height:9px;
            }
            QProgressBar::chunk {
                background:#087AF7;
                border-radius:4px;
            }
            """
        )

        self.setStyleSheet(
            """
            ReferenceAdvancedVideoEditorWidget,
            QWidget {
                color:#08245F;
            }

            QLabel {
                color:#08245F;
            }

            QCheckBox {
                color:#244B7B;
            }

            QComboBox {
                background:#FFFFFF;
                color:#08245F;
            }
            """
        )


class ReferenceVideoEditorPage(QWidget):
    back_requested = Signal()

    def __init__(
        self,
        app_root: Path,
    ) -> None:
        super().__init__()

        self.app_root = Path(app_root)
        self.videos_dir = (
            self.app_root / "Videos"
        )
        self.bin_dir = (
            self.app_root / "bin"
        )

        self.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ffmpeg = (
            self.bin_dir / "ffmpeg.exe"
        )
        self.ffprobe = (
            self.bin_dir / "ffprobe.exe"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName(
            "referenceVideoEditorScroll"
        )
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.editor = ReferenceAdvancedVideoEditorWidget(
            self.videos_dir,
            self.ffmpeg,
            self.ffprobe,
            self.scroll,
        )

        self.editor.setMinimumWidth(1000)
        self.editor.setMinimumHeight(700)

        self.scroll.setWidget(self.editor)
        root.addWidget(self.scroll, 1)

        self.setStyleSheet(
            """
            QScrollArea#referenceVideoEditorScroll {
                background:#F4F9FF;
                border:0;
            }

            QScrollArea#referenceVideoEditorScroll
            > QWidget > QWidget {
                background:#F4F9FF;
            }

            QScrollBar:vertical {
                background:#EDF4FC;
                width:10px;
                border-radius:5px;
            }

            QScrollBar::handle:vertical {
                background:#8BB9E8;
                min-height:50px;
                border-radius:5px;
            }

            QScrollBar:horizontal {
                background:#EDF4FC;
                height:10px;
                border-radius:5px;
            }

            QScrollBar::handle:horizontal {
                background:#8BB9E8;
                min-width:50px;
                border-radius:5px;
            }

            QScrollBar::add-line,
            QScrollBar::sub-line {
                width:0;
                height:0;
            }
            """
        )

    def refresh(self, _state=None) -> None:
        pass

    def shutdown(self) -> bool:
        try:
            if hasattr(
                self.editor,
                "pause_sequence",
            ):
                self.editor.pause_sequence()
        except Exception:
            pass

        try:
            player = getattr(
                self.editor,
                "player",
                None,
            )

            if player is not None:
                player.stop()
                player.setSource(QUrl())
        except Exception:
            pass

        worker = getattr(
            self.editor,
            "export_worker",
            None,
        )

        if worker is not None:
            try:
                if worker.isRunning():
                    status = getattr(
                        self.editor,
                        "status",
                        None,
                    )

                    if status is not None:
                        status.setText(
                            "Aguarde a exportação do vídeo "
                            "terminar antes de sair."
                        )
                    return False
            except Exception:
                pass

        return True
