import json, os, sys
from pathlib import Path

APP_NAME = "Principais Capas"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwO46cUIb0O--6_LUrysIjhCAlJJqjw0PRCuRLOTndiy4BkFZhNbXPQgA3rc9H8YC5l/exec"
ACCESS_KEY = "PC26-8F2D4A7B-31C9E6F0-5A1D"
GMAIL_PAPERS = {
    "O GLOBO", "FOLHA DE SÃO PAULO", "ESTADÃO",
    "CORREIO BRAZILIENSE", "ESTADO DE MINAS", "THE NEW YORK TIMES"
}
WEB_PAPERS = {"VALOR ECONÔMICO", "THE WASHINGTON POST"}
BUNDLED_URL_VERSION = "1.1.0"


def bundle_dir() -> Path:
    # Dentro do MonitorDeNoticias.exe os assets ficam preservados no namespace
    # monitor_noticias/capas_tool/assets.
    if getattr(sys, "frozen", False):
        return (
            Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            / "monitor_noticias"
            / "capas_tool"
        )
    return Path(__file__).resolve().parent.parent


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    # Portable primeiro: tenta pasta ao lado do EXE. Se não puder escrever, usa LOCALAPPDATA.
    p = executable_dir() / "data"
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return p
    except Exception:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PrincipaisCapas"
        base.mkdir(parents=True, exist_ok=True)
        return base


def cache_dir() -> Path:
    p = data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def downloads_dir() -> Path:
    p = Path.home() / "Downloads" / "Principais Capas"
    p.mkdir(parents=True, exist_ok=True)
    return p


def settings_path() -> Path:
    return data_dir() / "settings.json"


def load_settings() -> dict:
    p = settings_path()
    d = {}
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                d = raw
        except Exception:
            d = {}

    # Mesmo comportamento do Android v0.7.5.4+: ao migrar para uma versão
    # nova do endereço embutido, aplica o /exec oficial uma única vez. Depois
    # disso o usuário ainda pode alterar manualmente pelo botão Apps Script.
    if d.get("bundled_url_version") != BUNDLED_URL_VERSION:
        d["apps_script_url"] = APPS_SCRIPT_URL
        d["bundled_url_version"] = BUNDLED_URL_VERSION
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    else:
        d.setdefault("apps_script_url", APPS_SCRIPT_URL)
    return d


def save_settings(settings: dict):
    settings_path().write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
