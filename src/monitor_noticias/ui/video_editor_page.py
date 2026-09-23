from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal, Qt
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.video_editor.integrated_editor import (
    AdvancedVideoEditorWidget300,
)


class VideoEditorPage(QWidget):
    back_requested = Signal()

    def __init__(
        self,
        app_root: Path,
    ) -> None:
        super().__init__()

        self.paths = AppPaths.for_app_root(
            Path(app_root)
        )
        self.app_root = self.paths.root
        self.videos_dir = self.paths.videos
        self.bin_dir = self.paths.bin

        self.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ffmpeg = (
            self.paths.runtime_binary(
                "ffmpeg"
            )
        )
        self.ffprobe = (
            self.paths.runtime_binary(
                "ffprobe"
            )
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setObjectName(
            "videoEditorOuterScroll"
        )
        self.scroll.setWidgetResizable(
            True
        )
        self.scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.editor = (
            AdvancedVideoEditorWidget300(
                self.videos_dir,
                self.ffmpeg,
                self.ffprobe,
                self.scroll,
            )
        )

        self.editor.setMinimumWidth(
            1180
        )
        self.editor.setMinimumHeight(
            900
        )

        self.scroll.setWidget(
            self.editor
        )
        root.addWidget(
            self.scroll,
            1,
        )

        self.setStyleSheet(
            """
        QScrollArea#videoEditorOuterScroll {
            background:#07111f;
            border:0;
        }
        QScrollArea#videoEditorOuterScroll > QWidget > QWidget {
            background:#07111f;
        }
        QScrollBar:vertical {
            background:#0B1524;
            width:12px;
            border-radius:6px;
        }
        QScrollBar::handle:vertical {
            background:#31527D;
            min-height:54px;
            border-radius:6px;
        }
        QScrollBar::handle:vertical:hover {
            background:#4675AE;
        }
        QScrollBar:horizontal {
            background:#0B1524;
            height:12px;
            border-radius:6px;
        }
        QScrollBar::handle:horizontal {
            background:#31527D;
            min-width:54px;
            border-radius:6px;
        }
        QScrollBar::handle:horizontal:hover {
            background:#4675AE;
        }
        QScrollBar::add-line,
        QScrollBar::sub-line {
            width:0;
            height:0;
        }
        """
        )

    def refresh(
        self,
        _state=None,
    ) -> None:
        pass

    def shutdown(
        self,
    ) -> bool:
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
                player.setSource(
                    QUrl()
                )
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
