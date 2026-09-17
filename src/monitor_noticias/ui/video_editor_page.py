from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from monitor_noticias.video_editor.window import VideoEditorWindow


class VideoEditorPage(QWidget):
    """Workspace launcher equivalente ao VideoEditorScreen.kt ativo.

    A release original abria um executável PyInstaller separado. No Monitor Python
    o mesmo editor PySide6 é uma janela nativa top-level no mesmo processo; esta é
    a única diferença arquitetural deliberada do Passo 12 e não altera o motor.
    """

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self._opened_once = False
        self._windows: list[VideoEditorWindow] = []
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self); root.setContentsMargins(12, 12, 12, 12); root.setSpacing(10)
        header = QFrame(); hl = QHBoxLayout(header); hl.setContentsMargins(18, 10, 18, 10)
        logo = QLabel("▥"); logo.setStyleSheet("color:#37a6ff;font-size:42px")
        titles = QVBoxLayout(); title = QLabel("VideoMaster PRO"); title.setStyleSheet("font-size:27px;font-weight:700")
        subtitle = QLabel("Editor de Vídeo nativo • PySide6 6.9.1 • QtMultimedia • QMediaPlayer")
        subtitle.setStyleSheet("color:#a8b4c7")
        titles.addWidget(title); titles.addWidget(subtitle); hl.addWidget(logo); hl.addLayout(titles); hl.addStretch(1)
        self.open_button = QPushButton("Abrir Editor"); self.open_button.clicked.connect(self.open_editor); hl.addWidget(self.open_button)
        back = QPushButton("Voltar ao Monitor"); back.clicked.connect(self.back_requested.emit); hl.addWidget(back); root.addWidget(header)

        body = QHBoxLayout(); rail = QFrame(); rail.setFixedWidth(230); rl = QVBoxLayout(rail)
        for text, active in [
            ("✂  Editor de Vídeo", True), ("⇩  Extração", False), ("▤  Compactação", False),
            ("✄  Corte", False), ("▣  Unir Vídeos", False), ("↻  Converter", False),
        ]:
            button = QPushButton(text); button.setMinimumHeight(48)
            if active: button.setStyleSheet("background:#168fff;color:white;font-weight:700")
            else: button.setEnabled(False)
            rl.addWidget(button)
        rl.addStretch(1)
        motor = QLabel("Motor do preview\nPySide6.QtMultimedia.QMediaPlayer\nQVideoWidget para vídeo\nQAudioOutput para áudio")
        motor.setWordWrap(True); motor.setStyleSheet("color:#a8b4c7;padding:10px;border:1px solid #243650")
        rl.addWidget(motor); body.addWidget(rail)

        center = QFrame(); cl = QVBoxLayout(center); cl.addStretch(1)
        name = QLabel("Editor de Vídeo PySide6"); name.setStyleSheet("font-size:32px;font-weight:700"); cl.addWidget(name)
        desc = QLabel("A interface principal do editor abre em uma janela nativa Qt, usando QMediaPlayer + QVideoWidget + QAudioOutput para preview e FFmpeg apenas para exportação.")
        desc.setWordWrap(True); desc.setStyleSheet("color:#a8b4c7;font-size:15px"); cl.addWidget(desc)
        chips = QLabel("Preview real   •   Áudio real   •   Timeline visual   •   Exportação FFmpeg")
        chips.setStyleSheet("color:#4ed69e;padding:12px"); cl.addWidget(chips)
        big = QPushButton("Abrir Editor de Vídeo"); big.setMinimumHeight(56); big.clicked.connect(self.open_editor); cl.addWidget(big)
        self.status = QLabel("Pronto para abrir o Editor de Vídeo PySide6."); self.status.setStyleSheet("color:#a8b4c7"); cl.addWidget(self.status)
        cl.addStretch(1); body.addWidget(center, 1); root.addLayout(body, 1)

    def refresh(self, _state=None) -> None:
        if not self._opened_once:
            self._opened_once = True
            QTimer.singleShot(0, self.open_editor)

    def open_editor(self) -> None:
        try:
            window = VideoEditorWindow(self.app_root)
            # No baseline o editor vivia em processo separado; fechar a janela
            # encerrava esse processo e seus handles. No editor integrado, apagar
            # a top-level window reproduz esse teardown sem trocar o player.
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.destroyed.connect(lambda _=None, w=window: self._discard_window(w))
            self._windows.append(window)
            window.show(); window.raise_(); window.activateWindow()
            self.status.setText("Editor de Vídeo aberto em janela nativa PySide6 com QMediaPlayer, QVideoWidget e QAudioOutput.")
        except Exception as exc:
            self.status.setText(f"Falha ao abrir Editor de Vídeo PySide6: {exc}")

    def _discard_window(self, window: VideoEditorWindow) -> None:
        try: self._windows.remove(window)
        except ValueError: pass

    def shutdown(self) -> bool:
        """Reproduz o teardown do processo separado antes do Monitor sair."""
        for window in list(self._windows):
            try:
                window.player.stop()
                window.player.setSource(QUrl())
                window.close()
            except RuntimeError:
                self._discard_window(window)
        return all(not window.isVisible() for window in list(self._windows))
