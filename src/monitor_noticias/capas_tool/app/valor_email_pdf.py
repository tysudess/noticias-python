from __future__ import annotations

import base64
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import fitz
from .network import get_text_windows

from .config import ACCESS_KEY, cache_dir, data_dir, downloads_dir
from .models import CandidatePage

UA = "PrincipaisCapas-Windows/1.2.6"


def _valid_webapp_url(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith("https://script.google.com/macros/s/") and "/exec" in u


def _endpoint(base: str, action: str, target_date: date, page: int = 0) -> str:
    params = {"key": ACCESS_KEY, "action": action, "date": target_date.isoformat()}
    if page > 0:
        params["page"] = str(page)
    return base + ("&" if "?" in base else "?") + urlencode(params)


def _request_json(url: str) -> dict:
    try:
        body = get_text_windows(
            url,
            headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*"},
            connect_timeout=5,
            read_timeout=22,
        )
    except Exception as exc:
        raise RuntimeError(f"Ponte Gmail do Valor: {exc}") from exc
    body = (body or "").strip()
    if body.lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("A ponte do Valor abriu HTML em vez de JSON")
    try:
        return json.loads(body)
    except Exception as exc:
        raise RuntimeError("Resposta inválida da ponte Gmail para o Valor") from exc


def _safe_filename(value: str) -> str:
    s = (value or "").replace("\\", "_").replace("/", "_").strip()
    s = re.sub(r"[^A-Za-z0-9._ -]+", "_", s)
    return s or "Valor-Economico.pdf"


def _fetch_pdf_bytes(base: str, target_date: date, page: int) -> tuple[bytes, dict]:
    root = _request_json(_endpoint(base, "valor_pdf", target_date, page))
    if not root.get("ok"):
        raise RuntimeError(root.get("error") or f"PDF Página {page} do Valor não disponível")
    b64 = str(root.get("dataBase64") or "")
    if not b64:
        raise RuntimeError(f"PDF Página {page} do Valor veio vazio")
    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception as exc:
        raise RuntimeError(f"PDF Página {page} do Valor veio com base64 inválido") from exc
    if len(raw) < 5 or not raw.startswith(b"%PDF"):
        raise RuntimeError(f"Anexo Página {page} do Valor não é um PDF válido")
    return raw, root


def _write_pdf(target_date: date, filename: str, raw: bytes) -> tuple[Path, Path]:
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


def _render_first_page(pdf_path: Path, target_date: date, page_number: int) -> Path:
    out = cache_dir() / target_date.isoformat() / f"valor-email-p{page_number}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count <= 0:
            raise RuntimeError(f"PDF Página {page_number} do Valor sem páginas")
        page = doc.load_page(0)
        width_pt = max(1.0, float(page.rect.width))
        zoom = max(1.0, min(6.0, 2400.0 / width_pt))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pix.save(str(out))
        doc.close()
    except Exception as exc:
        raise RuntimeError(f"Não foi possível renderizar a Página {page_number} do Valor: {exc}") from exc
    if not out.exists() or out.stat().st_size < 8192:
        raise RuntimeError(f"Prévia da Página {page_number} do Valor inválida")
    return out


def load_valor_candidates(apps_script_url: str, target_date: date) -> list[CandidatePage]:
    """Port Windows do ValorEmailPdfClient Android v0.7.7.5.

    Página 1 é obrigatória. Páginas 1/2/3 ficam no app e em Downloads; se a
    Página 1 não estiver disponível, o chamador usa o fallback web da v1.2.2.
    """
    base = (apps_script_url or "").strip()
    if not _valid_webapp_url(base):
        return []

    manifest = _request_json(_endpoint(base, "valor_manifest", target_date))
    if not manifest.get("ok"):
        raise RuntimeError(manifest.get("error") or "Falha ao consultar PDFs do Valor no Gmail")
    if "pages" not in manifest:
        return []

    metas = []
    for item in manifest.get("pages") or []:
        try:
            pn = int(item.get("page") or 0)
        except Exception:
            pn = 0
        if pn < 1 or pn > 3:
            continue
        metas.append((pn, _safe_filename(str(item.get("filename") or ""))))
    metas.sort(key=lambda x: x[0])
    if not any(pn == 1 for pn, _ in metas):
        return []

    candidates: list[CandidatePage] = []
    for pn, filename in metas:
        c = CandidatePage(
            path=None,
            score=100,
            confidence=100,
            recognized_text=f"VALOR ECONÔMICO — PDF recebido por e-mail — Página {pn}",
            source_url=f"gmail-pdf://valor/{target_date.isoformat()}/pagina-{pn}",
            page_number=pn,
            available=False,
            error="",
            pdf_path=None,
            source_filename=filename,
        )
        try:
            raw, root = _fetch_pdf_bytes(base, target_date, pn)
            server_name = _safe_filename(str(root.get("filename") or filename))
            app_pdf, _ = _write_pdf(target_date, server_name, raw)
            c.path = _render_first_page(app_pdf, target_date, pn)
            c.pdf_path = app_pdf
            c.source_filename = server_name
            c.available = True
        except Exception as exc:
            c.available = False
            c.error = str(exc)
            if pn == 1:
                raise
        candidates.append(c)

    candidates.sort(key=lambda c: c.page_number)
    return candidates
