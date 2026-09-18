from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from monitor_noticias.video_editor.window import VideoEditorWindow


class VideoEditorPage(QWidget):
    """Editor de vídeo incorporado na aba, sem abrir janela externa."""

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self.editor: VideoEditorWindow | None = None
        self.workspace = None
        self._loaded = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel("Carregando Editor de Vídeo...")
        self.loading.setStyleSheet(
            "color:#6079A5;font-size:14px;padding:30px;"
        )
        self.root.addWidget(self.loading)

    def refresh(self, _state=None) -> None:
        if self._loaded:
            return

        self._loaded = True
        QTimer.singleShot(0, self._load_editor)

    def _load_editor(self) -> None:
        try:
            # Mantemos o QMainWindow como controlador do player, mas retiramos
            # o centralWidget e o statusBar para exibi-los dentro desta aba.
            self.editor = VideoEditorWindow(self.app_root)

            workspace = self.editor.takeCentralWidget()
            workspace.setStyleSheet(self.editor.styleSheet())

            self.root.removeWidget(self.loading)
            self.loading.hide()
            self.root.addWidget(workspace, 1)

            status = self.editor.statusBar()
            status.setParent(self)
            status.setStyleSheet(self.editor.styleSheet())
            self.root.addWidget(status, 0)

            self.workspace = workspace

        except Exception as exc:
            self.loading.setText(
                f"Falha ao carregar Editor de Vídeo: {exc}"
            )

    def shutdown(self) -> bool:
        if self.editor is None:
            return True

        try:
            self.editor.player.stop()
            self.editor.player.setSource(QUrl())
        except Exception:
            pass

        try:
            self.editor.close()
        except Exception:
            pass

        return True
