from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CoversPage(QWidget):
    """Integra o programa Principais Capas dentro do Monitor."""

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)
        self._window = None
        self._content = None
        self._loaded = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel("Carregando Principais Capas...")
        self.loading.setStyleSheet(
            "color:#6079A5;font-size:14px;padding:30px;"
        )
        self.root.addWidget(self.loading)

    def refresh(self, _state=None) -> None:
        if self._loaded:
            return

        self._loaded = True
        QTimer.singleShot(0, self._load_tool)

    def _load_tool(self) -> None:
        try:
            from monitor_noticias.capas_tool.app.ui import (
                MainWindow as CoversWindow,
                STYLE,
            )

            self._window = CoversWindow()

            content = self._window.takeCentralWidget()
            content.setStyleSheet(STYLE)

            self.root.removeWidget(self.loading)
            self.loading.hide()
            self.root.addWidget(content, 1)

            # Mantém a barra de status da ferramenta visível dentro da aba.
            status = self._window.statusBar()
            status.setParent(self)
            status.setStyleSheet(STYLE)
            self.root.addWidget(status, 0)

            self._content = content

        except Exception as exc:
            self.loading.setText(
                f"Falha ao carregar Principais Capas: {exc}"
            )

    def shutdown(self) -> bool:
        try:
            if self._window is not None:
                self._window.close()
        except Exception:
            pass
        return True
