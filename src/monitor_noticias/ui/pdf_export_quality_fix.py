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

from pypdf import PageObject, PdfWriter
from pypdf.generic import (
    BooleanObject,
    DictionaryObject,
    EncodedStreamObject,
    NameObject,
    NumberObject,
)

from monitor_noticias.pdf_editor.core import (
    PdfEditorModel,
    PdfExportQuality,
    PdfItemKind,
)
from monitor_noticias.ui import pdf_editor_page as pdf_page_module


log = logging.getLogger(__name__)

_INSTALLED = False

DEFAULT_IMAGE_DPI = 300.0
MIN_VALID_DPI = 36.0
MAX_VALID_DPI = 1200.0


def _safe_dpi(
    value,
    fallback: float = DEFAULT_IMAGE_DPI,
) -> float:
    try:
        dpi = float(value)

        if (
            MIN_VALID_DPI
            <= dpi
            <= MAX_VALID_DPI
        ):
            return dpi

    except Exception:
        pass

    return float(
        fallback
    )


def _image_dpi(
    image: Image.Image,
) -> tuple[float, float]:
    raw = image.info.get(
        "dpi"
    )

    if (
        isinstance(
            raw,
            (tuple, list),
        )
        and len(raw) >= 2
    ):
        return (
            _safe_dpi(
                raw[0]
            ),
            _safe_dpi(
                raw[1]
            ),
        )

    if isinstance(
        raw,
        (int, float),
    ):
        dpi = _safe_dpi(
            raw
        )
        return (
            dpi,
            dpi,
        )

    return (
        DEFAULT_IMAGE_DPI,
        DEFAULT_IMAGE_DPI,
    )


def _page_for_pixels(
    width_px: int,
    height_px: int,
    dpi_x: float,
    dpi_y: float,
) -> PageObject:
    width_px = max(
        1,
        int(
            width_px
        ),
    )
    height_px = max(
        1,
        int(
            height_px
        ),
    )

    dpi_x = _safe_dpi(
        dpi_x
    )
    dpi_y = _safe_dpi(
        dpi_y
    )

    width_pt = (
        float(
            width_px
        )
        / dpi_x
        * 72.0
    )
    height_pt = (
        float(
            height_px
        )
        / dpi_y
        * 72.0
    )

    return PageObject.create_blank_page(
        width=max(
            1.0,
            width_pt,
        ),
        height=max(
            1.0,
            height_pt,
        ),
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
        f"{page_width:.8f} 0 0 "
        f"{page_height:.8f} 0 0 cm\n"
        "/Im0 Do\n"
        "Q\n"
    ).encode(
        "ascii"
    )

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


def _write_export_log(
    self: PdfEditorModel,
    lines: list[str],
) -> None:
    try:
        target = (
            self.data_dir
            / "pdf_export_quality.log"
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            "\n".join(
                lines
            )
            + "\n",
            encoding="utf-8",
        )

    except Exception:
        log.exception(
            "Não foi possível gravar o log de qualidade do PDF."
        )


def _append_original_jpeg(
    self: PdfEditorModel,
    writer: PdfWriter,
    source: Path,
    diagnostics: list[str] | None = None,
) -> bool:
    source = Path(
        source
    )

    if (
        source.suffix.lower()
        not in {
            ".jpg",
            ".jpeg",
        }
        or not source.is_file()
    ):
        return False

    try:
        with Image.open(
            source
        ) as image:
            image.verify()

        with Image.open(
            source
        ) as image:
            width = int(
                image.width
            )
            height = int(
                image.height
            )
            mode = str(
                image.mode
            ).upper()

            dpi_x, dpi_y = (
                _image_dpi(
                    image
                )
            )

            if mode == "RGB":
                color_space = (
                    "/DeviceRGB"
                )
            elif mode == "L":
                color_space = (
                    "/DeviceGray"
                )
            else:
                return False

            try:
                orientation = (
                    image.getexif()
                    .get(
                        274,
                        1,
                    )
                )
            except Exception:
                orientation = 1

            if orientation not in {
                None,
                1,
            }:
                return False

        raw = source.read_bytes()

        if len(raw) < 4:
            return False

        page = _page_for_pixels(
            width,
            height,
            dpi_x,
            dpi_y,
        )

        stream = (
            EncodedStreamObject()
        )

        # JPEG ORIGINAL: nenhuma recompressão.
        stream._data = raw

        stream.update(
            {
                NameObject("/Type"):
                    NameObject(
                        "/XObject"
                    ),
                NameObject("/Subtype"):
                    NameObject(
                        "/Image"
                    ),
                NameObject("/Width"):
                    NumberObject(
                        width
                    ),
                NameObject("/Height"):
                    NumberObject(
                        height
                    ),
                NameObject("/ColorSpace"):
                    NameObject(
                        color_space
                    ),
                NameObject("/BitsPerComponent"):
                    NumberObject(
                        8
                    ),
                NameObject("/Filter"):
                    NameObject(
                        "/DCTDecode"
                    ),

                # Evita que o visualizador aplique suavização que deixa
                # screenshots/textos pequenos aparentemente borrados.
                NameObject("/Interpolate"):
                    BooleanObject(
                        False
                    ),
            }
        )

        _attach_image_xobject(
            writer,
            page,
            stream,
        )

        writer.add_page(
            page
        )

        if diagnostics is not None:
            diagnostics.append(
                (
                    f"JPEG ORIGINAL | {source.name} | "
                    f"{width}x{height} px -> "
                    f"{width}x{height} px | "
                    f"DPI {dpi_x:.2f}x{dpi_y:.2f} | "
                    "sem recompressao | interpolate=false"
                )
            )

        return True

    except Exception:
        log.exception(
            "Falha ao inserir JPEG original; usando fallback lossless."
        )
        return False


def _flatten_to_rgb(
    image: Image.Image,
) -> Image.Image:
    if image.mode == "RGB":
        return image.copy()

    if image.mode in {
        "RGBA",
        "LA",
    } or (
        image.mode == "P"
        and "transparency"
        in image.info
    ):
        rgba = image.convert(
            "RGBA"
        )

        background = Image.new(
            "RGBA",
            rgba.size,
            (
                255,
                255,
                255,
                255,
            ),
        )

        background.alpha_composite(
            rgba
        )

        return background.convert(
            "RGB"
        )

    return image.convert(
        "RGB"
    )


def _append_raster_native(
    self: PdfEditorModel,
    writer: PdfWriter,
    image: Image.Image,
    *,
    source_name: str = "imagem",
    diagnostics: list[str] | None = None,
) -> None:
    """Insere todos os pixels da imagem, sem resize/downsample."""

    dpi_x, dpi_y = (
        _image_dpi(
            image
        )
    )

    rgb = _flatten_to_rgb(
        image
    )

    width = int(
        rgb.width
    )
    height = int(
        rgb.height
    )

    page = _page_for_pixels(
        width,
        height,
        dpi_x,
        dpi_y,
    )

    stream = (
        EncodedStreamObject()
    )

    # Flate é lossless. level=1 altera apenas tamanho/tempo, nunca pixels.
    stream._data = zlib.compress(
        rgb.tobytes(),
        level=1,
    )

    stream.update(
        {
            NameObject("/Type"):
                NameObject(
                    "/XObject"
                ),
            NameObject("/Subtype"):
                NameObject(
                    "/Image"
                ),
            NameObject("/Width"):
                NumberObject(
                    width
                ),
            NameObject("/Height"):
                NumberObject(
                    height
                ),
            NameObject("/ColorSpace"):
                NameObject(
                    "/DeviceRGB"
                ),
            NameObject("/BitsPerComponent"):
                NumberObject(
                    8
                ),
            NameObject("/Filter"):
                NameObject(
                    "/FlateDecode"
                ),
            NameObject("/Interpolate"):
                BooleanObject(
                    False
                ),
        }
    )

    _attach_image_xobject(
        writer,
        page,
        stream,
    )

    writer.add_page(
        page
    )

    if diagnostics is not None:
        diagnostics.append(
            (
                f"RASTER LOSSLESS | {source_name} | "
                f"{width}x{height} px -> "
                f"{width}x{height} px | "
                f"DPI {dpi_x:.2f}x{dpi_y:.2f} | "
                "sem downsample | interpolate=false"
            )
        )


def _save_config_actual_cover(
    self: PdfEditorModel,
) -> None:
    data: dict[
        str,
        str,
    ] = {}

    if self.custom_cover is not None:
        try:
            relative = (
                Path(
                    self.custom_cover
                )
                .resolve()
                .relative_to(
                    self.app_root.resolve()
                )
            )

            data[
                "custom_cover"
            ] = (
                relative.as_posix()
            )

        except Exception:
            data[
                "custom_cover"
            ] = (
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
    source = Path(
        source
    )

    if not source.is_file():
        raise FileNotFoundError(
            source
        )

    with Image.open(
        source
    ) as image:
        image.verify()

    suffix = (
        source.suffix.lower()
        or ".png"
    )

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

    self.custom_cover = (
        target
    )

    _save_config_actual_cover(
        self
    )


def _export_native_quality(
    self: PdfEditorModel,
    output: Path,
    *,
    include_cover: bool = True,
    quality:
        PdfExportQuality
        = PdfExportQuality.HIGH,
    title: str = "",
    author: str = "",
) -> Path:
    if (
        not self.pages
        and not include_cover
    ):
        raise ValueError(
            "Adicione ao menos uma página "
            "ou mantenha a capa ativada."
        )

    output = Path(
        output
    )

    if (
        output.suffix.lower()
        != ".pdf"
    ):
        output = (
            output.with_name(
                output.name
                + ".pdf"
            )
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = PdfWriter()

    diagnostics: list[str] = [
        "EXPORTACAO PDF - QUALIDADE NATIVA",
        f"arquivo={output}",
        (
            "regra=nenhuma imagem raster e reduzida "
            "antes de entrar no PDF"
        ),
        "",
    ]

    metadata: dict[
        str,
        str,
    ] = {}

    if title.strip():
        metadata[
            "/Title"
        ] = title.strip()

    if author.strip():
        metadata[
            "/Author"
        ] = author.strip()

    if metadata:
        writer.add_metadata(
            metadata
        )

    if include_cover:
        cover_inserted = False

        if (
            self.custom_cover
            and Path(
                self.custom_cover
            ).is_file()
        ):
            cover_inserted = (
                _append_original_jpeg(
                    self,
                    writer,
                    Path(
                        self.custom_cover
                    ),
                    diagnostics,
                )
            )

        if not cover_inserted:
            cover_image = (
                self.current_cover_image()
            )

            _append_raster_native(
                self,
                writer,
                cover_image,
                source_name="capa",
                diagnostics=diagnostics,
            )

    for index, data in enumerate(
        self.pages,
        start=1,
    ):
        if (
            data.kind
            is PdfItemKind.PDF
            and data.rotation == 0
            and not data.flip_x
            and data.crop is None
        ):
            self._append_vector(
                writer,
                data,
            )

            diagnostics.append(
                (
                    f"PAGINA {index} | PDF VETORIAL | "
                    f"{Path(data.path).name} | "
                    "sem rasterizacao"
                )
            )

            continue

        if (
            data.kind
            is PdfItemKind.IMAGE
            and data.rotation == 0
            and not data.flip_x
            and data.crop is None
            and _append_original_jpeg(
                self,
                writer,
                Path(
                    data.path
                ),
                diagnostics,
            )
        ):
            continue

        rendered = (
            self.render_final_page(
                data,
                quality.dpi,
            )
        )

        source_name = (
            Path(
                data.path
            ).name
            if data.path
            else (
                f"pagina-{index}"
            )
        )

        _append_raster_native(
            self,
            writer,
            rendered,
            source_name=source_name,
            diagnostics=diagnostics,
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
        with temporary.open(
            "wb"
        ) as stream:
            writer.write(
                stream
            )

        temporary.replace(
            output
        )

    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except Exception:
            pass

    diagnostics.append("")
    diagnostics.append(
        f"resultado={output}"
    )

    _write_export_log(
        self,
        diagnostics,
    )

    return output


def _export_without_blocking_dialog(
    self,
) -> None:
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
        self._export_thread
        is not None
        and self._export_thread
        .isRunning()
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

    name, _ = (
        QFileDialog.getSaveFileName(
            self,
            "Salvar PDF",
            default_name,
            "PDF (*.pdf)",
        )
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
        "Gerando PDF com os pixels originais..."
    )

    thread = QThread(
        self
    )

    worker = (
        pdf_page_module
        ._ExportWorker(
            self.model,
            Path(
                name
            ),
            self.include_cover.isChecked(),
        )
    )

    worker.moveToThread(
        thread
    )

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
            (
                "PDF gerado sem redução de resolução. "
                "Qualidade nativa preservada: "
                + path
            )
        )

    def failure(
        message: str,
    ) -> None:
        self.export_button.setEnabled(
            True
        )

        self.status.setText(
            "Erro ao gerar PDF: "
            + message
        )

    def cleanup() -> None:
        self._export_thread = None
        self._export_worker = None

    worker.done.connect(
        success
    )
    worker.failed.connect(
        failure
    )

    worker.done.connect(
        thread.quit
    )
    worker.failed.connect(
        thread.quit
    )

    thread.finished.connect(
        worker.deleteLater
    )
    thread.finished.connect(
        cleanup
    )
    thread.finished.connect(
        thread.deleteLater
    )

    self._export_thread = (
        thread
    )
    self._export_worker = (
        worker
    )

    thread.start()


def install_pdf_export_quality_fix() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    PdfEditorModel._append_raster = (
        _append_raster_native
    )

    PdfEditorModel.save_custom_cover = (
        _save_custom_cover_original
    )

    PdfEditorModel._save_config = (
        _save_config_actual_cover
    )

    PdfEditorModel.export_pdf = (
        _export_native_quality
    )

    pdf_page_module.PdfEditorPage._export = (
        _export_without_blocking_dialog
    )

    _INSTALLED = True
