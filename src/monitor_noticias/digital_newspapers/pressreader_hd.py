from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
import re
import shutil
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import zlib

from PIL import Image
import requests
from PySide6.QtCore import QThread, Signal

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.digital_newspapers.providers import DigitalNewspaperProvider
from monitor_noticias.digital_newspapers.storage import SecureSessionStore
from monitor_noticias.networking.proxy import ProxySettings


PRESSREADER_HIGH_SCALES: tuple[int, ...] = (
    416,
    390,
    364,
    338,
    312,
    286,
    260,
    234,
    208,
    182,
    156,
    130,
    104,
)
PRESSREADER_HIGH_WIDTHS: tuple[int, ...] = (
    3200,
    3000,
    2800,
    2600,
    2400,
    2200,
    2000,
    1800,
    1600,
)


@dataclass(frozen=True, slots=True)
class DownloadedPageImage:
    page_number: int
    path: Path
    width: int
    height: int
    image_format: str


def pressreader_image_page_number(raw_url: str) -> int | None:
    """Retorna o número da página codificado em uma URL de imagem PressReader."""

    try:
        parsed = urlsplit(str(raw_url or "").strip())
        host = str(parsed.hostname or "").lower()
        path = str(parsed.path or "")
        if not host.endswith("prcdn.co") or "/img" not in path:
            return None
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        page_text = str(query.get("page") or "").strip()
        file_text = str(query.get("file") or "").strip()
        if not page_text or not file_text:
            return None
        page_number = int(page_text)
        return page_number if page_number > 0 else None
    except Exception:
        return None


def pressreader_total_pages_from_text(text: str) -> int | None:
    """Extrai o total mostrado pelo viewer, por exemplo ``35 de 38`` ou ``35 of 38``."""

    value = str(text or "")
    patterns = (
        r"\b\d{1,3}\s+(?:de|of)\s+(\d{1,3})\b",
        r"\b(?:page|pagina|página)\s+\d{1,3}\s+(?:de|of)\s+(\d{1,3})\b",
    )
    totals: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, value, flags=re.IGNORECASE):
            try:
                total = int(match.group(1))
            except Exception:
                continue
            if 1 <= total <= 500:
                totals.append(total)
    return max(totals) if totals else None


def pressreader_image_candidate_score(
    raw_url: str,
    *,
    expected_page: int | None = None,
) -> int | None:
    """Pontua somente imagens de página do CDN do PressReader.

    A regra replica o que já havia sido validado no APK Extrator Valor:
    host `*.prcdn.co`, caminho contendo `/img`, parâmetros `page` e `file`,
    com preferência por `i.prcdn.co` e pelos maiores `scale`/`width`.
    """

    try:
        parsed = urlsplit(str(raw_url or "").strip())
    except Exception:
        return None

    host = str(parsed.hostname or "").lower()
    path = str(parsed.path or "")
    if not host.endswith("prcdn.co") or "/img" not in path:
        return None

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    page_number = pressreader_image_page_number(raw_url)
    if page_number is None:
        return None

    if expected_page is not None and page_number != int(expected_page):
        return None

    def _safe_int(value: object) -> int:
        try:
            return int(str(value or "0"))
        except Exception:
            return 0

    score = 1_000_000 if host.startswith("i.") else 10_000
    score += _safe_int(query.get("scale")) * 100
    score += _safe_int(query.get("width"))
    return score


def pressreader_image_variants(raw_url: str) -> tuple[str, ...]:
    """Gera as mesmas tentativas HD usadas no APK, preservando os demais parâmetros."""

    value = str(raw_url or "").strip()
    if not value:
        return ()

    try:
        parsed = urlsplit(value)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except Exception:
        return (value,)

    fixed = [
        (name, item)
        for name, item in pairs
        if name.lower() not in {"scale", "width"}
    ]

    candidates: list[str] = []
    seen: set[str] = set()

    def _add(extra_name: str | None, extra_value: int | None) -> None:
        query = list(fixed)
        if extra_name is not None and extra_value is not None:
            query.append((extra_name, str(extra_value)))
        url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query, doseq=True),
                parsed.fragment,
            )
        )
        if url not in seen:
            seen.add(url)
            candidates.append(url)

    for scale in PRESSREADER_HIGH_SCALES:
        _add("scale", scale)
    for width in PRESSREADER_HIGH_WIDTHS:
        _add("width", width)

    if value not in seen:
        candidates.append(value)
    return tuple(candidates)


def _pdf_number(value: float) -> str:
    if abs(value - round(value)) < 0.00001:
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _prepare_pdf_image(path: Path) -> tuple[bytes, int, int, str, str]:
    raw = path.read_bytes()
    with Image.open(BytesIO(raw)) as image:
        image.load()
        width = int(image.width)
        height = int(image.height)
        fmt = str(image.format or "").upper()
        mode = str(image.mode or "")

        if fmt in {"JPEG", "JPG"} and raw.startswith(b"\xff\xd8\xff"):
            if mode == "L":
                color_space = "/DeviceGray"
            elif mode == "CMYK":
                color_space = "/DeviceCMYK"
            else:
                color_space = "/DeviceRGB"
            return raw, width, height, "/DCTDecode", color_space

        if "A" in mode:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            rgb = background
        else:
            rgb = image.convert("RGB")

        # Para PNG/WebP/outros formatos, preserva todos os pixels sem compressão
        # com perdas. O stream RGB é comprimido com Flate (zlib) dentro do PDF.
        payload = zlib.compress(rgb.tobytes(), level=6)
        return payload, width, height, "/FlateDecode", "/DeviceRGB"


def build_image_pdf_without_pixel_loss(
    image_paths: list[Path],
    output_path: Path,
) -> int:
    """Monta PDF de páginas-image sem reduzir pixels.

    JPEG entra por passthrough DCT, sem recompressão. Outros formatos são
    decodificados e armazenados em RGB + Flate, preservando pixel a pixel.
    Todas as páginas recebem a mesma largura física (612 pt) e altura proporcional.
    """

    if not image_paths:
        raise RuntimeError("Nenhuma página de imagem foi recebida para montar o PDF.")

    page_width_pt = 612.0
    prepared: list[tuple[bytes, int, int, str, str]] = []
    for path in image_paths:
        prepared.append(_prepare_pdf_image(path))

    page_object_numbers = [3 + index * 3 for index in range(len(prepared))]
    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {len(prepared)} /Kids [{kids}] >>"
        ).encode("ascii"),
    }

    for index, (payload, width, height, pdf_filter, color_space) in enumerate(prepared):
        page_obj = 3 + index * 3
        image_obj = page_obj + 1
        content_obj = page_obj + 2
        page_height_pt = page_width_pt * (float(height) / float(width))

        page_dict = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {_pdf_number(page_width_pt)} {_pdf_number(page_height_pt)}] "
            f"/Resources << /XObject << /Im0 {image_obj} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        ).encode("ascii")
        objects[page_obj] = page_dict

        image_header = (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
            f"/ColorSpace {color_space} /BitsPerComponent 8 /Filter {pdf_filter} "
            f"/Length {len(payload)} >>\nstream\n"
        ).encode("ascii")
        objects[image_obj] = image_header + payload + b"\nendstream"

        content = (
            "q\n"
            f"{_pdf_number(page_width_pt)} 0 0 {_pdf_number(page_height_pt)} 0 0 cm\n"
            "/Im0 Do\n"
            "Q\n"
        ).encode("ascii")
        objects[content_obj] = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"endstream"
        )

    max_obj = max(objects)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    part = output_path.with_suffix(output_path.suffix + ".part")

    offsets = [0] * (max_obj + 1)
    with part.open("wb") as handle:
        handle.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for number in range(1, max_obj + 1):
            offsets[number] = handle.tell()
            handle.write(f"{number} 0 obj\n".encode("ascii"))
            handle.write(objects[number])
            handle.write(b"\nendobj\n")

        xref_offset = handle.tell()
        handle.write(f"xref\n0 {max_obj + 1}\n".encode("ascii"))
        handle.write(b"0000000000 65535 f \n")
        for number in range(1, max_obj + 1):
            handle.write(f"{offsets[number]:010d} 00000 n \n".encode("ascii"))
        handle.write(
            (
                f"trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )

    try:
        output_path.unlink()
    except FileNotFoundError:
        pass
    part.replace(output_path)
    return len(image_paths)


class PressReaderHdPdfThread(QThread):
    """Baixa páginas HD autorizadas do PressReader e monta um único PDF."""

    status_changed = Signal(str)
    completed = Signal(str, int, str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        paths: AppPaths,
        provider: DigitalNewspaperProvider,
        target_date: date,
        page_urls: dict[int, object],
        output_path: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.provider = provider
        self.target_date = target_date
        normalized: dict[int, tuple[str, ...]] = {}
        for raw_page, raw_urls in dict(page_urls).items():
            page_number = int(raw_page)
            if isinstance(raw_urls, str):
                values = [raw_urls]
            else:
                try:
                    values = list(raw_urls)
                except Exception:
                    values = [str(raw_urls or "")]
            seen: set[str] = set()
            clean: list[str] = []
            for raw in values:
                value = str(raw or "").strip()
                if value and value not in seen:
                    seen.add(value)
                    clean.append(value)
            if clean:
                normalized[page_number] = tuple(clean)
        self.page_urls = normalized
        self.output_path = Path(output_path)

    def _proxy_settings(self) -> tuple[ProxySettings, object]:
        prefs = SharedPreferences(
            self.paths.data / "prefs" / "monitor_prefs.properties"
        )
        settings = ProxySettings(prefs, data_dir=self.paths.data)
        return settings, settings.load()

    def _restore_requests_cookies(self, session: requests.Session) -> None:
        vault = SecureSessionStore(self.paths, self.provider.id)
        rows = vault.load_json(default=[])
        if not isinstance(rows, list):
            return

        for item in rows:
            if not isinstance(item, dict):
                continue
            try:
                name = str(item.get("name") or "")
                domain = str(item.get("domain") or "").lstrip(".")
                cookie_path = str(item.get("path") or "/")
                if not name or not self.provider.domain_allowed(domain):
                    continue
                value = base64.b64decode(
                    str(item.get("value") or ""), validate=False
                ).decode("utf-8", "ignore")
                session.cookies.set(name, value, domain=domain, path=cookie_path)
            except Exception:
                continue

    def _headers(self, page_number: int) -> dict[str, str]:
        referer = self.provider.pressreader_page_url(self.target_date, page_number)
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/151 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": referer or self.provider.edition_url,
            "Cache-Control": "no-cache",
        }

    def _download_best_image(
        self,
        session: requests.Session,
        raw_urls: tuple[str, ...] | list[str],
        *,
        page_number: int,
        proxies,
        verify,
    ) -> tuple[bytes, int, int, str]:
        first_error: Exception | None = None
        best: tuple[bytes, int, int, str] | None = None
        best_pixels = 0

        tried_candidates: set[str] = set()
        for raw_url in raw_urls:
            per_source_best: tuple[bytes, int, int, str] | None = None
            per_source_pixels = 0
            for candidate in pressreader_image_variants(raw_url):
                if candidate in tried_candidates:
                    continue
                tried_candidates.add(candidate)
                if self.isInterruptionRequested():
                    raise RuntimeError("Download cancelado.")
                try:
                    response = session.get(
                        candidate,
                        headers=self._headers(page_number),
                        allow_redirects=True,
                        timeout=(15, 75),
                        proxies=proxies,
                        verify=verify,
                    )
                    if response.status_code < 200 or response.status_code >= 300:
                        response.close()
                        continue
                    payload = response.content
                    response.close()
                    if not payload:
                        continue

                    with Image.open(BytesIO(payload)) as image:
                        width = int(image.width)
                        height = int(image.height)
                        fmt = str(image.format or "").upper()

                    pixels = width * height
                    if pixels > per_source_pixels:
                        per_source_best = (payload, width, height, fmt)
                        per_source_pixels = pixels
                    if pixels > best_pixels:
                        best = (payload, width, height, fmt)
                        best_pixels = pixels

                    # Se este arquivo de página realmente entrega a resolução-alvo,
                    # não há motivo para testar tamanhos menores do mesmo arquivo.
                    if width >= int(self.provider.pressreader_target_width):
                        return payload, width, height, fmt
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
                    continue

            # O URL de maior score pode ser apenas thumbnail/preview. Se ele não
            # atingir a qualidade mínima, continua no próximo `file=` capturado
            # para a MESMA página antes de declarar falha.
            if (
                per_source_best is not None
                and per_source_best[1] >= int(self.provider.pressreader_min_width)
            ):
                return per_source_best

        if best is not None and best[1] >= int(self.provider.pressreader_min_width):
            return best

        detail = "nenhuma imagem válida"
        if best is not None:
            detail = f"{best[1]}x{best[2]} px"
        suffix = f" ({first_error})" if first_error is not None else ""
        raise RuntimeError(
            f"Página {page_number}: qualidade insuficiente - {detail}; mínimo "
            f"{self.provider.pressreader_min_width}px de largura{suffix}."
        )

    def run(self) -> None:
        expected_pages = sorted(self.page_urls)
        if not expected_pages:
            self.failed.emit("Nenhuma página HD foi localizada no PressReader.")
            return
        if expected_pages != list(range(1, expected_pages[-1] + 1)):
            self.failed.emit("A sequência de páginas do PressReader veio incompleta.")
            return
        if len(expected_pages) < int(self.provider.min_edition_pages):
            self.failed.emit(
                f"Foram localizadas apenas {len(expected_pages)} páginas; a edição "
                f"completa exige pelo menos {self.provider.min_edition_pages}."
            )
            return

        pages_dir = self.output_path.parent / "paginas_hd"
        # V86: não apaga imagens já baixadas de uma tentativa anterior. Cada
        # página válida é substituída apenas quando uma nova versão HD é obtida.
        pages_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []

        try:
            settings, config = self._proxy_settings()
            proxies = settings.requests_proxies(config)
            verify = settings.requests_verify(config)

            with requests.Session() as session:
                session.trust_env = False
                self._restore_requests_cookies(session)

                total = len(expected_pages)
                for index, page_number in enumerate(expected_pages, start=1):
                    self.status_changed.emit(
                        f"{self.provider.name}: baixando página {page_number:02d}/{total:02d} em HD…"
                    )
                    payload, width, height, fmt = self._download_best_image(
                        session,
                        self.page_urls[page_number],
                        page_number=page_number,
                        proxies=proxies,
                        verify=verify,
                    )
                    suffix = {
                        "JPEG": ".jpg",
                        "JPG": ".jpg",
                        "PNG": ".png",
                        "WEBP": ".webp",
                        "AVIF": ".avif",
                        "TIFF": ".tif",
                    }.get(fmt, ".img")
                    image_path = pages_dir / f"pagina-{page_number:03d}{suffix}"
                    image_path.write_bytes(payload)
                    downloaded.append(image_path)
                    self.status_changed.emit(
                        f"{self.provider.name}: página {page_number:02d} salva separadamente "
                        f"em {width}x{height}px."
                    )

            self.status_changed.emit(
                f"{self.provider.name}: montando PDF único com {len(downloaded)} páginas HD…"
            )
            pages = build_image_pdf_without_pixel_loss(downloaded, self.output_path)

            from pypdf import PdfReader

            verified_pages = len(PdfReader(str(self.output_path)).pages)
            if verified_pages != pages:
                raise RuntimeError(
                    f"PDF final inconsistente: esperado {pages} páginas, recebido {verified_pages}."
                )
            if self.output_path.stat().st_size < int(self.provider.min_edition_bytes):
                raise RuntimeError(
                    "O PDF final ficou pequeno demais para representar a edição completa."
                )

            self.completed.emit(
                str(self.output_path),
                pages,
                "PressReader - imagens HD + PDF",
            )
        except Exception as exc:
            try:
                self.output_path.unlink()
            except Exception:
                pass
            detail = str(exc) or exc.__class__.__name__
            if downloaded:
                detail += (
                    f" As {len(downloaded)} imagem(ns) já baixadas foram preservadas em "
                    f"{pages_dir}."
                )
            self.failed.emit(detail)
