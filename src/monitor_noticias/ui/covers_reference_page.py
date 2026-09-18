from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.capas_tool.app.config import bundle_dir
from monitor_noticias.capas_tool.app.ui import MainWindow as CoversEngineWindow


LIGHT_STYLE = """
QMainWindow, QWidget {
    background:#F4F9FF;
    color:#08245F;
    font-family:'Segoe UI';
    font-size:12px;
}

QFrame#header,
QFrame#card {
    background:#FFFFFF;
    border:1px solid #D4E4F5;
    border-radius:12px;
}

QLabel#title {
    font-size:22px;
    font-weight:900;
    color:#08245F;
}

QLabel#sub {
    color:#6079A5;
}

QLabel#green {
    color:#08A66B;
    font-weight:800;
}

QPushButton {
    background:#FFFFFF;
    border:1px solid #C9DDF2;
    border-radius:9px;
    padding:10px 14px;
    color:#0C3974;
    font-weight:800;
    min-height:30px;
}

QPushButton:hover {
    background:#EEF6FF;
    border-color:#9FC6ED;
}

QPushButton#primary {
    background:qlineargradient(
        x1:0,y1:0,x2:1,y2:0,
        stop:0 #0A79F4,
        stop:1 #168DFF
    );
    border:0;
    color:#FFFFFF;
}

QPushButton#greenBtn {
    background:#18A765;
    border:0;
    color:#FFFFFF;
}

QPushButton#danger {
    background:#FFF0F3;
    border:1px solid #FFB4C6;
    color:#D72B52;
}

QCheckBox {
    spacing:8px;
}

QCheckBox::indicator {
    width:18px;
    height:18px;
}

QListWidget {
    background:#FFFFFF;
    border:1px solid #D4E4F5;
    border-radius:10px;
    padding:5px;
    outline:none;
}

QListWidget::item {
    padding:5px;
    border-radius:9px;
    margin:3px 1px;
}

QListWidget::item:selected {
    background:#EAF4FF;
    border:1px solid #8EC5FF;
}

QDateEdit,
QLineEdit {
    background:#FFFFFF;
    border:1px solid #C9DDF2;
    border-radius:8px;
    padding:8px 10px;
    color:#08245F;
}

QProgressBar {
    border:0;
    background:#DDEAF7;
    border-radius:4px;
    height:7px;
}

QProgressBar::chunk {
    background:#087AF7;
    border-radius:4px;
}

QGroupBox {
    background:#FFFFFF;
    border:1px solid #D4E4F5;
    border-radius:10px;
    margin-top:12px;
    padding-top:12px;
    font-weight:800;
    color:#08245F;
}

QGroupBox::title {
    subcontrol-origin:margin;
    left:10px;
    padding:0 6px;
    color:#315A8C;
}
"""


class ReferenceCoversWindow(CoversEngineWindow):
    """Motor original de Capas com composição visual integrada ao Monitor."""

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(LIGHT_STYLE)
        self.resize(1320, 760)
        self.setMinimumSize(980, 620)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(8)

        header = QFrame()
        header.setObjectName("header")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(10)

        icon = QLabel()
        pix = QPixmap(str(bundle_dir() / "assets" / "app_icon.png"))
        icon.setPixmap(
            pix.scaled(
                58,
                58,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        hl.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)

        title = QLabel("PRINCIPAIS CAPAS")
        title.setObjectName("title")

        sub = QLabel(
            "Windows Portable • busca automática • revisão manual • PDF otimizado"
        )
        sub.setObjectName("sub")

        text.addWidget(title)
        text.addWidget(sub)
        hl.addLayout(text, 1)

        date_label = QLabel("Data:")
        date_label.setStyleSheet(
            "font-weight:800;color:#08245F;"
        )
        hl.addWidget(date_label)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMinimumWidth(135)
        hl.addWidget(self.date_edit)

        cfg = QPushButton("⚙  Apps Script")
        cfg.clicked.connect(self.configure_script)
        hl.addWidget(cfg)

        root.addWidget(header)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.refresh_btn = QPushButton("↻  ATUALIZAR CAPAS")
        self.refresh_btn.setObjectName("primary")
        self.refresh_btn.clicked.connect(self.refresh_all)

        self.pdf_btn = QPushButton("▣  GERAR PDF")
        self.pdf_btn.setObjectName("greenBtn")
        self.pdf_btn.clicked.connect(self.generate_pdf)

        self.open_btn = QPushButton("▤  ABRIR PDF GERADO")
        self.open_btn.clicked.connect(self.open_pdf)

        allb = QPushButton("✓  Marcar todas")
        allb.clicked.connect(lambda: self.set_all(True))

        noneb = QPushButton("×  Desmarcar")
        noneb.clicked.connect(lambda: self.set_all(False))

        for button in (
            self.refresh_btn,
            self.pdf_btn,
            self.open_btn,
            allb,
            noneb,
        ):
            actions.addWidget(button, 1)

        root.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        content = QHBoxLayout()
        content.setSpacing(10)
        root.addLayout(content, 1)

        left = QFrame()
        left.setObjectName("card")

        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(7)

        list_title = QLabel("JORNAIS (8)")
        list_title.setStyleSheet(
            "font-size:12px;font-weight:900;color:#08245F;"
        )
        ll.addWidget(list_title)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._select_row)
        ll.addWidget(self.list, 1)

        content.addWidget(left, 34)

        right = QFrame()
        right.setObjectName("card")

        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 10, 12, 10)
        rl.setSpacing(7)

        self.paper_title = QLabel("Selecione um jornal")
        self.paper_title.setObjectName("title")
        rl.addWidget(self.paper_title)

        self.paper_status = QLabel("")
        self.paper_status.setObjectName("green")
        self.paper_status.setWordWrap(True)
        rl.addWidget(self.paper_status)

        self.preview = QLabel("▤\n\nAguardando capa")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(330)
        self.preview.setStyleSheet(
            "background:#FBFDFF;"
            "border:1px solid #C9DDF2;"
            "border-radius:10px;"
            "color:#6E88AE;"
            "font-size:14px;"
        )
        rl.addWidget(self.preview, 1)

        candbox = QGroupBox("Páginas recebidas / candidatas")
        cl = QHBoxLayout(candbox)

        self.prev_btn = QPushButton("◀  Anterior")
        self.prev_btn.clicked.connect(
            lambda: self.move_candidate(-1)
        )

        self.cand_label = QLabel("0 de 0")
        self.cand_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.cand_label.setStyleSheet(
            "font-weight:800;color:#08245F;"
        )

        self.next_btn = QPushButton("Próxima  ▶")
        self.next_btn.clicked.connect(
            lambda: self.move_candidate(1)
        )

        cl.addWidget(self.prev_btn)
        cl.addWidget(self.cand_label, 1)
        cl.addWidget(self.next_btn)

        rl.addWidget(candbox)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.review_btn = QPushButton("USAR ESTA PÁGINA")
        self.review_btn.setObjectName("primary")
        self.review_btn.clicked.connect(
            self.use_current_candidate
        )

        manual = QPushButton("INSERIR CAPA MANUALMENTE")
        manual.clicked.connect(self.manual_cover)

        restore = QPushButton("VOLTAR PARA AUTOMÁTICA")
        restore.clicked.connect(self.restore_auto)

        buttons.addWidget(self.review_btn, 1)
        buttons.addWidget(manual, 1)
        buttons.addWidget(restore, 1)

        rl.addLayout(buttons)
        content.addWidget(right, 66)

        self.statusBar().showMessage("Pronto")

    def _refresh_list(self):
        row = self.list.currentRow()
        self.list.clear()

        for idx, entry in enumerate(self.entries, 1):
            item = QListWidgetItem()
            item.setData(
                Qt.ItemDataRole.UserRole,
                entry.name,
            )
            self.list.addItem(item)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(7, 5, 7, 5)
            layout.setSpacing(9)

            check = QCheckBox()
            check.setChecked(entry.selected)
            check.toggled.connect(
                lambda value, e=entry: self._toggle(
                    e,
                    value,
                )
            )
            layout.addWidget(check)

            number = QLabel(str(idx))
            number.setFixedWidth(28)
            number.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            number.setStyleSheet(
                "font-size:15px;"
                "font-weight:900;"
                "color:#0A5DB7;"
            )
            layout.addWidget(number)

            texts = QVBoxLayout()
            texts.setSpacing(2)

            name = QLabel(entry.name)
            name.setStyleSheet(
                "font-size:13px;"
                "font-weight:900;"
                "color:#08245F;"
            )

            status = QLabel(entry.status)
            status.setWordWrap(True)
            status.setStyleSheet(
                "font-size:10px;"
                "color:#6079A5;"
            )

            texts.addWidget(name)
            texts.addWidget(status)
            layout.addLayout(texts, 1)

            if entry.current_path:
                pm = QPixmap(
                    str(entry.current_path)
                ).scaled(
                    43,
                    62,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                thumb = QLabel()
                thumb.setPixmap(pm)
                layout.addWidget(thumb)

            item.setSizeHint(QSize(300, 72))
            self.list.setItemWidget(
                item,
                widget,
            )

        if self.entries:
            self.list.setCurrentRow(
                max(
                    0,
                    min(
                        row if row >= 0 else 0,
                        len(self.entries) - 1,
                    ),
                )
            )


class ReferenceCoversPage(QWidget):
    """Capas como uma página real do Monitor, sem aparência de janela externa."""

    back_requested = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()

        self.app_root = Path(app_root)
        self._window = None
        self._content = None
        self._loaded = False
        self._loading = False

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.loading = QLabel("Carregando Principais Capas…")
        self.loading.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.loading.setStyleSheet(
            "color:#6079A5;font-size:13px;"
        )
        self.root.addWidget(self.loading, 1)

    def refresh(self, _state=None) -> None:
        if self._loaded or self._loading:
            return

        self._loading = True
        QTimer.singleShot(0, self._load)

    def _load(self) -> None:
        try:
            # Mantém o resolver reforçado do ajuste anterior quando disponível.
            try:
                from monitor_noticias.capas_tool.app import web_resolver
                from monitor_noticias.capas_tool.app import ui as covers_ui
                from monitor_noticias.capas_tool.app.web_resolver_patch import (
                    RobustFrontPageResolver,
                )

                # web_resolver.Resolver é usado por imports novos.
                web_resolver.Resolver = RobustFrontPageResolver

                # ui.py importou "Resolver" por valor na inicialização.
                # Portanto também precisamos substituir o símbolo já importado.
                covers_ui.Resolver = RobustFrontPageResolver

            except Exception:
                pass

            window = ReferenceCoversWindow()
            window.hide()

            content = window.takeCentralWidget()

            if content is None:
                raise RuntimeError(
                    "Principais Capas não retornou uma área de trabalho."
                )

            content.setParent(self)
            content.setMinimumSize(1000, 620)

            scroll = QScrollArea(self)
            scroll.setObjectName("referenceCoversScroll")
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            scroll.setWidget(content)
            scroll.setStyleSheet(
                """
                QScrollArea#referenceCoversScroll {
                    background:#F4F9FF;
                    border:0;
                }
                QScrollBar:vertical {
                    background:#EDF4FC;
                    width:10px;
                    border-radius:5px;
                }
                QScrollBar::handle:vertical {
                    background:#8BB9E8;
                    min-height:55px;
                    border-radius:5px;
                }
                QScrollBar:horizontal {
                    background:#EDF4FC;
                    height:10px;
                    border-radius:5px;
                }
                QScrollBar::handle:horizontal {
                    background:#8BB9E8;
                    min-width:55px;
                    border-radius:5px;
                }
                QScrollBar::add-line,
                QScrollBar::sub-line {
                    width:0;
                    height:0;
                }
                """
            )

            self.root.removeWidget(self.loading)
            self.loading.hide()
            self.root.addWidget(scroll, 1)

            self._window = window
            self._content = content
            self._scroll = scroll
            self._loaded = True
            self._loading = False

        except Exception as exc:
            self._loading = False
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
