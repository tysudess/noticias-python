from __future__ import annotations

"""Funções puras para a grade e as guias visuais do Estúdio V168."""

import math

DEFAULT_GUIDE_CONFIG = {
    "grid_enabled": False,
    "grid_step": 50,
    "thirds_enabled": False,
    "center_enabled": False,
    "safe_area_enabled": False,
}
VALID_GRID_STEPS = {10, 20, 50, 100, 200}


def _finite(value, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def _boolean(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on", "sim"}:
            return True
        if normalized in {"0", "false", "no", "off", "não", "nao", ""}:
            return False
    return default


def normalize_guide_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    step = int(round(_finite(source.get("grid_step", 50), 50)))
    if step not in VALID_GRID_STEPS:
        step = 50
    return {
        "grid_enabled": _boolean(source.get("grid_enabled", False)),
        "grid_step": step,
        "thirds_enabled": _boolean(source.get("thirds_enabled", False)),
        "center_enabled": _boolean(source.get("center_enabled", False)),
        "safe_area_enabled": _boolean(source.get("safe_area_enabled", False)),
    }


def visible_grid_positions(
    canvas_size: tuple[float, float],
    visible_bounds: tuple[float, float, float, float],
    step: float,
    zoom: float,
    *,
    min_screen_spacing: float = 14.0,
    max_lines: int = 180,
) -> dict:
    """Retorna linhas da grade relativas ao canto superior esquerdo do canvas.

    `visible_bounds` é (left, top, right, bottom) também relativo ao canvas.
    A grade reduz automaticamente a densidade quando o zoom está muito baixo.
    """
    width = _finite(canvas_size[0], 0.0)
    height = _finite(canvas_size[1], 0.0)
    left, top, right, bottom = (_finite(v, 0.0) for v in visible_bounds)
    base_step = _finite(step, 50.0)
    scale = _finite(zoom, 0.0)
    spacing = max(1.0, _finite(min_screen_spacing, 14.0))
    limit = max(2, min(1000, int(max_lines)))

    if width <= 0 or height <= 0 or base_step <= 0 or scale <= 0:
        return {"vertical": [], "horizontal": [], "effective_step": 0.0}

    left, right = sorted((max(0.0, min(width, left)), max(0.0, min(width, right))))
    top, bottom = sorted((max(0.0, min(height, top)), max(0.0, min(height, bottom))))
    multiplier = max(1, int(math.ceil(spacing / max(0.001, base_step * scale))))
    effective = base_step * multiplier

    def positions(start: float, end: float) -> list[float]:
        if end < start:
            return []
        first = math.ceil((start - 1e-9) / effective) * effective
        count = max(0, int(math.floor((end - first) / effective)) + 1)
        if count > limit:
            extra = int(math.ceil(count / limit))
            local_step = effective * extra
            first = math.ceil((start - 1e-9) / local_step) * local_step
            count = max(0, int(math.floor((end - first) / local_step)) + 1)
            return [round(first + index * local_step, 4) for index in range(min(count, limit))]
        return [round(first + index * effective, 4) for index in range(count)]

    return {
        "vertical": positions(left, right),
        "horizontal": positions(top, bottom),
        "effective_step": round(effective, 4),
    }


def composition_guide_positions(canvas_size: tuple[float, float]) -> dict:
    """Posições normalizadas de terços, centro e margens seguras de 5%."""
    width = max(0.0, _finite(canvas_size[0], 0.0))
    height = max(0.0, _finite(canvas_size[1], 0.0))
    if width <= 0 or height <= 0:
        return {"vertical_thirds": [], "horizontal_thirds": [], "center": None, "safe_rect": None}
    return {
        "vertical_thirds": [width / 3.0, width * 2.0 / 3.0],
        "horizontal_thirds": [height / 3.0, height * 2.0 / 3.0],
        "center": (width / 2.0, height / 2.0),
        "safe_rect": (width * 0.05, height * 0.05, width * 0.95, height * 0.95),
    }
