from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class CoversPage(QWidget):
    """Principais Capas incorporado ao Monitor com viewport rolável."""

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()

        self.app_root = Path(app_root)

        self._window = None
        self._content = None
        self._status = None
        self._scroll = None
        self._loaded = False
        self._loading = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel(
            "Carregando Principais Capas..."
        )
        self.loading.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
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
            # Instala o resolver reforçado ANTES de ui.py importar Resolver.
            from monitor_noticias.capas_tool.app import web_resolver
            from monitor_noticias.capas_tool.app.web_resolver_patch import (
                RobustFrontPageResolver,
            )

            web_resolver.Resolver = RobustFrontPageResolver

            from monitor_noticias.capas_tool.app.ui import (
                MainWindow as CoversWindow,
                STYLE,
            )

            window = CoversWindow()
            window.hide()

            content = window.takeCentralWidget()

            if content is None:
                raise RuntimeError(
                    "A interface de Principais Capas não retornou centralWidget."
                )

            content.setParent(self)
            content.setStyleSheet(STYLE)

            # Tamanho de projeto preservado. O scroll assume em telas menores.
            content.setMinimumSize(1480, 900)

            scroll = QScrollArea(self)
            scroll.setObjectName("coversOuterScroll")
            scroll.setFrameShape(
                QScrollArea.Shape.NoFrame
            )
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setWidget(content)

            status = window.statusBar()
            status.setParent(self)
            status.setStyleSheet(STYLE)

            self.root.removeWidget(self.loading)
            self.loading.hide()

            self.root.addWidget(scroll, 1)
            self.root.addWidget(status, 0)

            self._window = window
            self._content = content
            self._status = status
            self._scroll = scroll

            self.setStyleSheet(
                """
                QScrollArea#coversOuterScroll {
                    background:#071625;
                    border:0;
                }

                QScrollBar:vertical {
                    background:#0B1F33;
                    width:12px;
                    border-radius:6px;
                }

                QScrollBar::handle:vertical {
                    background:#315675;
                    min-height:52px;
                    border-radius:6px;
                }

                QScrollBar::handle:vertical:hover {
                    background:#4380B0;
                }

                QScrollBar:horizontal {
                    background:#0B1F33;
                    height:12px;
                    border-radius:6px;
                }

                QScrollBar::handle:horizontal {
                    background:#315675;
                    min-width:52px;
                    border-radius:6px;
                }

                QScrollBar::handle:horizontal:hover {
                    background:#4380B0;
                }

                QScrollBar::add-line,
                QScrollBar::sub-line {
                    width:0;
                    height:0;
                }
                """
            )

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
