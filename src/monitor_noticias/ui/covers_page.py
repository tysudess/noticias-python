from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CoversPage(QWidget):
    """Principais Capas integrado ao mesmo processo PySide6 do Monitor."""

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = Path(app_root)

        self._window = None
        self._content = None
        self._status = None
        self._loaded = False
        self._loading = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel("Carregando Principais Capas...")
        self.loading.setStyleSheet(
            "color:#6079A5;"
            "font-size:14px;"
            "padding:30px;"
        )
        self.root.addWidget(self.loading, 1)

    def refresh(self, _state=None) -> None:
        if self._loaded or self._loading:
            return

        self._loading = True
        QTimer.singleShot(0, self._load_tool)

    def _load_tool(self) -> None:
        try:
            from monitor_noticias.capas_tool.app.ui import (
                MainWindow as CoversWindow,
                STYLE,
            )

            window = CoversWindow()

            content = window.takeCentralWidget()
            if content is None:
                raise RuntimeError(
                    "A interface de Principais Capas não retornou centralWidget."
                )

            content.setParent(self)
            content.setStyleSheet(STYLE)
            content.setMinimumSize(0, 0)

            status = window.statusBar()
            status.setParent(self)
            status.setStyleSheet(STYLE)

            self.root.removeWidget(self.loading)
            self.loading.hide()

            self.root.addWidget(content, 1)
            self.root.addWidget(status, 0)

            self._window = window
            self._content = content
            self._status = status
            self._loaded = True
            self._loading = False

        except Exception as exc:
            self._loading = False
            self._loaded = False
            self.loading.setText(
                "Falha ao carregar Principais Capas:\n"
                f"{exc}"
            )

    def shutdown(self) -> bool:
        try:
            if self._window is not None:
                self._window.close()
        except Exception:
            pass

        return True
