from __future__ import annotations

"""Configurações e estilos tipográficos puros do Estúdio V167.

Este módulo não depende de Qt. A normalização mantém os valores seguros e
estáveis antes de aplicar formatação ao documento rico do QGraphicsTextItem.
"""

import math
import re

DEFAULT_TYPOGRAPHY_CONFIG = {
    "font_family": "Segoe UI",
    "font_size": 54,
    "weight": 700,
    "italic": False,
    "underline": False,
    "letter_spacing": 0.0,
    "word_spacing": 0.0,
    "line_spacing": 110.0,
    "paragraph_spacing": 0.0,
    "capitalization": "mixed",
    "alignment": "left",
    "outline_width": 0.0,
    "outline_color": "#102A43",
    "highlight_enabled": False,
    "highlight_color": "#F2D777",
    "use_text_color": False,
    "text_color": "#102A43",
}

TYPOGRAPHY_PRESETS = {
    "headline": {
        "font_family": "Arial", "font_size": 64, "weight": 800,
        "line_spacing": 96, "letter_spacing": -0.4, "alignment": "left",
        "use_text_color": True, "text_color": "#102A43",
    },
    "subtitle": {
        "font_family": "Arial", "font_size": 36, "weight": 600,
        "line_spacing": 108, "letter_spacing": 0.1, "alignment": "left",
        "use_text_color": True, "text_color": "#315B78",
    },
    "body": {
        "font_family": "Segoe UI", "font_size": 25, "weight": 400,
        "line_spacing": 135, "paragraph_spacing": 8, "alignment": "left",
        "use_text_color": True, "text_color": "#17344A",
    },
    "caption": {
        "font_family": "Segoe UI", "font_size": 18, "weight": 600,
        "line_spacing": 115, "letter_spacing": 0.5, "capitalization": "upper",
        "use_text_color": True, "text_color": "#64748B",
    },
    "quote": {
        "font_family": "Georgia", "font_size": 38, "weight": 500,
        "italic": True, "line_spacing": 125, "alignment": "center",
        "use_text_color": True, "text_color": "#17344A",
    },
    "highlight": {
        "font_family": "Segoe UI", "font_size": 28, "weight": 700,
        "highlight_enabled": True, "highlight_color": "#F2D777",
        "use_text_color": True, "text_color": "#102A43",
    },
}

_VALID_CAPITALIZATION = {"mixed", "upper", "lower", "small", "capitalize"}
_VALID_ALIGNMENT = {"left", "center", "right", "justify"}
_VALID_COLORS = re.compile(r"^#[0-9a-fA-F]{6}$")


def _number(value, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(parsed):
        return default
    return max(low, min(high, parsed))


def _boolean(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        value = value.strip().casefold()
        if value in {"1", "true", "yes", "on", "sim"}:
            return True
        if value in {"0", "false", "no", "off", "não", "nao", ""}:
            return False
    return default


def _color(value, default: str) -> str:
    candidate = str(value or "").strip()
    return candidate.upper() if _VALID_COLORS.fullmatch(candidate) else default


def normalize_typography_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    result = dict(DEFAULT_TYPOGRAPHY_CONFIG)

    family = str(source.get("font_family", result["font_family"]) or "").strip()
    result["font_family"] = (family[:96] or result["font_family"])
    result["font_size"] = int(round(_number(source.get("font_size"), 54, 8, 600)))
    result["weight"] = int(round(_number(source.get("weight"), 700, 100, 900) / 100) * 100)
    result["italic"] = _boolean(source.get("italic", False))
    result["underline"] = _boolean(source.get("underline", False))
    result["letter_spacing"] = _number(source.get("letter_spacing"), 0.0, -20.0, 80.0)
    result["word_spacing"] = _number(source.get("word_spacing"), 0.0, -20.0, 150.0)
    result["line_spacing"] = _number(source.get("line_spacing"), 110.0, 80.0, 300.0)
    result["paragraph_spacing"] = _number(source.get("paragraph_spacing"), 0.0, 0.0, 120.0)

    capitalization = str(source.get("capitalization", "mixed")).strip().lower()
    result["capitalization"] = capitalization if capitalization in _VALID_CAPITALIZATION else "mixed"
    alignment = str(source.get("alignment", "left")).strip().lower()
    result["alignment"] = alignment if alignment in _VALID_ALIGNMENT else "left"

    result["outline_width"] = _number(source.get("outline_width"), 0.0, 0.0, 24.0)
    result["outline_color"] = _color(source.get("outline_color"), "#102A43")
    result["highlight_enabled"] = _boolean(source.get("highlight_enabled", False))
    result["highlight_color"] = _color(source.get("highlight_color"), "#F2D777")
    result["use_text_color"] = _boolean(source.get("use_text_color", False))
    result["text_color"] = _color(source.get("text_color"), "#102A43")
    return result


def typography_preset(name: str) -> dict:
    preset = TYPOGRAPHY_PRESETS.get(str(name or "").strip().lower(), {})
    return normalize_typography_config({**DEFAULT_TYPOGRAPHY_CONFIG, **preset})
