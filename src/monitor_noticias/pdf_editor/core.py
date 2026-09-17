from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from enum import Enum
from io import BytesIO
import base64
import json
import logging
import math
from pathlib import Path
import uuid
import zlib

from PIL import Image
import pypdfium2 as pdfium
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, EncodedStreamObject, NameObject, NumberObject

log = logging.getLogger(__name__)

PDF_PAGE_WIDTH_PT = 595.276
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
SUPPORTED_IMPORTS = SUPPORTED_IMAGES | {".pdf"}


class PdfItemKind(str, Enum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    BLANK = "BLANK"


class PdfExportQuality(Enum):
    HIGH = ("Alta (recomendado)", 450)
    MEDIUM = ("Média", 300)
    COMPACT = ("Compacta", 220)

    def __init__(self, label: str, dpi: int) -> None:
        self.label = label
        self.dpi = dpi


@dataclass(slots=True)
class PdfCrop:
    x: float
    y: float
    w: float
    h: float


@dataclass(slots=True)
class PdfPageData:
    kind: PdfItemKind
    path: str = ""
    page_no: int | None = None
    rotation: int = 0
    flip_x: bool = False
    crop: PdfCrop | None = None
    uid: str = ""

    def __post_init__(self) -> None:
        if not self.uid:
            self.uid = str(uuid.uuid4())

    def copy_deep(self) -> "PdfPageData":
        return replace(self, crop=replace(self.crop) if self.crop else None)


@dataclass(slots=True)
class PdfSnapshot:
    pages: list[PdfPageData]
    selected: int


class PdfImportError(RuntimeError):
    pass


class PdfEditorModel:
    """Estado/motor equivalente ao PdfEditorScreenV2 ativo da release V8."""

    def __init__(self, app_root: Path) -> None:
        self.app_root = Path(app_root)
        self.data_dir = self.app_root / "data"
        self.config_file = self.data_dir / "config.json"
        self.custom_cover_file = self.data_dir / "capa_padrao_usuario.png"
        self.hd_default_cover_file = self.data_dir / "capa_padrao.png"
        self.resource_cover_file = self.app_root / "resources" / "pdf-default-cover.b64"
        self.pages: list[PdfPageData] = []
        self.selected_index = -1
        self.zoom = 1.0
        self.custom_cover: Path | None = None
        self._undo: deque[PdfSnapshot] = deque()
        self._redo: deque[PdfSnapshot] = deque()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_config()

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)

    def _snapshot(self) -> PdfSnapshot:
        return PdfSnapshot([p.copy_deep() for p in self.pages], self.selected_index)

    def push_undo(self) -> None:
        self._undo.append(self._snapshot())
        while len(self._undo) > 30:
            self._undo.popleft()

    def _restore(self, snap: PdfSnapshot) -> None:
        self.pages = [p.copy_deep() for p in snap.pages]
        if not self.pages:
            self.selected_index = -1
        else:
            self.selected_index = min(max(-1, snap.selected), len(self.pages) - 1)

    def undo(self) -> bool:
        if not self._undo:
            return False
        snap = self._undo.pop()
        self._redo.append(self._snapshot())
        self._restore(snap)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        snap = self._redo.pop()
        self._undo.append(self._snapshot())
        self._restore(snap)
        return True

    def set_zoom(self, value: float) -> float:
        self.zoom = min(3.0, max(0.50, float(value)))
        return self.zoom

    def import_files(self, files: list[Path]) -> list[str]:
        valid = [Path(p) for p in files if Path(p).exists() and Path(p).is_file()]
        if not valid:
            return []
        self.push_undo()
        added = 0
        errors: list[str] = []
        for file in valid:
            try:
                suffix = file.suffix.lower()
                if suffix == ".pdf":
                    reader = PdfReader(str(file))
                    if reader.is_encrypted and reader.decrypt("") == 0:
                        raise PdfImportError("PDF protegido por senha não suportada pelo fluxo original.")
                    if len(reader.pages) == 0:
                        raise PdfImportError("PDF sem páginas")
                    for index in range(len(reader.pages)):
                        self.pages.append(PdfPageData(PdfItemKind.PDF, str(file.resolve()), index))
                        added += 1
                elif suffix in SUPPORTED_IMAGES:
                    with Image.open(file) as image:
                        image.load()
                    self.pages.append(PdfPageData(PdfItemKind.IMAGE, str(file.resolve())))
                    added += 1
                else:
                    continue
            except Exception as exc:
                errors.append(f"Não foi possível importar {file.name}: {exc}")
        if added == 0:
            if self._undo:
                self._undo.pop()
        else:
            self._redo.clear()
            self.selected_index = len(self.pages) - 1
        return errors

    def create_blank_page(self) -> int:
        self.push_undo()
        self.pages.append(PdfPageData(PdfItemKind.BLANK))
        self._redo.clear()
        self.selected_index = len(self.pages) - 1
        return self.selected_index

    def delete_selected(self) -> bool:
        index = self.selected_index
        if index < 0 or index >= len(self.pages):
            return False
        self.push_undo()
        self.pages.pop(index)
        self._redo.clear()
        self.selected_index = -1 if not self.pages else min(index, len(self.pages) - 1)
        return True

    def clear_all(self) -> bool:
        if not self.pages:
            return False
        self.push_undo()
        self.pages.clear()
        self._redo.clear()
        self.selected_index = -1
        return True

    def reorder(self, source: int, target_insert_index: int) -> bool:
        if source < 0 or source >= len(self.pages):
            return False
        target = min(max(0, target_insert_index), len(self.pages))
        if target in {source, source + 1}:
            return False
        self.push_undo()
        item = self.pages.pop(source)
        if target > source:
            target -= 1
        self.pages.insert(min(max(0, target), len(self.pages)), item)
        self._redo.clear()
        self.selected_index = next(i for i, p in enumerate(self.pages) if p.uid == item.uid)
        return True

    def apply_crop(self, crop: PdfCrop) -> bool:
        index = self.selected_index
        if index < 0 or index >= len(self.pages):
            return False
        self.push_undo()
        self.pages[index].crop = PdfCrop(crop.x, crop.y, crop.w, crop.h)
        self._redo.clear()
        return True

    # Mantidos no motor porque fazem parte do estado/exportação do V2; a UI final
    # da release não possui chamada comprovada para showTransformMenu().
    def rotate_selected(self, degrees: int) -> bool:
        index = self.selected_index
        if index < 0 or index >= len(self.pages):
            return False
        self.push_undo()
        page = self.pages[index]
        page.rotation = ((page.rotation + int(degrees)) % 360 + 360) % 360
        page.crop = None
        self._redo.clear()
        return True

    def flip_selected(self) -> bool:
        index = self.selected_index
        if index < 0 or index >= len(self.pages):
            return False
        self.push_undo()
        page = self.pages[index]
        page.flip_x = not page.flip_x
        page.crop = None
        self._redo.clear()
        return True

    def render_transformed_source(self, page: PdfPageData, dpi: int) -> Image.Image:
        if page.kind is PdfItemKind.IMAGE:
            with Image.open(page.path) as src:
                image = src.convert("RGB").copy()
        elif page.kind is PdfItemKind.PDF:
            doc = pdfium.PdfDocument(page.path)
            try:
                pdf_page = doc[page.page_no or 0]
                bitmap = pdf_page.render(scale=float(dpi) / 72.0)
                image = bitmap.to_pil().convert("RGB").copy()
                bitmap.close()
                pdf_page.close()
            finally:
                doc.close()
        else:
            image = Image.new("RGB", (1240, 1754), "white")

        rotation = page.rotation % 360
        if rotation == 90:
            image = image.transpose(Image.Transpose.ROTATE_270)
        elif rotation == 180:
            image = image.transpose(Image.Transpose.ROTATE_180)
        elif rotation == 270:
            image = image.transpose(Image.Transpose.ROTATE_90)
        if page.flip_x:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        return image

    def render_final_page(self, page: PdfPageData, dpi: int) -> Image.Image:
        image = self.render_transformed_source(page, dpi)
        crop = page.crop
        if crop is None:
            return image
        nx = min(1.0, max(0.0, crop.x))
        ny = min(1.0, max(0.0, crop.y))
        nw = min(max(0.0, crop.w), 1.0 - nx)
        nh = min(max(0.0, crop.h), 1.0 - ny)
        x1 = min(image.width - 1, max(0, math.floor(nx * image.width)))
        y1 = min(image.height - 1, max(0, math.floor(ny * image.height)))
        x2 = min(image.width, max(x1 + 1, math.ceil((nx + nw) * image.width)))
        y2 = min(image.height, max(y1 + 1, math.ceil((ny + nh) * image.height)))
        return image.crop((x1, y1, x2, y2)).copy()

    def render_preview(self, index: int | None = None) -> Image.Image | None:
        idx = self.selected_index if index is None else index
        if idx < 0 or idx >= len(self.pages):
            return None
        page = self.pages[idx]
        if page.crop is not None:
            return self.render_final_page(page, 120)
        return self.render_transformed_source(page, 120)

    def render_thumbnail(self, index: int) -> Image.Image:
        image = self.render_final_page(self.pages[index], 58)
        scale = min(56.0 / image.width, 84.0 / image.height, 1.0)
        width = max(1, round(image.width * scale))
        height = max(1, round(image.height * scale))
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def save_custom_cover(self, source: Path) -> None:
        with Image.open(source) as image:
            image.convert("RGB").save(self.custom_cover_file, format="PNG")
        self.custom_cover = self.custom_cover_file
        self._save_config()

    def current_cover_image(self) -> Image.Image:
        if self.custom_cover and self.custom_cover.exists():
            with Image.open(self.custom_cover) as image:
                return image.convert("RGB").copy()
        if self.hd_default_cover_file.exists():
            with Image.open(self.hd_default_cover_file) as image:
                return image.convert("RGB").copy()
        if self.resource_cover_file.exists():
            try:
                raw = base64.b64decode(self.resource_cover_file.read_text(encoding="utf-8").strip())
                with Image.open(BytesIO(raw)) as image:
                    return image.convert("RGB").copy()
            except Exception:
                log.exception("Falha ao abrir capa padrão embutida")
        image = Image.new("RGB", (1245, 2048), (28, 28, 28))
        # O recurso original ainda será copiado no passo de assets/portable; sem ele,
        # a capa fallback exata com fonte SansSerif não é garantida por Pillow.
        return image

    def _load_config(self) -> None:
        try:
            if not self.config_file.exists():
                return
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            relative = str(data.get("custom_cover", "")).strip()
            if relative:
                candidate = self.app_root.joinpath(*relative.replace("\\", "/").split("/"))
                if candidate.exists():
                    self.custom_cover = candidate
        except Exception:
            log.exception("Falha ao ler configuração do Editor PDF")

    def _save_config(self) -> None:
        data: dict[str, str] = {}
        if self.custom_cover is not None:
            data["custom_cover"] = "data/capa_padrao_usuario.png"
        self.config_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def export_pdf(
        self,
        output: Path,
        *,
        include_cover: bool = True,
        quality: PdfExportQuality = PdfExportQuality.HIGH,
        title: str = "",
        author: str = "",
    ) -> Path:
        if not self.pages and not include_cover:
            raise ValueError("Adicione ao menos uma página ou mantenha a capa ativada.")
        output = Path(output)
        if output.suffix.lower() != ".pdf":
            output = output.with_name(output.name + ".pdf")
        output.parent.mkdir(parents=True, exist_ok=True)
        writer = PdfWriter()
        metadata: dict[str, str] = {}
        if title.strip():
            metadata["/Title"] = title.strip()
        if author.strip():
            metadata["/Author"] = author.strip()
        if metadata:
            writer.add_metadata(metadata)
        if include_cover:
            self._append_raster(writer, self.current_cover_image())
        for data in self.pages:
            if data.kind is PdfItemKind.PDF and data.rotation == 0 and not data.flip_x and data.crop is None:
                self._append_vector(writer, data)
            else:
                self._append_raster(writer, self.render_final_page(data, quality.dpi))
        with output.open("wb") as stream:
            writer.write(stream)
        return output

    def _append_vector(self, writer: PdfWriter, data: PdfPageData) -> None:
        reader = PdfReader(data.path)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PdfImportError("PDF protegido por senha não suportada pelo fluxo original.")
        source = reader.pages[data.page_no or 0]
        box = source.cropbox if source.cropbox is not None else source.mediabox
        width = float(box.width)
        height = float(box.height)
        if width <= 0 or height <= 0:
            raise PdfImportError("Página PDF com dimensões inválidas.")
        page_width = PDF_PAGE_WIDTH_PT
        page_height = page_width * height / width
        target = PageObject.create_blank_page(width=page_width, height=page_height)
        scale = min(page_width / width, page_height / height)
        x = (page_width - width * scale) / 2.0
        y = (page_height - height * scale) / 2.0
        left = float(box.left)
        bottom = float(box.bottom)
        ctm = (scale, 0.0, 0.0, scale, x - left * scale, y - bottom * scale)
        target.merge_transformed_page(source, ctm, over=True, expand=False)
        # PDFBox LayerUtility.importPageAsForm + drawForm incorpora o conteúdo da
        # página, não a árvore de anotações. pypdf copia /Annots no merge, então
        # removemos explicitamente para reproduzir o comportamento do motor ativo.
        target.pop(NameObject("/Annots"), None)
        writer.add_page(target)

    def _append_raster(self, writer: PdfWriter, image: Image.Image) -> None:
        rgb = image.convert("RGB")
        page_width = PDF_PAGE_WIDTH_PT
        page_height = page_width * rgb.height / rgb.width
        page = PageObject.create_blank_page(width=page_width, height=page_height)

        stream = EncodedStreamObject()
        stream._data = zlib.compress(rgb.tobytes())
        stream.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(rgb.width),
            NameObject("/Height"): NumberObject(rgb.height),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/FlateDecode"),
        })
        image_ref = writer._add_object(stream)
        xobjects = DictionaryObject({NameObject("/Im0"): image_ref})
        resources = DictionaryObject({NameObject("/XObject"): xobjects})
        page[NameObject("/Resources")] = resources

        content = EncodedStreamObject()
        commands = f"q\n{page_width:.6f} 0 0 {page_height:.6f} 0 0 cm\n/Im0 Do\nQ\n".encode("ascii")
        content._data = zlib.compress(commands)
        content[NameObject("/Filter")] = NameObject("/FlateDecode")
        page[NameObject("/Contents")] = writer._add_object(content)
        writer.add_page(page)
