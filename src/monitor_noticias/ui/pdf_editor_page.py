from __future__ import annotations

import logging
import threading
from pathlib import Path

from PIL import Image
from PySide6.QtCore import (
    QObject,
    QPoint,
    QRect,
    QRunnable,
    QSize,
    QThread,
    QThreadPool,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.pdf_editor import (
    PdfCrop,
    PdfEditorModel,
    PdfExportQuality,
    PdfItemKind,
    SUPPORTED_IMPORTS,
)

log = logging.getLogger(__name__)

# PDFium não é seguro para renderizações concorrentes no mesmo processo.
# Prévia e miniaturas compartilham este lock para evitar fechamentos nativos
# ao trocar rapidamente entre páginas de um PDF.
_PDF_RENDER_LOCK = threading.RLock()


def _pil_to_qimage(image: Image.Image) -> QImage:
    rgb = image.convert("RGB")
    return QImage(
        rgb.tobytes(),
        rgb.width,
        rgb.height,
        rgb.width * 3,
        QImage.Format.Format_RGB888,
    ).copy()


class _ImageWorker(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, token: int, fn) -> None:
        super().__init__()
        self.token = int(token)
        self.fn = fn

    def run(self) -> None:
        try:
            image = self.fn()
            if image is None:
                raise RuntimeError("A página não pôde ser renderizada.")
            self.done.emit(
                self.token,
                _pil_to_qimage(image),
            )
        except Exception as exc:
            self.failed.emit(
                self.token,
                str(exc),
            )


class _ExportWorker(QObject):
    done = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        model: PdfEditorModel,
        output: Path,
        include_cover: bool,
    ) -> None:
        super().__init__()
        self.model = model
        self.output = Path(output)
        self.include_cover = bool(include_cover)

    def run(self) -> None:
        try:
            path = self.model.export_pdf(
                self.output,
                include_cover=self.include_cover,
                quality=PdfExportQuality.HIGH,
            )
            self.done.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class _ThumbSignals(QObject):
    ready = Signal(str, object)


class _ThumbTask(QRunnable):
    """Miniatura por snapshot da página.

    O código antigo guardava apenas o índice. Se o usuário reordenasse ou
    excluísse uma página antes do worker terminar, a miniatura podia pertencer
    a outra página. Aqui o worker recebe uma cópia imutável da página.
    """

    def __init__(
        self,
        model: PdfEditorModel,
        page,
        uid: str,
        signals: _ThumbSignals,
    ) -> None:
        super().__init__()
        self.model = model
        self.page = page.copy_deep()
        self.uid = uid
        self.signals = signals

    def run(self) -> None:
        try:
            with _PDF_RENDER_LOCK:
                image = self.model.render_final_page(
                    self.page,
                    58,
                )

            scale = min(
                56.0 / max(1, image.width),
                84.0 / max(1, image.height),
                1.0,
            )
            width = max(
                1,
                round(image.width * scale),
            )
            height = max(
                1,
                round(image.height * scale),
            )

            image = image.resize(
                (width, height),
                Image.Resampling.LANCZOS,
            )

            self.signals.ready.emit(
                self.uid,
                _pil_to_qimage(image),
            )
        except Exception:
            log.exception(
                "Falha ao gerar miniatura PDF"
            )


class PdfPreview(QWidget):
    crop_selected = Signal(object)
    crop_cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.setMinimumSize(620, 520)
        self.setMouseTracking(True)
        self.setFocusPolicy(
            Qt.FocusPolicy.StrongFocus
        )

        self._image: QImage | None = None
        self._zoom = 1.0
        self._image_rect = QRect()

        self._crop_mode = False
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._existing: PdfCrop | None = None

    @property
    def crop_mode(self) -> bool:
        return bool(self._crop_mode)

    def set_image(
        self,
        image: QImage | None,
        zoom: float,
        existing_crop: PdfCrop | None = None,
    ) -> None:
        self._image = image
        self._zoom = float(zoom)
        self._existing = existing_crop
        self._start = None
        self._end = None

        # Uma atualização normal da prévia sai do modo de recorte.
        self._crop_mode = False
        self.unsetCursor()
        self.update()

    def begin_crop(
        self,
        image: QImage,
        zoom: float,
        existing_crop: PdfCrop | None,
    ) -> None:
        self._image = image
        self._zoom = float(zoom)
        self._existing = existing_crop
        self._start = None
        self._end = None
        self._crop_mode = True

        self.setCursor(
            Qt.CursorShape.CrossCursor
        )
        self.setFocus(
            Qt.FocusReason.OtherFocusReason
        )
        self.update()

    def cancel_crop(self) -> None:
        was_active = self._crop_mode

        self._crop_mode = False
        self._start = None
        self._end = None
        self.unsetCursor()
        self.update()

        if was_active:
            self.crop_cancelled.emit()

    def paintEvent(self, _event) -> None:
        from PySide6.QtGui import (
            QColor,
            QFont,
            QPainter,
            QPen,
        )

        painter = QPainter(self)
        painter.fillRect(
            self.rect(),
            QColor(7, 17, 30),
        )
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        if (
            self._image is None
            or self._image.isNull()
        ):
            self._image_rect = QRect()

            cx = self.width() // 2
            cy = self.height() // 2 - 20

            painter.setPen(
                QColor(214, 164, 77)
            )
            painter.setFont(
                QFont(
                    "Sans Serif",
                    20,
                    QFont.Weight.Bold,
                )
            )
            painter.drawText(
                QRect(
                    cx - 280,
                    cy - 40,
                    560,
                    40,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "Arraste e solte seus arquivos aqui",
            )

            painter.setPen(
                QColor(164, 175, 194)
            )
            painter.setFont(
                QFont(
                    "Sans Serif",
                    12,
                )
            )
            painter.drawText(
                QRect(
                    cx - 280,
                    cy + 8,
                    560,
                    30,
                ),
                Qt.AlignmentFlag.AlignCenter,
                "Suporte a PDFs e imagens (JPG, PNG, etc.)",
            )
            return

        fit = min(
            max(1, self.width() - 34)
            / max(1, self._image.width()),
            max(1, self.height() - 34)
            / max(1, self._image.height()),
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
            Qt.GlobalColor.white,
        )

        painter.drawImage(
            self._image_rect,
            self._image,
        )

        painter.setPen(
            QPen(
                QColor(88, 111, 142),
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

            rx = x + round(
                crop.x * width
            )
            ry = y + round(
                crop.y * height
            )
            rw = max(
                1,
                round(crop.w * width),
            )
            rh = max(
                1,
                round(crop.h * height),
            )

            painter.setPen(
                QPen(
                    QColor(30, 137, 255),
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
                    30,
                    137,
                    255,
                    55,
                ),
            )

            painter.setPen(
                QPen(
                    QColor(30, 137, 255),
                    2,
                )
            )
            painter.drawRect(rect)

    def _clamp(
        self,
        point: QPoint,
    ) -> QPoint:
        rect = self._image_rect

        if rect.isNull():
            return point

        return QPoint(
            min(
                max(point.x(), rect.left()),
                rect.right(),
            ),
            min(
                max(point.y(), rect.top()),
                rect.bottom(),
            ),
        )

    def mousePressEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if (
            self._crop_mode
            and event.button()
            == Qt.MouseButton.LeftButton
            and self._image_rect.contains(
                event.position().toPoint()
            )
        ):
            self._start = self._clamp(
                event.position().toPoint()
            )
            self._end = self._start
            self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if (
            self._crop_mode
            and self._start is not None
        ):
            self._end = self._clamp(
                event.position().toPoint()
            )
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(
        self,
        event: QMouseEvent,
    ) -> None:
        if (
            not self._crop_mode
            or self._start is None
            or event.button()
            != Qt.MouseButton.LeftButton
        ):
            super().mouseReleaseEvent(event)
            return

        end = self._clamp(
            event.position().toPoint()
        )
        selected = QRect(
            self._start,
            end,
        ).normalized()

        image_rect = self._image_rect

        if (
            selected.width() >= 6
            and selected.height() >= 6
            and image_rect.width() > 0
            and image_rect.height() > 0
        ):
            x = (
                selected.left()
                - image_rect.left()
            ) / image_rect.width()
            y = (
                selected.top()
                - image_rect.top()
            ) / image_rect.height()
            w = (
                selected.width()
                / image_rect.width()
            )
            h = (
                selected.height()
                / image_rect.height()
            )

            # Garante coordenadas válidas antes de enviar ao modelo.
            x = min(
                1.0,
                max(0.0, x),
            )
            y = min(
                1.0,
                max(0.0, y),
            )
            w = min(
                1.0 - x,
                max(0.001, w),
            )
            h = min(
                1.0 - y,
                max(0.001, h),
            )

            self._crop_mode = False
            self.unsetCursor()
            self._start = None
            self._end = None

            self.crop_selected.emit(
                PdfCrop(
                    x,
                    y,
                    w,
                    h,
                )
            )
        else:
            # Mantém o modo ativo quando o usuário só clicou.
            self._start = None
            self._end = None

        self.update()
        event.accept()

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ) -> None:
        if (
            self._crop_mode
            and event.key()
            == Qt.Key.Key_Escape
        ):
            self.cancel_crop()
            event.accept()
            return

        super().keyPressEvent(event)


class ReorderList(QListWidget):
    reorder_requested = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )

    def dropEvent(
        self,
        event: QDropEvent,
    ) -> None:
        source = self.currentRow()

        if source < 0:
            event.ignore()
            return

        point = event.position().toPoint()
        target = self.indexAt(point).row()

        if target < 0:
            target = self.count()
        else:
            rect = self.visualItemRect(
                self.item(target)
            )

            if point.y() > rect.center().y():
                target += 1

        event.ignore()
        self.reorder_requested.emit(
            source,
            target,
        )


class PdfEditorPage(QWidget):
    back_requested = Signal()

    def __init__(
        self,
        app_root: Path,
    ) -> None:
        super().__init__()

        self.model = PdfEditorModel(
            app_root
        )

        self.setAcceptDrops(True)

        self._preview_token = 0
        self._preview_threads: set[QThread] = set()
        self._preview_workers: dict[int, _ImageWorker] = {}

        self._export_thread: QThread | None = None
        self._export_worker: _ExportWorker | None = None

        self._thumb_signals = _ThumbSignals()
        self._thumb_signals.ready.connect(
            self._thumbnail_ready
        )
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._pool.setExpiryTimeout(5000)

        self._thumbnail_mode = True

        self._build()
        self._shortcuts()
        self._refresh_all()

    def _button(
        self,
        text: str,
        slot,
    ) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(38)
        button.clicked.connect(slot)
        return button

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            8,
            6,
            8,
            6,
        )
        root.setSpacing(8)

        header = QHBoxLayout()

        brand = QVBoxLayout()
        brand_label = QLabel(
            "DEPARTAMENTO\nDE IMPRENSA"
        )
        brand_label.setStyleSheet(
            "font-size:22px;"
            "font-weight:700;"
            "color:#d6a44d"
        )
        brand.addWidget(brand_label)
        header.addLayout(brand)

        header.addStretch()

        center = QVBoxLayout()

        title = QLabel(
            "VISUALIZAÇÃO DO DOCUMENTO"
        )
        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        title.setStyleSheet(
            "font-size:22px;"
            "font-weight:700"
        )
        center.addWidget(title)

        subtitle = QLabel(
            "Adicione uma imagem ou PDF "
            "para começar a editar"
        )
        subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        center.addWidget(subtitle)

        bank = QLabel(
            "Banco de Opiniões 1304"
        )
        bank.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        bank.setObjectName("muted")
        center.addWidget(bank)

        header.addLayout(
            center,
            2,
        )
        header.addStretch()

        header.addWidget(
            self._button(
                "←  Voltar ao Monitor",
                self.back_requested.emit,
            )
        )

        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(10)

        left = QFrame()
        left.setFixedWidth(220)

        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(
            8,
            4,
            8,
            8,
        )
        left_layout.setSpacing(5)

        left_layout.addWidget(
            self._button(
                "↑  Arquivos",
                self._choose_all,
            )
        )
        left_layout.addWidget(
            self._button(
                "PDF",
                self._choose_pdfs,
            )
        )
        left_layout.addWidget(
            self._button(
                "✂  Cortar",
                self._start_crop,
            )
        )
        left_layout.addWidget(
            self._button(
                "⛶  Redimensionar",
                self._resize_visual,
            )
        )
        left_layout.addWidget(
            self._button(
                "▤  Criar",
                self._create_blank,
            )
        )
        left_layout.addWidget(
            self._button(
                "▥  Excluir",
                self._delete,
            )
        )
        left_layout.addWidget(
            self._button(
                "↕  Ordenar",
                self._focus_reorder,
            )
        )

        left_layout.addStretch()

        drop = QLabel(
            "☁\n\nArraste\nPDF/imagem\nou selecione"
        )
        drop.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        drop.setMinimumHeight(170)
        drop.setStyleSheet(
            "border:1px dashed #d6a44d;"
            "border-radius:8px;"
            "color:#d7d5d0"
        )
        left_layout.addWidget(drop)

        left_layout.addWidget(
            self._button(
                "Selecionar",
                self._choose_all,
            )
        )

        body.addWidget(left)

        middle = QVBoxLayout()

        controls = QHBoxLayout()

        controls.addWidget(
            self._button(
                "−",
                lambda: self._zoom(-.15),
            )
        )

        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        controls.addWidget(
            self.zoom_label
        )

        controls.addWidget(
            self._button(
                "+",
                lambda: self._zoom(.15),
            )
        )

        controls.addWidget(
            self._button(
                "⛶  Ajustar",
                lambda: self._set_zoom(1.0),
            )
        )

        controls.addSpacing(8)

        controls.addWidget(
            self._button(
                "↶",
                self._undo,
            )
        )
        controls.addWidget(
            self._button(
                "↷",
                self._redo,
            )
        )
        controls.addWidget(
            self._button(
                "▱  Limpar",
                self._clear,
            )
        )

        controls.addStretch()

        self.thumb_mode = self._button(
            "▦  Miniaturas",
            lambda: self._set_list_mode(True),
        )
        self.list_mode = self._button(
            "☷  Lista",
            lambda: self._set_list_mode(False),
        )

        controls.addWidget(
            self.thumb_mode
        )
        controls.addWidget(
            self.list_mode
        )

        self.page_count = QLabel(
            "0 páginas"
        )
        controls.addWidget(
            self.page_count
        )

        middle.addLayout(controls)

        content = QHBoxLayout()

        self.preview = PdfPreview()
        self.preview.setStyleSheet(
            "border:1px solid #4d6786"
        )
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
        self.thumbs.setFixedWidth(92)
        self.thumbs.currentRowChanged.connect(
            self._select
        )
        self.thumbs.reorder_requested.connect(
            self._reorder
        )

        content.addWidget(
            self.thumbs
        )

        middle.addLayout(
            content,
            1,
        )

        body.addLayout(
            middle,
            1,
        )

        right = QFrame()
        right.setFixedWidth(245)

        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        title2 = QLabel(
            "Capa e Exportação"
        )
        title2.setStyleSheet(
            "font-size:18px;"
            "font-weight:700"
        )
        right_layout.addWidget(title2)

        self.include_cover = QCheckBox(
            "•  Incluir capa padrão"
        )
        self.include_cover.setChecked(True)
        right_layout.addWidget(
            self.include_cover
        )

        self.cover = QLabel()
        self.cover.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.cover.setMinimumHeight(230)
        self.cover.setStyleSheet(
            "border:1px solid #d6a44d"
        )
        right_layout.addWidget(
            self.cover
        )

        right_layout.addWidget(
            self._button(
                "▧  Trocar capa",
                self._change_cover,
            )
        )

        right_layout.addStretch()

        self.export_button = self._button(
            "✔  GERAR PDF",
            self._export,
        )
        self.export_button.setMinimumHeight(
            58
        )
        right_layout.addWidget(
            self.export_button
        )

        body.addWidget(right)
        root.addLayout(
            body,
            1,
        )

        self.status = QLabel("")
        self.status.setObjectName(
            "muted"
        )
        self.status.setWordWrap(True)
        root.addWidget(
            self.status
        )

    def _shortcuts(self) -> None:
        for sequence, slot in (
            ("Ctrl+Z", self._undo),
            ("Ctrl+Y", self._redo),
            ("Delete", self._delete),
            ("Ctrl+S", self._export),
            ("Escape", self._cancel_crop),
        ):
            QShortcut(
                QKeySequence(sequence),
                self,
                activated=slot,
            )

    def refresh(
        self,
        _state=None,
    ) -> None:
        pass

    # --------------------------------------------------------------
    # IMPORTAÇÃO
    # --------------------------------------------------------------

    def _choose_all(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar arquivos",
            "",
            (
                "PDF e imagens "
                "(*.pdf *.jpg *.jpeg *.png *.webp "
                "*.bmp *.tiff *.tif)"
            ),
        )

        self._import(
            [Path(name) for name in names]
        )

    def _choose_pdfs(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar PDFs",
            "",
            "Arquivos PDF (*.pdf)",
        )

        self._import(
            [Path(name) for name in names]
        )

    def _import(
        self,
        paths: list[Path],
    ) -> None:
        if not paths:
            return

        self._cancel_crop(
            update_status=False
        )

        before = len(self.model.pages)
        errors = self.model.import_files(paths)
        after = len(self.model.pages)

        self._refresh_all()

        added = max(
            0,
            after - before,
        )

        if added:
            self.status.setText(
                f"{added} página(s) adicionada(s)."
            )

        for error in errors:
            QMessageBox.critical(
                self,
                "Editor de PDF",
                error,
            )

    def dragEnterEvent(
        self,
        event: QDragEnterEvent,
    ) -> None:
        if (
            event.mimeData().hasUrls()
            and any(
                Path(
                    url.toLocalFile()
                ).suffix.lower()
                in SUPPORTED_IMPORTS
                for url in event.mimeData().urls()
            )
        ):
            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(
        self,
        event: QDropEvent,
    ) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]

        self._import(paths)
        event.acceptProposedAction()

    # --------------------------------------------------------------
    # EDIÇÃO / PÁGINAS
    # --------------------------------------------------------------

    def _create_blank(self) -> None:
        """Cria uma nova página A4 em branco e a seleciona."""
        self._cancel_crop(
            update_status=False
        )

        new_index = self.model.create_blank_page()

        # Garante seleção, mesmo se futuramente o model mudar sua política.
        self.model.selected_index = new_index

        self._refresh_all()

        if (
            0 <= new_index
            < self.thumbs.count()
        ):
            self.thumbs.setCurrentRow(
                new_index
            )
            self.thumbs.scrollToItem(
                self.thumbs.item(
                    new_index
                )
            )

        self.status.setText(
            f"Nova página em branco criada "
            f"(página {new_index + 1})."
        )

    def _delete(self) -> None:
        self._cancel_crop(
            update_status=False
        )

        if self.model.delete_selected():
            self._refresh_all()
            self.status.setText(
                "Página excluída."
            )
        elif self.model.pages:
            self.status.setText(
                "Selecione uma página para excluir."
            )

    def _clear(self) -> None:
        if not self.model.pages:
            return

        answer = QMessageBox.question(
            self,
            "Limpar",
            "Remover todas as páginas do documento?",
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self._cancel_crop(
            update_status=False
        )

        if self.model.clear_all():
            self._refresh_all()
            self.status.setText(
                "Documento limpo."
            )

    def _undo(self) -> None:
        self._cancel_crop(
            update_status=False
        )

        if self.model.undo():
            self._refresh_all()
            self.status.setText(
                "Última alteração desfeita."
            )

    def _redo(self) -> None:
        self._cancel_crop(
            update_status=False
        )

        if self.model.redo():
            self._refresh_all()
            self.status.setText(
                "Alteração refeita."
            )

    def _zoom(
        self,
        delta: float,
    ) -> None:
        self._set_zoom(
            self.model.zoom + delta
        )

    def _set_zoom(
        self,
        value: float,
    ) -> None:
        self.model.set_zoom(value)

        self.zoom_label.setText(
            f"{round(self.model.zoom * 100)}%"
        )

        # Se estiver cortando, atualizar zoom no meio da seleção causaria
        # coordenadas diferentes. Saímos do modo e renderizamos novamente.
        self._cancel_crop(
            update_status=False
        )
        self._request_preview()

    def _resize_visual(self) -> None:
        if (
            self.model.selected_index
            not in range(
                len(self.model.pages)
            )
        ):
            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Selecione uma página para redimensionar.",
            )
            return

        value, ok = QInputDialog.getItem(
            self,
            "Redimensionar visualização",
            "Escolha a escala de visualização da página:",
            [
                "75%",
                "90%",
                "100%",
                "110%",
                "125%",
            ],
            2,
            False,
        )

        if ok:
            self._set_zoom(
                float(
                    value.removesuffix("%")
                )
                / 100.0
            )

    def _focus_reorder(self) -> None:
        if len(self.model.pages) < 2:
            QMessageBox.information(
                self,
                "Reordenar",
                "Adicione pelo menos duas páginas para reordenar.",
            )
            return

        self._cancel_crop(
            update_status=False
        )

        self.thumbs.setFocus()

        QMessageBox.information(
            self,
            "Reordenar",
            "Arraste as miniaturas na coluna lateral "
            "para mudar a ordem das páginas.",
        )

    def _reorder(
        self,
        source: int,
        target: int,
    ) -> None:
        self._cancel_crop(
            update_status=False
        )

        if self.model.reorder(
            source,
            target,
        ):
            self._refresh_all()
            self.status.setText(
                "Ordem das páginas atualizada."
            )

    def _select(
        self,
        row: int,
    ) -> None:
        if (
            0 <= row
            < len(self.model.pages)
        ):
            self.model.selected_index = row

        elif not self.model.pages:
            self.model.selected_index = -1

        self._cancel_crop(
            update_status=False
        )
        self._request_preview()

        if (
            0 <= self.model.selected_index
            < len(self.model.pages)
        ):
            self.status.setText(
                f"Página {self.model.selected_index + 1} de "
                f"{len(self.model.pages)} selecionada."
            )

    # --------------------------------------------------------------
    # CORTE — correção principal
    # --------------------------------------------------------------

    def _start_crop(self) -> None:
        index = self.model.selected_index

        if (
            index
            not in range(
                len(self.model.pages)
            )
        ):
            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Selecione uma página para recortar.",
            )
            return

        # Invalida qualquer preview assíncrono pendente.
        self._preview_token += 1

        page = self.model.pages[
            index
        ].copy_deep()

        self.status.setText(
            "Preparando o modo de corte..."
        )

        try:
            # O corte é preparado de forma direta. Assim não disputa token com
            # a atualização normal da prévia, que era a origem do defeito.
            with _PDF_RENDER_LOCK:
                rendered = (
                    self.model.render_transformed_source(
                        page,
                        120,
                    )
                )
            image = _pil_to_qimage(
                rendered
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Não foi possível preparar "
                f"o recorte:\n{exc}",
            )
            self.status.setText(
                "Falha ao preparar o recorte."
            )
            return

        self.preview.begin_crop(
            image,
            self.model.zoom,
            page.crop,
        )

        self.status.setText(
            "MODO CORTAR ATIVO — clique e arraste sobre "
            "a área que deseja MANTER. Ao soltar, o recorte "
            "será aplicado. ESC cancela."
        )

    def _crop_done(
        self,
        crop: PdfCrop,
    ) -> None:
        # Revalidação antes de salvar.
        x = min(
            1.0,
            max(0.0, float(crop.x)),
        )
        y = min(
            1.0,
            max(0.0, float(crop.y)),
        )
        w = min(
            1.0 - x,
            max(0.001, float(crop.w)),
        )
        h = min(
            1.0 - y,
            max(0.001, float(crop.h)),
        )

        if (
            w <= 0.001
            or h <= 0.001
        ):
            self.status.setText(
                "Recorte ignorado: área muito pequena."
            )
            return

        if self.model.apply_crop(
            PdfCrop(
                x,
                y,
                w,
                h,
            )
        ):
            # Invalida previews anteriores e solicita uma imagem já recortada.
            self._preview_token += 1
            self._refresh_all()

            self.status.setText(
                "Recorte aplicado. A prévia e a exportação "
                "agora usam somente a área selecionada. "
                "Ctrl+Z desfaz."
            )

    def _crop_cancelled(self) -> None:
        self.status.setText(
            "Corte cancelado."
        )

    def _cancel_crop(
        self,
        *,
        update_status: bool = True,
    ) -> None:
        if not hasattr(
            self,
            "preview",
        ):
            return

        active = self.preview.crop_mode

        if active:
            self.preview.cancel_crop()

            if update_status:
                self.status.setText(
                    "Corte cancelado."
                )

    # --------------------------------------------------------------
    # PRÉVIA — corrige a corrida de tokens
    # --------------------------------------------------------------

    def _run_image_worker(
        self,
        token: int,
        fn,
        on_done=None,
    ) -> None:
        """Executa renderização sem alterar o token recebido.

        O defeito antigo estava aqui: quando já havia um worker rodando, a
        função incrementava _preview_token outra vez. O worker recém-criado
        passava a ser considerado obsoleto antes mesmo de terminar.
        Isso quebrava o recorte e fazia uma página recém-criada parecer que
        não tinha sido criada.
        """
        thread = QThread(self)
        worker = _ImageWorker(
            token,
            fn,
        )
        worker.moveToThread(thread)

        # Mantém referências fortes até o término.
        self._preview_threads.add(
            thread
        )
        self._preview_workers[
            id(thread)
        ] = worker

        thread.started.connect(
            worker.run
        )

        def done(
            result_token: int,
            image: QImage,
        ) -> None:
            try:
                if (
                    result_token
                    == self._preview_token
                ):
                    if on_done:
                        on_done(image)
                    else:
                        self.preview.set_image(
                            image,
                            self.model.zoom,
                            None,
                        )
            finally:
                thread.quit()

        def failed(
            result_token: int,
            message: str,
        ) -> None:
            try:
                if (
                    result_token
                    == self._preview_token
                ):
                    self.status.setText(
                        message
                    )
            finally:
                thread.quit()

        def cleanup() -> None:
            self._preview_workers.pop(
                id(thread),
                None,
            )
            self._preview_threads.discard(
                thread
            )

        worker.done.connect(done)
        worker.failed.connect(failed)

        thread.finished.connect(
            cleanup
        )
        thread.finished.connect(
            worker.deleteLater
        )
        thread.finished.connect(
            thread.deleteLater
        )

        thread.start()

    def _request_preview(self) -> None:
        """Atualiza a página selecionada sem criar múltiplos QThreads.

        A combinação anterior de:
        - um QThread novo a cada clique de miniatura;
        - tarefas de miniatura no QThreadPool;
        - pypdfium2/PDFium renderizando ao mesmo tempo

        podia encerrar o processo nativamente ao trocar rapidamente de página.
        A prévia principal agora é renderizada de forma serial e protegida.
        """

        index = self.model.selected_index

        self._preview_token += 1

        if (
            index
            not in range(
                len(self.model.pages)
            )
        ):
            self.preview.set_image(
                None,
                self.model.zoom,
            )
            return

        page = self.model.pages[
            index
        ].copy_deep()

        try:
            with _PDF_RENDER_LOCK:
                if page.crop is not None:
                    rendered = self.model.render_final_page(
                        page,
                        120,
                    )
                else:
                    rendered = self.model.render_transformed_source(
                        page,
                        120,
                    )

            image = _pil_to_qimage(
                rendered
            )

            self.preview.set_image(
                image,
                self.model.zoom,
                None,
            )

        except Exception as exc:
            log.exception(
                "Falha ao trocar a página na prévia do Editor PDF"
            )
            self.preview.set_image(
                None,
                self.model.zoom,
            )
            self.status.setText(
                "Não foi possível visualizar esta página: "
                f"{exc}"
            )


    # --------------------------------------------------------------
    # MINIATURAS / LISTA
    # --------------------------------------------------------------

    def _set_list_mode(
        self,
        thumbnails: bool,
    ) -> None:
        self._thumbnail_mode = bool(
            thumbnails
        )

        self.thumbs.setIconSize(
            QSize(56, 84)
            if self._thumbnail_mode
            else QSize(0, 0)
        )

        height = (
            108
            if self._thumbnail_mode
            else 46
        )

        for index in range(
            self.thumbs.count()
        ):
            self.thumbs.item(
                index
            ).setSizeHint(
                QSize(
                    80,
                    height,
                )
            )

    def _refresh_all(self) -> None:
        selected = self.model.selected_index

        if self.model.pages:
            selected = min(
                max(
                    0,
                    selected,
                ),
                len(self.model.pages) - 1,
            )
            self.model.selected_index = (
                selected
            )
        else:
            selected = -1
            self.model.selected_index = -1

        self.thumbs.blockSignals(True)
        self.thumbs.clear()

        for index, page in enumerate(
            self.model.pages
        ):
            item = QListWidgetItem(
                str(index + 1)
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                page.uid,
            )
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.thumbs.addItem(item)

            self._pool.start(
                _ThumbTask(
                    self.model,
                    page,
                    page.uid,
                    self._thumb_signals,
                )
            )

        self.thumbs.setVisible(
            bool(self.model.pages)
        )

        count = len(
            self.model.pages
        )
        self.page_count.setText(
            f"{count} "
            f"{'página' if count == 1 else 'páginas'}"
        )

        if (
            0 <= selected
            < self.thumbs.count()
        ):
            self.thumbs.setCurrentRow(
                selected
            )

        self.thumbs.blockSignals(False)

        self._set_list_mode(
            self._thumbnail_mode
        )

        self.zoom_label.setText(
            f"{round(self.model.zoom * 100)}%"
        )

        self._refresh_cover()
        self._request_preview()

    def _thumbnail_ready(
        self,
        uid: str,
        image: QImage,
    ) -> None:
        for index in range(
            self.thumbs.count()
        ):
            item = self.thumbs.item(
                index
            )

            if (
                item.data(
                    Qt.ItemDataRole.UserRole
                )
                == uid
            ):
                item.setIcon(
                    QPixmap.fromImage(
                        image
                    )
                )

                item.setSizeHint(
                    QSize(
                        80,
                        108
                        if self._thumbnail_mode
                        else 46,
                    )
                )
                break

    # --------------------------------------------------------------
    # CAPA
    # --------------------------------------------------------------

    def _refresh_cover(self) -> None:
        try:
            image = _pil_to_qimage(
                self.model.current_cover_image()
            )

            pixmap = QPixmap.fromImage(
                image
            ).scaled(
                205,
                305,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.cover.setPixmap(
                pixmap
            )

        except Exception as exc:
            self.status.setText(
                str(exc)
            )

    def _change_cover(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self,
            "Trocar capa",
            "",
            (
                "Imagem "
                "(*.jpg *.jpeg *.png *.webp "
                "*.bmp *.tiff *.tif)"
            ),
        )

        if not name:
            return

        try:
            self.model.save_custom_cover(
                Path(name)
            )
            self._refresh_cover()

            self.status.setText(
                "Capa padrão atualizada."
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Não foi possível trocar "
                f"a capa: {exc}",
            )

    # --------------------------------------------------------------
    # EXPORTAÇÃO
    # --------------------------------------------------------------

    def _export(self) -> None:
        if (
            not self.model.pages
            and not self.include_cover.isChecked()
        ):
            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Adicione ao menos uma página "
                "ou mantenha a capa ativada.",
            )
            return

        if (
            self._export_thread is not None
            and self._export_thread.isRunning()
        ):
            self.status.setText(
                "A exportação já está em andamento."
            )
            return

        default_name = (
            "RADAR DE NOTICIAS - MIDIA IMPRESSA.pdf"
            if self.include_cover.isChecked()
            else "documento.pdf"
        )

        name, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar PDF",
            default_name,
            "PDF (*.pdf)",
        )

        if not name:
            return

        self._cancel_crop(
            update_status=False
        )

        self.export_button.setEnabled(
            False
        )
        self.status.setText(
            "Gerando PDF..."
        )

        thread = QThread(self)
        worker = _ExportWorker(
            self.model,
            Path(name),
            self.include_cover.isChecked(),
        )
        worker.moveToThread(thread)

        thread.started.connect(
            worker.run
        )

        def success(
            path: str,
        ) -> None:
            self.export_button.setEnabled(
                True
            )
            self.status.setText(
                f"PDF gerado com sucesso: {path}"
            )

            box = QMessageBox(self)
            box.setWindowTitle(
                "Exportação concluída"
            )
            box.setText(
                "PDF gerado com sucesso!\n"
                f"{path}"
            )

            box.addButton(
                "OK",
                QMessageBox.ButtonRole.AcceptRole,
            )

            folder = box.addButton(
                "Abrir pasta",
                QMessageBox.ButtonRole.ActionRole,
            )

            box.exec()

            if (
                box.clickedButton()
                is folder
            ):
                QDesktopServices.openUrl(
                    QUrl.fromLocalFile(
                        str(
                            Path(path).parent
                        )
                    )
                )

        def failure(
            message: str,
        ) -> None:
            self.export_button.setEnabled(
                True
            )
            self.status.setText(
                message
            )

            QMessageBox.critical(
                self,
                "Editor de PDF",
                "Erro ao gerar PDF: "
                f"{message}",
            )

        worker.done.connect(
            thread.quit
        )
        worker.failed.connect(
            thread.quit
        )

        worker.done.connect(
            success
        )
        worker.failed.connect(
            failure
        )

        thread.finished.connect(
            worker.deleteLater
        )
        thread.finished.connect(
            thread.deleteLater
        )

        self._export_thread = thread
        self._export_worker = worker

        thread.start()
