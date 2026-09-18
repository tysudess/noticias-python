import csv
import io
import os
import re
import subprocess
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from PIL import Image
from .config import bundle_dir

AD_WORDS = (
    "PUBLICIDADE", "INFORME PUBLICITARIO", "CONTEUDO PUBLICITARIO",
    "ADVERTISEMENT", "ADVERTORIAL", "PAID CONTENT", "SPONSORED CONTENT",
)


def normalize(text: str) -> str:
    s = unicodedata.normalize("NFD", text or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def _tesseract_exe() -> Path | None:
    candidates = [
        bundle_dir() / "tesseract" / "tesseract.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _run_tesseract_tsv(path: Path):
    """Retorna (texto bruto, linhas com bbox, largura, altura).

    É a equivalência desktop do ML Kit usado por ClippingImageScanner.java:
    precisamos de texto + posição de cada linha para pontuar masthead no topo.
    """
    exe = _tesseract_exe()
    if not exe:
        return "", [], 0, 0

    im = Image.open(path).convert("RGB")
    # Android analisa preview de ~1200px; mantemos a mesma escala.
    if im.width > 1200:
        nh = max(1, round(im.height * (1200 / im.width)))
        im = im.resize((1200, nh), Image.Resampling.LANCZOS)
    w, h = im.size

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "page.png"
        im.save(p, "PNG")
        cmd = [str(exe), str(p), "stdout", "-l", "por+eng", "--psm", "3", "tsv"]
        cp = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=35,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        tsv = cp.stdout or ""

    groups = {}
    try:
        reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
        for r in reader:
            txt = (r.get("text") or "").strip()
            if not txt:
                continue
            try:
                conf = float(r.get("conf") or -1)
            except Exception:
                conf = -1
            if conf < 0:
                continue
            key = (r.get("block_num"), r.get("par_num"), r.get("line_num"))
            try:
                left = int(r.get("left") or 0); top = int(r.get("top") or 0)
                width = int(r.get("width") or 0); height = int(r.get("height") or 0)
            except Exception:
                continue
            g = groups.setdefault(key, {"words": [], "left": left, "top": top, "right": left+width, "bottom": top+height})
            g["words"].append(txt)
            g["left"] = min(g["left"], left); g["top"] = min(g["top"], top)
            g["right"] = max(g["right"], left+width); g["bottom"] = max(g["bottom"], top+height)
    except Exception:
        groups = {}

    lines = []
    for g in groups.values():
        text = " ".join(g["words"]).strip()
        if not text:
            continue
        lines.append({
            "text": text,
            "left": g["left"], "top": g["top"],
            "width": max(1, g["right"]-g["left"]),
            "height": max(1, g["bottom"]-g["top"]),
        })
    lines.sort(key=lambda x: (x["top"], x["left"]))
    raw = "\n".join(x["text"] for x in lines)
    return raw, lines, w, h


def is_strong_nyt_masthead(text: str) -> bool:
    t = normalize(text)
    if "ALL THE NEWS THAT S FIT TO PRINT" in t or "ALL THE NEWS THAT IS FIT TO PRINT" in t:
        return True
    if "THE NEW YORK TIMES" not in t:
        return False
    if "THE NEW YORK TIMES COMPANY" in t and not re.search(
        r"THE NEW YORK TIMES (MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)", t
    ):
        return False
    return True


def matches_expected(text: str, name: str) -> bool:
    t = normalize(text)
    expected = normalize(name)
    if expected == "O GLOBO":
        return "O GLOBO" in t or ("GLOBO" in t and "IRINEU MARINHO" in t)
    if "FOLHA" in expected:
        return "FOLHA" in t and ("PAULO" in t or "S PAULO" in t)
    if "ESTADAO" in expected:
        # "FUNDADO EM 1875" sozinho não identifica a capa: a frase também
        # aparece no cabeçalho de páginas internas. Exigimos o nome do jornal.
        return (
            "ESTADAO" in t
            or ("ESTADO" in t and "S PAULO" in t)
            or ("ESTADO" in t and "SAO PAULO" in t)
        )
    if "CORREIO BRAZILIENSE" in expected:
        return "CORREIO" in t and "BRAZILIENSE" in t
    if "ESTADO DE MINAS" in expected:
        return "ESTADO" in t and "MINAS" in t
    if "NEW YORK TIMES" in expected:
        return is_strong_nyt_masthead(t)
    if "WASHINGTON POST" in expected:
        return "WASHINGTON" in t and "POST" in t and "WASHINGTON POST SPORTS" not in t
    if "VALOR ECONOMICO" in expected:
        return "VALOR" in t
    return bool(expected and expected in t)


def matches_cover_profile_top(top20: str, top35: str, name: str) -> bool:
    t20 = normalize(top20); t35 = normalize(top35); n = normalize(name)
    if n == "O GLOBO": return "O GLOBO" in t20 or ("GLOBO" in t20 and "IRINEU MARINHO" in t35)
    if "FOLHA" in n: return "FOLHA DE S PAULO" in t20 or "FOLHA DE SAO PAULO" in t20 or ("FOLHA" in t20 and "PAULO" in t20)
    if "ESTADAO" in n: return contains_exact_estadao_masthead(t35)
    if "CORREIO BRAZILIENSE" in n: return "CORREIO BRAZILIENSE" in t20 or ("CORREIO" in t20 and "BRAZILIENSE" in t20)
    if "ESTADO DE MINAS" in n: return "ESTADO DE MINAS" in t20 or ("ESTADO" in t20 and "MINAS" in t20)
    if "NEW YORK TIMES" in n: return is_strong_nyt_masthead(t20)
    return matches_expected(t20, name)

def contains_exact_estadao_masthead(text: str) -> bool:
    t = normalize(text)
    return (
        "O ESTADO DE S PAULO" in t
        or "O ESTADO DE SAO PAULO" in t
        or "ESTADAO" in t
    )


def is_internal_page_header_line(text: str) -> bool:
    t = normalize(text).strip()
    if not t:
        return False
    # Marcadores típicos de páginas/seções internas: A2, A3, A12, B4 etc.
    return re.match(r"^(A|B|C|D)\s?\d{1,2}(\s.*)?$", t) is not None


def _contains_ad(text: str) -> bool:
    t = normalize(text)
    return any(x in t for x in AD_WORDS)


def _detect_other(text: str, expected_name: str) -> str:
    t, expected = normalize(text), normalize(expected_name)
    if "O GLOBO" in t and expected != "O GLOBO": return "O GLOBO"
    if "FOLHA" in t and "PAULO" in t and "FOLHA" not in expected: return "FOLHA DE SÃO PAULO"
    if "CORREIO" in t and "BRAZILIENSE" in t and "CORREIO BRAZILIENSE" not in expected: return "CORREIO BRAZILIENSE"
    if "ESTADO" in t and "MINAS" in t and "ESTADO DE MINAS" not in expected: return "ESTADO DE MINAS"
    if (("ESTADO" in t and "PAULO" in t) or "ESTADAO" in t) and "ESTADAO" not in expected: return "ESTADÃO"
    if "NEW YORK" in t and "TIMES" in t and "NEW YORK TIMES" not in expected: return "THE NEW YORK TIMES"
    return ""


def _date_matches(text: str, target_date: date | None) -> bool:
    if not target_date:
        return False
    t = normalize(text)
    day, year = str(target_date.day), str(target_date.year)
    months_pt = ["", "JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
    months_en = ["", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
    padded = " " + t + " "
    has_day = re.search(rf"(?:^| )0?{re.escape(day)}(?: |$)", padded) is not None
    return has_day and year in t and (months_pt[target_date.month] in t or months_en[target_date.month] in t)


def score_candidate(path: Path, name: str, mastheads: list[str], target_date: date | None = None) -> tuple[int, int, str]:
    """Port fiel de ClippingImageScanner.scoreCandidate (Android v0.7.6.2)."""
    try:
        with Image.open(path) as orig:
            ow, oh = orig.size
        if ow < 700 or oh < 950 or oh / max(1, ow) < 1.12:
            return 0, 0, ""
        raw, lines, w, h = _run_tesseract_tsv(path)
    except Exception:
        return 0, 0, ""

    full = normalize(raw)
    top20 = []; top35 = []; top50 = []
    masthead_strength = 0
    internal_page_marker_top = False
    h = max(1, h); w = max(1, w)

    for line in lines:
        line_text = normalize(line["text"])
        center_y = (line["top"] + line["height"] / 2) / h
        if center_y <= 0.20: top20.append(line_text)
        if center_y <= 0.35: top35.append(line_text)
        if center_y <= 0.50: top50.append(line_text)
        if center_y <= 0.20 and is_internal_page_header_line(line_text):
            internal_page_marker_top = True
        if matches_expected(line_text, name) and center_y <= 0.32:
            height_frac = line["height"] / h
            width_frac = line["width"] / w
            strength = 1
            if height_frac >= 0.018 or width_frac >= 0.24: strength = 2
            if height_frac >= 0.030 or width_frac >= 0.40: strength = 3
            if height_frac >= 0.045 or width_frac >= 0.55: strength = 4
            masthead_strength = max(masthead_strength, strength)

    t20 = normalize(" ".join(top20)); t35 = normalize(" ".join(top35)); t50 = normalize(" ".join(top50))
    expected20 = matches_expected(t20, name)
    expected35 = matches_expected(t35, name)
    expected50 = matches_expected(t50, name)
    expected_full = matches_expected(full, name)
    if expected20 and masthead_strength == 0:
        masthead_strength = 1

    score = 8
    if masthead_strength >= 4: score += 72
    elif masthead_strength == 3: score += 64
    elif masthead_strength == 2: score += 54
    elif expected20: score += 42
    elif expected35: score += 32
    elif expected50: score += 22
    elif expected_full: score += 10

    line_count = len(lines)
    if line_count >= 24: score += 10
    elif line_count >= 14: score += 7
    elif line_count >= 8: score += 3
    elif line_count <= 3: score -= 8

    if _date_matches(full, target_date): score += 8
    other = _detect_other(t35, name)
    if other: score -= 70
    ad = _contains_ad(full)
    if ad: score -= 10 if expected20 else 35

    # v1.2.5 / Android v0.7.7.6 — perfil de capa; nunca elimina candidata.
    profile_date = _date_matches(full, target_date)
    profile_exact_top = matches_cover_profile_top(t20, t35, name)
    profile_strong_top = masthead_strength >= 3 or (profile_exact_top and masthead_strength >= 2)
    profile_medium_top = masthead_strength >= 2 or expected20 or profile_exact_top
    profile_estadao = "ESTADAO" in normalize(name)
    if profile_exact_top: score += 10
    if profile_strong_top: score += 8
    if profile_strong_top and profile_date: score += 12
    if internal_page_marker_top and not profile_estadao and not profile_strong_top:
        score -= 28; score = min(score, 48)
    if not profile_medium_top and expected_full: score = min(score, 62)

    # v1.1.4 / Android v0.7.6.2 — ESTADÃO:
    # A decisão é feita pela imagem final. Uma chamada de capa pode conter
    # A2/A3/A12/B4 etc. apenas indicando a página da matéria; não penalizamos
    # esses marcadores. "FUNDADO EM 1875" sozinho segue insuficiente.
    estadao = "ESTADAO" in normalize(name)
    if estadao:
        exact_estadao_top = contains_exact_estadao_masthead(t35)
        target_date_present = _date_matches(full, target_date)
        founder_only = "FUNDADO EM 1875" in full and not exact_estadao_top

        if exact_estadao_top and target_date_present:
            score += 28
        elif exact_estadao_top:
            score += 14

        if founder_only:
            score = min(score, 62)
        # Não penalizar A2/A3/A12/B4 no Estadão: pode ser uma chamada da capa.

    nyt = "NEW YORK TIMES" in normalize(name)
    nyt_company_only = nyt and "THE NEW YORK TIMES COMPANY" in full and not is_strong_nyt_masthead(t20)
    if nyt_company_only:
        score -= 45
        score = min(score, 35)

    if profile_exact_top and profile_strong_top and profile_date and not other and not ad and line_count >= 8:
        score = max(score, 92)
    elif profile_exact_top and profile_strong_top and not other and not ad:
        score = max(score, 84)

    if not expected_full: score = min(score, 55)
    if other: score = min(score, 20)
    if ad and not expected20: score = min(score, 35)
    score = max(0, min(100, score))
    return score, score, raw


def read_top(path: Path) -> str:
    """Compatibilidade: OCR do topo usado para rejeitar WaPo SPORTS."""
    try:
        raw, lines, _w, h = _run_tesseract_tsv(path)
        if not lines or h <= 0:
            return raw
        return "\n".join(x["text"] for x in lines if (x["top"] + x["height"] / 2) / h <= 0.34)
    except Exception:
        return ""
