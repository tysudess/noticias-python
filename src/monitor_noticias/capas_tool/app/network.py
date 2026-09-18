import re
import json
import os
import subprocess
import requests

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from .config import ACCESS_KEY

ANDROID_FEED_UA = "PrincipaisCapas/0.7.0 Android"
IMAGE_UA = "Mozilla/5.0 (Android) PrincipaisCapas/0.7.5.0"


def _valid_webapp_url(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith("https://script.google.com/macros/s/") and "/exec" in u


def _powershell_get_text(url: str, headers: dict | None = None, timeout_sec: int = 22) -> str:
    """Fallback Windows nativo: usa WinHTTP/.NET, certificado e proxy do Windows."""
    if os.name != "nt":
        raise RuntimeError("PowerShell disponível apenas no Windows")
    env = os.environ.copy()
    env["PC_HTTP_URL"] = url
    env["PC_HTTP_UA"] = str((headers or {}).get("User-Agent") or ANDROID_FEED_UA)
    script = (
        "$ProgressPreference='SilentlyContinue';"
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$h=@{'User-Agent'=$env:PC_HTTP_UA;'Accept'='application/json,text/plain,*/*'};"
        f"$r=Invoke-WebRequest -UseBasicParsing -Uri $env:PC_HTTP_URL -TimeoutSec {int(timeout_sec)} -Headers $h;"
        "[Console]::Out.Write($r.Content)"
    )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cp = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout_sec + 8,
        creationflags=flags,
    )
    if cp.returncode != 0:
        err = (cp.stderr or cp.stdout or "falha no PowerShell").strip().replace("\r", " ").replace("\n", " ")
        raise RuntimeError(err[:280])
    body = (cp.stdout or "").strip()
    if not body:
        raise RuntimeError("PowerShell retornou resposta vazia")
    return body


def get_text_windows(url: str, headers: dict | None = None, connect_timeout: int = 5, read_timeout: int = 18) -> str:
    """Rede robusta para o Portable.

    1) PowerShell/Windows nativo (certificados e proxy do Windows);
    2) requests usando proxy/ambiente;
    3) requests sem proxy do ambiente.
    """
    errors = []
    if os.name == "nt":
        try:
            return _powershell_get_text(url, headers=headers, timeout_sec=max(12, read_timeout))
        except Exception as exc:
            errors.append("Windows: " + str(exc))

    for trust_env, label in ((True, "proxy/sistema"), (False, "direto")):
        try:
            with requests.Session() as session:
                session.trust_env = trust_env
                r = session.get(
                    url,
                    timeout=(connect_timeout, read_timeout),
                    headers=headers or {},
                    allow_redirects=True,
                )
                if r.status_code < 200 or r.status_code >= 300:
                    raise RuntimeError(f"HTTP {r.status_code}")
                return (r.text or "").strip()
        except Exception as exc:
            errors.append(label + ": " + str(exc))
    raise RuntimeError(" | ".join(errors[-3:]))


def fetch_matters(apps_script_url: str, target_date: date) -> tuple[dict[str, list[str]], dict]:
    """Port do ClippingFeedClient.fetchMatterUrls do Android.

    Mesmos parâmetros, chave, data yyyy-MM-dd, redirects e limites de timeout.
    Mantém todas as matterUrl únicas retornadas pelo Apps Script.
    """
    base = (apps_script_url or "").strip()
    if not base:
        raise RuntimeError("Gmail automático não configurado")
    if not _valid_webapp_url(base):
        raise RuntimeError("URL inválida do Apps Script")

    params = {"key": ACCESS_KEY, "action": "matters", "date": target_date.isoformat()}
    url = base + ("&" if "?" in base else "?") + urlencode(params)

    try:
        body = get_text_windows(
            url,
            headers={"User-Agent": ANDROID_FEED_UA, "Accept": "application/json,text/plain,*/*"},
            connect_timeout=5,
            read_timeout=18,
        )
    except Exception as exc:
        raise RuntimeError(f"Ponte Gmail: {exc}") from exc
    low = body[:120].lower()
    if low.startswith("<!doctype") or low.startswith("<html"):
        raise RuntimeError(
            "A ponte abriu HTML. Atualize a implantação do Apps Script e mantenha acesso como Qualquer pessoa."
        )
    try:
        root = json.loads(body)
    except Exception as exc:
        raise RuntimeError("Resposta inválida da ponte Gmail") from exc
    if not root.get("ok"):
        raise RuntimeError(root.get("error") or "Falha na ponte Gmail")

    out: dict[str, list[str]] = {}
    for item in root.get("matters") or []:
        name = str(item.get("name") or "").strip()
        matter_url = str(item.get("matterUrl") or "").strip()
        if not name or not matter_url:
            continue
        arr = out.setdefault(name, [])
        if matter_url not in arr:
            arr.append(matter_url)

    if not out:
        threads = int(root.get("threads") or 0)
        messages = int(root.get("messagesScanned") or 0)
        raw_links = int(root.get("rawLeiaMaisFound") or 0)
        dated = int(root.get("datedItemsMatched") or 0)
        if threads == 0 or messages == 0:
            raise RuntimeError("A ponte está ativa, mas não encontrou e-mails de capas aceitos (ex.: 'Monitoramento: Capa(s) de Jornais' ou 'CAPA DE JORNAIS 1 APP') para a data selecionada")
        if raw_links == 0:
            raise RuntimeError("Os e-mails foram encontrados, mas nenhum link 'Leia mais' foi localizado")
        if dated == 0:
            raise RuntimeError("Há links 'Leia mais', mas nenhum corresponde à data selecionada")
        raise RuntimeError("Nenhuma capa compatível foi classificada no Gmail para a data selecionada")

    return out, root


def download_image(url: str, dest: Path, referer: str = "", cookie_header: str = "", user_agent: str = IMAGE_UA) -> Path:
    headers = {
        "User-Agent": user_agent or IMAGE_UA,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    if cookie_header:
        headers["Cookie"] = cookie_header
    with requests.get(url, timeout=(7, 18), headers=headers, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "html" in ctype:
            raise RuntimeError("O endereço retornou HTML em vez da imagem da página.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(32 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)
                if total > 60 * 1024 * 1024:
                    raise RuntimeError("imagem maior que 60 MB")
    if dest.stat().st_size < 8192:
        raise RuntimeError("arquivo de imagem vazio/placeholder")
    return dest


def safe_slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "capa"
