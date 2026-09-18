from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from monitor_noticias.video_editor.integrated_editor import (
    AdvancedVideoEditorWidget300,
)


class VideoEditorPage(QWidget):
    """Editor de Vídeo integrado diretamente na aba do Monitor.

    Usa somente o editor avançado do projeto fornecido pelo usuário:
    AdvancedVideoEditorWidget300 -> AdvancedVideoEditorWidget.

    Não usa a janela principal do Extrator de Vídeos, não usa o downloader
    e não cria QMainWindow separada.
    """

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()

        self.app_root = Path(app_root)
        self.videos_dir = self.app_root / "Videos"
        self.bin_dir = self.app_root / "bin"

        self.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ffmpeg = self.bin_dir / "ffmpeg.exe"
        self.ffprobe = self.bin_dir / "ffprobe.exe"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.editor = AdvancedVideoEditorWidget300(
            self.videos_dir,
            self.ffmpeg,
            self.ffprobe,
            self,
        )

        root.addWidget(self.editor, 1)

    def refresh(self, _state=None) -> None:
        # O editor é persistente. O refresh de 500 ms do Monitor não deve
        # reconstruir timeline, preview ou controles.
        pass

    def shutdown(self) -> bool:
        try:
            if hasattr(self.editor, "pause_sequence"):
                self.editor.pause_sequence()
        except Exception:
            pass

        try:
            player = getattr(self.editor, "player", None)
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
                    # Não fecha o Monitor no meio de uma exportação.
                    status = getattr(
                        self.editor,
                        "status",
                        None,
                    )
                    if status is not None:
                        status.setText(
                            "Aguarde a exportação do vídeo terminar antes de sair."
                        )
                    return False
            except Exception:
                pass

        return True
