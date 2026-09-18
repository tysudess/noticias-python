from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Signal, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from monitor_noticias.video_editor.window import VideoEditorWindow


class VideoEditorPage(QWidget):
    """Usa o MESMO editor de vídeo que antes abria em janela separada,
    mas incorpora sua interface dentro da aba do Monitor.
    """

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)

        self.editor: VideoEditorWindow | None = None
        self.workspace: QWidget | None = None
        self.status = None
        self._loaded = False
        self._loading = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel("Carregando Editor de Vídeo...")
        self.loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading.setStyleSheet(
            "color:#6079A5;"
            "font-size:14px;"
            "padding:30px;"
        )
        self.root.addWidget(self.loading, 1)

    def refresh(self, _state=None) -> None:
        # O MainWindow atualiza páginas periodicamente.
        # O editor só deve ser criado UMA vez.
        if self._loaded or self._loading:
            return

        self._loading = True
        QTimer.singleShot(0, self._load_editor)

    def _load_editor(self) -> None:
        try:
            # Esta é exatamente a mesma classe que antes era aberta
            # como janela independente:
            #
            #   VideoMaster PRO - Editor de Vídeo
            #
            # Não criamos outro editor e não iniciamos outro executável.
            editor = VideoEditorWindow(self.app_root)

            # Garante que a QMainWindow controladora nunca apareça como
            # uma janela separada.
            editor.hide()
            editor.setWindowFlag(
                Qt.WindowType.Window,
                False,
            )

            workspace = editor.takeCentralWidget()

            if workspace is None:
                raise RuntimeError(
                    "O Editor de Vídeo não retornou a interface principal."
                )

            # Reparenta o conteúdo original para dentro da aba.
            workspace.setParent(self)
            workspace.setMinimumSize(0, 0)
            workspace.setMaximumSize(16777215, 16777215)
            workspace.setStyleSheet(editor.styleSheet())

            # Mantém a barra de status original do editor, também incorporada.
            status = editor.statusBar()
            status.setParent(self)
            status.setStyleSheet(editor.styleSheet())

            self.root.removeWidget(self.loading)
            self.loading.hide()

            self.root.addWidget(workspace, 1)
            self.root.addWidget(status, 0)

            self.editor = editor
            self.workspace = workspace
            self.status = status

            self._loaded = True
            self._loading = False

        except Exception as exc:
            self._loading = False
            self._loaded = False

            self.loading.setText(
                "Falha ao carregar o Editor de Vídeo:\n"
                f"{exc}"
            )

    def showEvent(self, event) -> None:
        super().showEvent(event)

        if not self._loaded and not self._loading:
            self.refresh()

    def shutdown(self) -> bool:
        if self.editor is None:
            return True

        try:
            self.editor.player.stop()
            self.editor.player.setSource(QUrl())
        except Exception:
            pass

        try:
            self.editor.hide()
            self.editor.deleteLater()
        except Exception:
            pass

        self.editor = None
        return True
