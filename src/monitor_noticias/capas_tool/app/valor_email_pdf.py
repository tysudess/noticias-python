from __future__ import annotations

import base64
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import pypdfium2 as pdfium

from .network import get_text_windows
from .config import (
    ACCESS_KEY,
    cache_dir,
    data_dir,
    downloads_dir,
)
from .models import CandidatePage


UA = "PrincipaisCapas-Windows/1.2.7"


def _valid_webapp_url(url: str) -> bool:
    value = (url or "").strip().lower()
    return (
        value.startswith("https://script.google.com/macros/s/")
        and "/exec" in value
    )


def _endpoint(base: str, action: str, target_date: date, page: int = 0) -> str:
    params = {
        "key": ACCESS_KEY,
        "action": action,
        "date": target_date.isoformat(),
    }
    if page > 0:
        params["page"] = str(page)
    return base + ("&" if "?" in base else "?") + urlencode(params)


def _request_json(url: str) -> dict:
    try:
        body = get_text_windows(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/json,text/plain,*/*",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            connect_timeout=7,
            read_timeout=30,
        )
    except Exception as exc:
        raise RuntimeError(f"Ponte Gmail do Valor: {exc}") from exc

    body = (body or "").strip()

    if body.lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("A ponte do Valor abriu HTML em vez de JSON")

    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(
            "Resposta inválida da ponte Gmail para o Valor"
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            "A ponte Gmail do Valor não retornou um objeto JSON"
        )

    return parsed


def _safe_filename(value: str) -> str:
    text = (
        (value or "")
        .replace("\\", "_")
        .replace("/", "_")
        .strip()
    )
    text = re.sub(r"[^A-Za-z0-9._ -]+", "_", text)
    return text or "Valor-Economico.pdf"


def _extract_page_number(item: dict) -> int:
    if not isinstance(item, dict):
        return 0

    raw = (
        item.get("page")
        or item.get("pageNumber")
        or item.get("page_number")
        or item.get("pagina")
        or 0
    )

    try:
        return int(raw)
    except Exception:
        return 0


def _extract_filename(item: dict) -> str:
    if not isinstance(item, dict):
        return "Valor-Economico.pdf"

    return _safe_filename(
        str(
            item.get("filename")
            or item.get("fileName")
            or item.get("name")
            or ""
        )
    )


def _manifest_pages(manifest: dict) -> list[dict]:
    raw = (
        manifest.get("pages")
        or manifest.get("attachments")
        or manifest.get("files")
        or []
    )

    if not isinstance(raw, list):
        return []

    return [item for item in raw if isinstance(item, dict)]


def _fetch_pdf_bytes(
    base: str,
    target_date: date,
    page: int,
) -> tuple[bytes, dict]:
    root = _request_json(
        _endpoint(base, "valor_pdf", target_date, page)
    )

    if not root.get("ok"):
        raise RuntimeError(
            root.get("error")
            or f"PDF Página {page} do Valor não disponível"
        )

    b64 = str(
        root.get("dataBase64")
        or root.get("data_base64")
        or root.get("base64")
        or ""
    )

    if not b64:
        raise RuntimeError(f"PDF Página {page} do Valor veio vazio")

    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception as exc:
        raise RuntimeError(
            f"PDF Página {page} do Valor veio com base64 inválido"
        ) from exc

    if len(raw) < 5 or not raw.startswith(b"%PDF"):
        raise RuntimeError(
            f"Anexo Página {page} do Valor não é um PDF válido"
        )

    return raw, root


def _write_pdf(
    target_date: date,
    filename: str,
    raw: bytes,
) -> tuple[Path, Path]:
    safe = _safe_filename(filename)

    app_dir = data_dir() / "valor-pdfs" / target_date.isoformat()
    app_dir.mkdir(parents=True, exist_ok=True)

    app_pdf = app_dir / safe
    app_pdf.write_bytes(raw)

    download_dir = downloads_dir() / "Valor Economico"
    download_dir.mkdir(parents=True, exist_ok=True)

    download_pdf = download_dir / safe
    download_pdf.write_bytes(raw)

    return app_pdf, download_pdf


def _render_first_page(
    pdf_path: Path,
    target_date: date,
    page_number: int,
) -> Path:
    out = (
        cache_dir()
        / target_date.isoformat()
        / f"valor-email-p{page_number}.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf = None
    page = None
    bitmap = None

    try:
        pdf = pdfium.PdfDocument(str(pdf_path))

        if len(pdf) <= 0:
            raise RuntimeError(
                f"PDF Página {page_number} do Valor sem páginas"
            )

        page = pdf[0]
        width_pt, _ = page.get_size()
        width_pt = max(1.0, float(width_pt))

        scale = max(
            1.0,
            min(
                6.0,
                2400.0 / width_pt,
            ),
        )

        bitmap = page.render(
            scale=scale,
            rotation=0,
        )

        image = bitmap.to_pil()
        image.save(out, format="PNG")

    except Exception as exc:
        raise RuntimeError(
            "Não foi possível renderizar "
            f"a Página {page_number} do Valor: {exc}"
        ) from exc

    finally:
        try:
            if bitmap is not None:
                bitmap.close()
        except Exception:
            pass

        try:
            if page is not None:
                page.close()
        except Exception:
            pass

        try:
            if pdf is not None:
                pdf.close()
        except Exception:
            pass

    if not out.exists() or out.stat().st_size < 8192:
        raise RuntimeError(
            f"Prévia da Página {page_number} do Valor inválida"
        )

    return out


def load_valor_candidates(
    apps_script_url: str,
    target_date: date,
) -> list[CandidatePage]:
    """Carrega exclusivamente do Gmail os PDFs do Valor Econômico.

    V43:
    - Gmail é a fonte obrigatória do Valor;
    - Página 1 é obrigatória;
    - ausência/erro NÃO libera fallback web automático;
    - aceita pequenas variações no JSON da ponte Apps Script.
    """

    base = (apps_script_url or "").strip()

    if not _valid_webapp_url(base):
        raise RuntimeError(
            "Apps Script do Gmail não está configurado "
            "com uma URL /exec válida."
        )

    manifest = _request_json(
        _endpoint(
            base,
            "valor_manifest",
            target_date,
        )
    )

    if not manifest.get("ok"):
        raise RuntimeError(
            manifest.get("error")
            or "Falha ao consultar os PDFs do Valor no Gmail"
        )

    page_items = _manifest_pages(manifest)

    if not page_items:
        raise RuntimeError(
            "O Gmail não retornou anexos do Valor "
            "para a data selecionada."
        )

    metas: list[tuple[int, str]] = []
    seen_pages: set[int] = set()

    for item in page_items:
        page_number = _extract_page_number(item)

        if (
            page_number < 1
            or page_number > 3
            or page_number in seen_pages
        ):
            continue

        seen_pages.add(page_number)

        metas.append(
            (
                page_number,
                _extract_filename(item),
            )
        )

    metas.sort(key=lambda item: item[0])

    if not any(page_number == 1 for page_number, _ in metas):
        available = (
            ", ".join(str(page_number) for page_number, _ in metas)
            or "nenhuma"
        )

        raise RuntimeError(
            "O Gmail respondeu, mas a Página 1 "
            "do Valor não foi encontrada. "
            f"Páginas informadas: {available}."
        )

    candidates: list[CandidatePage] = []

    for page_number, filename in metas:
        candidate = CandidatePage(
            path=None,
            score=100,
            confidence=100,
            recognized_text=(
                "VALOR ECONÔMICO — PDF recebido por e-mail — "
                f"Página {page_number}"
            ),
            source_url=(
                "gmail-pdf://valor/"
                f"{target_date.isoformat()}/pagina-{page_number}"
            ),
            page_number=page_number,
            available=False,
            error="",
            pdf_path=None,
            source_filename=filename,
        )

        try:
            raw, root = _fetch_pdf_bytes(
                base,
                target_date,
                page_number,
            )

            server_name = _safe_filename(
                str(
                    root.get("filename")
                    or root.get("fileName")
                    or filename
                )
            )

            app_pdf, _ = _write_pdf(
                target_date,
                server_name,
                raw,
            )

            candidate.path = _render_first_page(
                app_pdf,
                target_date,
                page_number,
            )

            candidate.pdf_path = app_pdf
            candidate.source_filename = server_name
            candidate.available = True

        except Exception as exc:
            candidate.available = False
            candidate.error = str(exc)

            if page_number == 1:
                raise RuntimeError(
                    "A Página 1 do Valor foi localizada "
                    "no Gmail, mas não pôde ser aberta: "
                    f"{exc}"
                ) from exc

        candidates.append(candidate)

    candidates.sort(
        key=lambda candidate: candidate.page_number
    )

    return candidates
