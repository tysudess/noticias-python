from __future__ import annotations

import json
from pathlib import Path

THEME_ESCURO = "escuro"
THEME_CLARO = "claro"
DEFAULT_THEME = THEME_ESCURO
SUPPORTED_THEMES = frozenset({THEME_ESCURO, THEME_CLARO})
_LEGACY_THEMES = {"marinho": THEME_ESCURO}


def normalize_theme(theme: object) -> str:
    """Normaliza temas atuais e migra a preferência antiga ``marinho``."""
    value = str(theme or DEFAULT_THEME).strip().lower()
    value = _LEGACY_THEMES.get(value, value)
    return value if value in SUPPORTED_THEMES else DEFAULT_THEME


def load_saved_theme(path: Path) -> str:
    """Lê a preferência sem impedir a inicialização se o arquivo estiver inválido."""
    target = Path(path)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return DEFAULT_THEME
        return normalize_theme(payload.get("theme", DEFAULT_THEME))
    except (OSError, ValueError, TypeError, AttributeError):
        return DEFAULT_THEME


def save_theme(path: Path, theme: str) -> None:
    """Grava a preferência de forma atômica, sem sobrescrever outros dados do app."""
    selected = normalize_theme(theme)
    if str(theme).strip().lower() not in SUPPORTED_THEMES:
        raise ValueError(f"Tema não suportado: {theme!r}")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    payload = {"version": 2, "theme": selected}
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
