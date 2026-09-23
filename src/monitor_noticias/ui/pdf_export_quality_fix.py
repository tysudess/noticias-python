from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
import uuid
import zlib

from PIL import Image
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog

from pypdf import PdfWriter
from pypdf.generic import (
    DictionaryObject,
    EncodedStreamObject,
    NameObject,
    NumberObject,
    PageObject,
)

from monitor_noticias.pdf_editor.core import (
    PDF_PAGE_WIDTH_PT,
    PdfEditorModel,
    PdfExportQuality,
    PdfItemKind,
)
from monitor_noticias.ui import pdf_editor_page as pdf_page_module


log = logging.getLogger(__name__)

_INSTALLED = False


def _image_page(
    writer: PdfWriter,
    width_px: int,
    height_px: int,
) -> PageObject:
    width_px = max(1, int(width_px))
    height_px = max(1, int(height_px))

    page_width = PDF_PAGE_WIDTH_PT
    page_height = (
        page_width
        * float(height_px)
        / float(width_px)
    )

    return PageObject.create_blank_page(
        width=page_width,
        height=page_height,
    )


def _attach_image_xobject(
    writer: PdfWriter,
    page: PageObject,
    stream: EncodedStreamObject,
) -> None:
    image_ref = writer._add_object(
        stream
    )

    xobjects = DictionaryObject(
        {
            NameObject("/Im0"):
                image_ref
        }
    )

    resources = DictionaryObject(
        {
            NameObject("/XObject"):
                xobjects
        }
    )

    page[
        NameObject("/Resources")
    ] = resources

    page_width = float(
        page.mediabox.width
    )
    page_height = float(
        page.mediabox.height
    )

    content = EncodedStreamObject()

    commands = (
        "q\n"
        f"{page_width:.6f} 0 0 "
        f"{page_height:.6f} 0 0 cm\n"
        "/Im0 Do\n"
        "Q\n"
    ).encode("ascii")

    content._data = zlib.compress(
        commands,
        level=1,
    )

    content[
        NameObject("/Filter")
    ] = NameObject(
        "/FlateDecode"
    )

    page[
        NameObject("/Contents")
    ] = writer._add_object(
        content
    )


def _append_original_jpeg(
    self: PdfEditorModel,
    writer: PdfWriter,
    source: Path,
) -> bool:
    """Insere JPEG original sem decodificar/recomprimir."""

    source = Path(source)

    if (
        source.suffix.lower()
        not in {".jpg", ".jpeg"}
        or not source.is_file()
    ):
        return False

    try:
        with Image.open(source) as image:
            image.verify()

        with Image.open(source) as image:
            width = int(image.width)
            height = int(image.height)
            mode = str(image.mode).upper()

            if mode == "RGB":
                color_space = "/DeviceRGB"
            elif mode == "L":
                color_space = "/DeviceGray"
            else:
                return False

            try:
                orientation = image.getexif().get(274, 1)
            except Exception:
                orientation = 1

            if orientation not in {None, 1}:
                return False

        raw = source.read_bytes()

        if len(raw) < 4:
            return False

        page = _image_page(
            writer,
            width,
            height,
        )

        stream = EncodedStreamObject()
        stream._data = raw

        stream.update(
            {
                NameObject("/Type"):
                    NameObject("/XObject"),
                NameObject("/Subtype"):
                    NameObject("/Image"),
                NameObject("/Width"):
                    NumberObject(width),
                NameObject("/Height"):
                    NumberObject(height),
                NameObject("/ColorSpace"):
                    NameObject(color_space),
                NameObject("/BitsPerComponent"):
                    NumberObject(8),
                NameObject("/Filter"):
                    NameObject("/DCTDecode"),
            }
        )

        _attach_image_xobject(
            writer,
            page,
            stream,
        )

        writer.add_page(page)
        return True

    except Exception:
        log.exception(
            "Falha ao inserir JPEG original; "
            "usando fallback lossless."
        )
        return False


def _append_raster_lossless_fast(
    self: PdfEditorModel,
    writer: PdfWriter,
    image: Image.Image,
) -> None:
    """Mantém todos os pixels; zlib level=1 só reduz tempo de CPU."""

    rgb = (
        image
        if image.mode == "RGB"
        else image.convert("RGB")
    )

    page = _image_page(
        writer,
        rgb.width,
        rgb.height,
    )

    stream = EncodedStreamObject()

    stream._data = zlib.compress(
        rgb.tobytes(),
        level=1,
    )

    stream.update(
        {
            NameObject("/Type"):
                NameObject("/XObject"),
            NameObject("/Subtype"):
                NameObject("/Image"),
            NameObject("/Width"):
                NumberObject(rgb.width),
            NameObject("/Height"):
                NumberObject(rgb.height),
            NameObject("/ColorSpace"):
                NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"):
                NumberObject(8),
            NameObject("/Filter"):
                NameObject("/FlateDecode"),
        }
    )

    _attach_image_xobject(
        writer,
        page,
        stream,
    )

    writer.add_page(page)


def _save_config_actual_cover(
    self: PdfEditorModel,
) -> None:
    data: dict[str, str] = {}

    if self.custom_cover is not None:
        try:
            relative = (
                Path(self.custom_cover)
                .resolve()
                .relative_to(
                    self.app_root.resolve()
                )
            )
            data["custom_cover"] = relative.as_posix()

        except Exception:
            data["custom_cover"] = (
                "data/"
                + Path(
                    self.custom_cover
                ).name
            )

    self.config_file.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _save_custom_cover_original(
    self: PdfEditorModel,
    source: Path,
) -> None:
    """Copia a capa sem conversão, resize ou reencode."""

    source = Path(source)

    if not source.is_file():
        raise FileNotFoundError(source)

    with Image.open(source) as image:
        image.verify()

    suffix = source.suffix.lower() or ".png"

    target = (
        self.data_dir
        / (
            "capa_padrao_usuario_original"
            + suffix
        )
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        target,
    )

    self.custom_cover = target

    _save_config_actual_cover(
        self
    )


def _export_full_quality(
    self: PdfEditorModel,
    output: Path,
    *,
    include_cover: bool = True,
    quality: PdfExportQuality = PdfExportQuality.HIGH,
    title: str = "",
    author: str = "",
) -> Path:
    """Exporta sem reduzir resolução de imagens."""

    if not self.pages and not include_cover:
        raise ValueError(
            "Adicione ao menos uma página "
            "ou mantenha a capa ativada."
        )

    output = Path(output)

    if output.suffix.lower() != ".pdf":
        output = output.with_name(
            output.name + ".pdf"
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = PdfWriter()

    metadata: dict[str, str] = {}

    if title.strip():
        metadata["/Title"] = title.strip()

    if author.strip():
        metadata["/Author"] = author.strip()

    if metadata:
        writer.add_metadata(metadata)

    if include_cover:
        cover_inserted = False

        if (
            self.custom_cover
            and Path(self.custom_cover).is_file()
        ):
            cover_inserted = _append_original_jpeg(
                self,
                writer,
                Path(self.custom_cover),
            )

        if not cover_inserted:
            _append_raster_lossless_fast(
                self,
                writer,
                self.current_cover_image(),
            )

    for data in self.pages:
        if (
            data.kind is PdfItemKind.PDF
            and data.rotation == 0
            and not data.flip_x
            and data.crop is None
        ):
            self._append_vector(
                writer,
                data,
            )
            continue

        if (
            data.kind is PdfItemKind.IMAGE
            and data.rotation == 0
            and not data.flip_x
            and data.crop is None
            and _append_original_jpeg(
                self,
                writer,
                Path(data.path),
            )
        ):
            continue

        rendered = self.render_final_page(
            data,
            quality.dpi,
        )

        _append_raster_lossless_fast(
            self,
            writer,
            rendered,
        )

    temporary = (
        output.parent
        / (
            "."
            + output.name
            + "."
            + uuid.uuid4().hex
            + ".tmp"
        )
    )

    try:
        with temporary.open("wb") as stream:
            writer.write(stream)

        temporary.replace(output)

    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except Exception:
            pass

    return output


def _export_without_blocking_success_dialog(
    self,
) -> None:
    """Exporta em thread e não abre popup modal de sucesso."""

    if (
        not self.model.pages
        and not self.include_cover.isChecked()
    ):
        self.status.setText(
            "Adicione ao menos uma página "
            "ou mantenha a capa ativada."
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

    self.export_button.setEnabled(False)

    self.status.setText(
        "Gerando PDF em qualidade original..."
    )

    thread = QThread(self)

    worker = pdf_page_module._ExportWorker(
        self.model,
        Path(name),
        self.include_cover.isChecked(),
    )

    worker.moveToThread(thread)

    thread.started.connect(
        worker.run
    )

    def success(path: str) -> None:
        self.export_button.setEnabled(True)

        self.status.setText(
            "PDF gerado com sucesso - qualidade original: "
            + path
        )

    def failure(message: str) -> None:
        self.export_button.setEnabled(True)

        self.status.setText(
            "Erro ao gerar PDF: "
            + message
        )

    def cleanup() -> None:
        self._export_thread = None
        self._export_worker = None

    worker.done.connect(success)
    worker.failed.connect(failure)

    worker.done.connect(thread.quit)
    worker.failed.connect(thread.quit)

    thread.finished.connect(
        worker.deleteLater
    )
    thread.finished.connect(
        cleanup
    )
    thread.finished.connect(
        thread.deleteLater
    )

    self._export_thread = thread
    self._export_worker = worker

    thread.start()


def install_pdf_export_quality_fix() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    PdfEditorModel._append_raster = (
        _append_raster_lossless_fast
    )
    PdfEditorModel.save_custom_cover = (
        _save_custom_cover_original
    )
    PdfEditorModel._save_config = (
        _save_config_actual_cover
    )
    PdfEditorModel.export_pdf = (
        _export_full_quality
    )
    pdf_page_module.PdfEditorPage._export = (
        _export_without_blocking_success_dialog
    )

    _INSTALLED = True
