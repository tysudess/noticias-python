from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.ui.pdf_editor_page import (
    PdfEditorPage,
    PdfPreview,
    ReorderList,
    _pil_to_qimage,
)


class ReferencePdfPreview(PdfPreview):
    """Prévia clara, fiel ao editor de referência."""

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor("#FBFDFF"),
        )
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        if self._image is None or self._image.isNull():
            self._image_rect = QRect()
            cx = self.width() // 2
            cy = self.height() // 2 - 15

            painter.setPen(QColor("#BDD1EC"))
            painter.setFont(
                QFont(
                    "Segoe UI",
                    36,
                    QFont.Weight.Bold,
                )
            )
            painter.drawText(
                QRect(
                    cx - 80,
                    cy - 90,
                    160,
                    80,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "▰",
            )

            painter.setPen(QColor("#087AF7"))
            painter.setFont(
                QFont(
                    "Segoe UI",
                    20,
                    QFont.Weight.Bold,
                )
            )
            painter.drawText(
                QRect(
                    cx - 330,
                    cy - 5,
                    660,
                    44,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "Arraste e solte seus arquivos aqui",
            )

            painter.setPen(QColor("#6C83AA"))
            painter.setFont(
                QFont(
                    "Segoe UI",
                    12,
                )
            )
            painter.drawText(
                QRect(
                    cx - 330,
                    cy + 42,
                    660,
                    32,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "Suporte a PDFs e imagens (JPG, PNG, etc.)",
            )
            return

        fit = min(
            max(1, self.width() - 34)
            / self._image.width(),
            max(1, self.height() - 34)
            / self._image.height(),
        )

        scale = max(.03, fit) * self._zoom

        width = max(
            1,
            round(self._image.width() * scale),
        )
        height = max(
            1,
            round(self._image.height() * scale),
        )

        x = (self.width() - width) // 2
        y = (self.height() - height) // 2

        self._image_rect = QRect(
            x,
            y,
            width,
            height,
        )

        painter.fillRect(
            x - 2,
            y - 2,
            width + 4,
            height + 4,
            QColor("#FFFFFF"),
        )

        painter.drawImage(
            self._image_rect,
            self._image,
        )

        # Contorno necessário principalmente para páginas em branco.
        painter.setPen(
            QPen(
                QColor("#B8CCE6"),
                1,
            )
        )
        painter.drawRect(
            self._image_rect.adjusted(
                0,
                0,
                -1,
                -1,
            )
        )

        if self._existing is not None:
            crop = self._existing

            rx = x + round(crop.x * width)
            ry = y + round(crop.y * height)
            rw = max(1, round(crop.w * width))
            rh = max(1, round(crop.h * height))

            painter.setPen(
                QPen(
                    QColor("#087AF7"),
                    2,
                )
            )
            painter.drawRect(
                rx,
                ry,
                rw,
                rh,
            )

        if (
            self._start is not None
            and self._end is not None
        ):
            rect = QRect(
                self._start,
                self._end,
            ).normalized()

            painter.fillRect(
                rect,
                QColor(
                    8,
                    122,
                    247,
                    55,
                ),
            )

            painter.setPen(
                QPen(
                    QColor("#087AF7"),
                    2,
                )
            )
            painter.drawRect(rect)


class ReferencePdfEditorPage(PdfEditorPage):
    """Editor PDF com o layout claro da imagem de referência."""

    def __init__(self, app_root: Path) -> None:
        app_root = Path(app_root)

        # A capa enviada pelo usuário é copiada como capa padrão HD do portable.
        resource = (
            app_root
            / "resources"
            / "pdf-default-cover.png"
        )
        data_cover = (
            app_root
            / "data"
            / "capa_padrao.png"
        )

        try:
            if resource.is_file():
                data_cover.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                shutil.copy2(
                    resource,
                    data_cover,
                )
        except Exception:
            pass

        super().__init__(app_root)

    def _start_crop(self) -> None:
        # Toda a lógica de recorte está centralizada e corrigida na página base.
        super()._start_crop()

    def _crop_done(self, crop) -> None:
        super()._crop_done(crop)

    def _tool_button(
        self,
        text: str,
        slot,
        tone: str = "blue",
    ) -> QPushButton:
        button = self._button(text, slot)
        button.setProperty(
            "toolTone",
            tone,
        )
        button.setObjectName(
            "pdfToolButton"
        )
        return button

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # -------------------------------------------------
        # Barra de ferramentas
        # -------------------------------------------------
        left = QFrame()
        left.setObjectName("pdfSideTools")
        left.setFixedWidth(190)

        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(7)

        back = self._tool_button(
            "←  Voltar ao Monitor",
            self.back_requested.emit,
            "blue",
        )
        back.setMinimumHeight(44)
        ll.addWidget(back)

        tools_title = QLabel("Ferramentas PDF")
        tools_title.setObjectName("pdfPanelTitle")
        ll.addWidget(tools_title)

        ll.addWidget(
            self._tool_button(
                "▣  Arquivos",
                self._choose_all,
                "blue",
            )
        )
        ll.addWidget(
            self._tool_button(
                "▤  PDF",
                self._choose_pdfs,
                "blue",
            )
        )
        ll.addWidget(
            self._tool_button(
                "✂  Cortar",
                self._start_crop,
                "purple",
            )
        )
        ll.addWidget(
            self._tool_button(
                "⛶  Redimensionar",
                self._resize_visual,
                "pink",
            )
        )
        ll.addWidget(
            self._tool_button(
                "⊕  Criar",
                self._create_blank,
                "cyan",
            )
        )
        ll.addWidget(
            self._tool_button(
                "▥  Excluir",
                self._delete,
                "red",
            )
        )
        ll.addWidget(
            self._tool_button(
                "↕  Ordenar",
                self._focus_reorder,
                "cyan",
            )
        )

        ll.addStretch(1)

        drop = QLabel(
            "☁\n\nArraste PDF/imagem\nou selecione"
        )
        drop.setObjectName("pdfMiniDrop")
        drop.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        drop.setMinimumHeight(115)
        ll.addWidget(drop)

        select = self._button(
            "Selecionar",
            self._choose_all,
        )
        select.setObjectName("pdfPrimary")
        ll.addWidget(select)

        root.addWidget(left)

        # -------------------------------------------------
        # Área principal
        # -------------------------------------------------
        center = QFrame()
        center.setObjectName("pdfMainCard")

        middle = QVBoxLayout(center)
        middle.setContentsMargins(14, 12, 14, 12)
        middle.setSpacing(10)

        title = QLabel(
            "Visualização do documento"
        )
        title.setObjectName("pdfMainTitle")
        middle.addWidget(title)

        subtitle = QLabel(
            "Clique em uma miniatura para trocar de página. "
            "Arraste para reordenar."
        )
        subtitle.setObjectName("pdfMuted")
        middle.addWidget(subtitle)

        controls = QHBoxLayout()
        controls.setSpacing(7)

        minus = self._button(
            "−",
            lambda: self._zoom(-.15),
        )
        minus.setFixedWidth(42)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName(
            "pdfZoomValue"
        )
        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        plus = self._button(
            "+",
            lambda: self._zoom(.15),
        )
        plus.setFixedWidth(42)

        fit = self._button(
            "⛶  Ajustar",
            lambda: self._set_zoom(1.0),
        )

        undo = self._button(
            "↶",
            self._undo,
        )
        undo.setFixedWidth(42)

        redo = self._button(
            "↷",
            self._redo,
        )
        redo.setFixedWidth(42)

        clear = self._button(
            "▱  Limpar",
            self._clear,
        )

        controls.addWidget(minus)
        controls.addWidget(self.zoom_label)
        controls.addWidget(plus)
        controls.addWidget(fit)
        controls.addWidget(undo)
        controls.addWidget(redo)
        controls.addWidget(clear)
        controls.addStretch(1)

        self.thumb_mode = self._button(
            "▦  Miniaturas",
            lambda: self._set_list_mode(True),
        )
        self.list_mode = self._button(
            "☷  Lista",
            lambda: self._set_list_mode(False),
        )

        controls.addWidget(self.thumb_mode)
        controls.addWidget(self.list_mode)

        self.page_count = QLabel("0 páginas")
        self.page_count.setObjectName(
            "pdfMuted"
        )
        controls.addWidget(self.page_count)

        middle.addLayout(controls)

        content = QHBoxLayout()
        content.setSpacing(8)

        self.preview = ReferencePdfPreview()
        self.preview.setObjectName("pdfPreview")
        self.preview.crop_selected.connect(
            self._crop_done
        )
        self.preview.crop_cancelled.connect(
            self._crop_cancelled
        )
        content.addWidget(
            self.preview,
            1,
        )

        self.thumbs = ReorderList()
        self.thumbs.setObjectName(
            "pdfThumbs"
        )
        self.thumbs.setFixedWidth(116)
        self.thumbs.setVerticalScrollMode(
            self.thumbs.ScrollMode.ScrollPerPixel
        )
        self.thumbs.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.thumbs.currentRowChanged.connect(
            self._select
        )
        self.thumbs.reorder_requested.connect(
            self._reorder
        )
        content.addWidget(self.thumbs)

        middle.addLayout(content, 1)

        self.status = QLabel("")
        self.status.setObjectName("pdfMuted")
        middle.addWidget(self.status)

        root.addWidget(center, 1)

        # -------------------------------------------------
        # Capa e exportação
        # -------------------------------------------------
        right = QFrame()
        right.setObjectName("pdfExportCard")
        right.setFixedWidth(250)

        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.setSpacing(9)

        title2 = QLabel("▣  Capa e Exportação")
        title2.setObjectName("pdfPanelTitle")
        rl.addWidget(title2)

        self.include_cover = QCheckBox(
            "Incluir capa padrão"
        )
        self.include_cover.setChecked(True)
        self.include_cover.setObjectName(
            "pdfCoverCheck"
        )
        rl.addWidget(self.include_cover)

        self.cover = QLabel()
        self.cover.setObjectName(
            "pdfCoverPreview"
        )
        self.cover.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.cover.setMinimumHeight(305)
        rl.addWidget(self.cover)

        change = self._button(
            "▧  Trocar capa",
            self._change_cover,
        )
        change.setObjectName(
            "pdfSecondary"
        )
        rl.addWidget(change)

        note = QLabel(
            "A capa é opcional. O documento mantém "
            "a ordem mostrada nas miniaturas."
        )
        note.setObjectName("pdfMuted")
        note.setWordWrap(True)
        rl.addWidget(note)

        rl.addStretch(1)

        self.export_button = self._button(
            "▤  GERAR PDF",
            self._export,
        )
        self.export_button.setObjectName(
            "pdfExport"
        )
        self.export_button.setMinimumHeight(54)
        rl.addWidget(self.export_button)

        root.addWidget(right)

        self.setStyleSheet(
            """
            QFrame#pdfSideTools,
            QFrame#pdfMainCard,
            QFrame#pdfExportCard {
                background:#FFFFFF;
                border:1px solid #D4E4F5;
                border-radius:12px;
            }

            QLabel#pdfPanelTitle {
                color:#08245F;
                font-size:16px;
                font-weight:900;
                padding:4px 0;
            }

            QLabel#pdfMainTitle {
                color:#08245F;
                font-size:20px;
                font-weight:900;
            }

            QLabel#pdfMuted {
                color:#6079A5;
                font-size:10px;
            }

            QLabel#pdfZoomValue {
                color:#08245F;
                font-size:12px;
                font-weight:900;
                min-width:48px;
            }

            QLabel#pdfMiniDrop {
                background:#F8FBFF;
                color:#315A8C;
                border:1px dashed #C9DDF2;
                border-radius:10px;
                font-size:10px;
            }

            QLabel#pdfCoverPreview {
                background:#FBFDFF;
                border:1px solid #D4E4F5;
                border-radius:10px;
                padding:8px;
            }

            QPushButton {
                min-height:34px;
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
                border-radius:8px;
                padding:7px 11px;
                font-weight:800;
            }

            QPushButton:hover {
                background:#EEF6FF;
            }

            QPushButton#pdfPrimary {
                background:#087AF7;
                color:#FFFFFF;
                border:0;
            }

            QPushButton#pdfSecondary {
                background:#FFFFFF;
                color:#0C3974;
                border:1px solid #C9DDF2;
            }

            QPushButton#pdfExport {
                background:#08A66B;
                color:#FFFFFF;
                border:0;
                font-size:12px;
                font-weight:900;
            }

            QPushButton#pdfToolButton {
                text-align:left;
                background:#FFFFFF;
                border:1px solid #D4E4F5;
                color:#0C3974;
            }

            QPushButton#pdfToolButton[toolTone='blue'] {
                border-left:3px solid #087AF7;
            }

            QPushButton#pdfToolButton[toolTone='purple'] {
                border-left:3px solid #8B3CF6;
            }

            QPushButton#pdfToolButton[toolTone='pink'] {
                border-left:3px solid #EA3158;
            }

            QPushButton#pdfToolButton[toolTone='cyan'] {
                border-left:3px solid #13B6E9;
            }

            QPushButton#pdfToolButton[toolTone='red'] {
                border-left:3px solid #EA3158;
            }

            QListWidget#pdfThumbs {
                background:#F8FBFF;
                border:1px solid #D4E4F5;
                border-radius:8px;
            }

            QCheckBox#pdfCoverCheck {
                color:#163B70;
                font-weight:700;
            }
            """
        )

    def _refresh_cover(self) -> None:
        try:
            image = _pil_to_qimage(
                self.model.current_cover_image()
            )

            pixmap = QPixmap.fromImage(
                image
            ).scaled(
                190,
                285,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.cover.setPixmap(pixmap)

        except Exception as exc:
            self.status.setText(str(exc))
