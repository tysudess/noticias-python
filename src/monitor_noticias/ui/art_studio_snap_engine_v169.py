from __future__ import annotations

"""Cálculo puro de encaixe magnético e guias inteligentes do Estúdio V169."""

import math
from collections.abc import Iterable, Sequence

DEFAULT_SNAP_CONFIG = {
    "enabled": False,
    "snap_to_objects": True,
    "snap_to_page": True,
    "snap_to_grid": False,
    "snap_to_composition_guides": True,
    "show_guides": True,
    "threshold_px": 8,
}
VALID_THRESHOLDS = {4, 6, 8, 10, 12, 16, 20, 24}


def _finite(value, default: float = 0.0) -> float:
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


def normalize_snap_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    try:
        threshold = int(round(_finite(source.get("threshold_px", 8), 8)))
    except (TypeError, ValueError, OverflowError):
        threshold = 8
    if threshold not in VALID_THRESHOLDS:
        threshold = min(VALID_THRESHOLDS, key=lambda candidate: (abs(candidate - threshold), candidate))
    return {
        "enabled": _boolean(source.get("enabled", False)),
        "snap_to_objects": _boolean(source.get("snap_to_objects", True), True),
        "snap_to_page": _boolean(source.get("snap_to_page", True), True),
        "snap_to_grid": _boolean(source.get("snap_to_grid", False)),
        "snap_to_composition_guides": _boolean(source.get("snap_to_composition_guides", True), True),
        "show_guides": _boolean(source.get("show_guides", True), True),
        "threshold_px": threshold,
    }


def _rect(value) -> tuple[float, float, float, float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
        return None
    left, top, right, bottom = (_finite(part, float("nan")) for part in value)
    if not all(math.isfinite(part) for part in (left, top, right, bottom)):
        return None
    if right < left or bottom < top:
        return None
    return left, top, right, bottom


def _axis_anchors(bounds: tuple[float, float, float, float], axis: str) -> tuple[float, float, float]:
    left, top, right, bottom = bounds
    if axis == "x":
        return left, (left + right) / 2.0, right
    return top, (top + bottom) / 2.0, bottom


def _best_axis_snap(
    moving: tuple[float, float, float, float],
    targets: Iterable[tuple[float, float, float, float]],
    axis: str,
    threshold_scene: float,
    *,
    extra_lines: Iterable[float] = (),
    grid_step: float | None = None,
    grid_origin: float = 0.0,
) -> dict:
    moving_anchors = _axis_anchors(moving, axis)
    candidates: list[tuple[float, int, float, str, float]] = []
    anchor_names = ("start", "center", "end")
    for target in targets:
        target_anchors = _axis_anchors(target, axis)
        for moving_index, moving_value in enumerate(moving_anchors):
            for target_index, target_value in enumerate(target_anchors):
                delta = target_value - moving_value
                distance = abs(delta)
                if distance > threshold_scene:
                    continue
                if moving_index == target_index == 1:
                    priority = 0  # centro com centro
                elif moving_index == target_index:
                    priority = 1  # bordas equivalentes
                else:
                    priority = 2  # borda com centro ou borda oposta
                relation = f"{anchor_names[moving_index]}:{anchor_names[target_index]}"
                candidates.append((distance, priority, target_value, relation, delta))

    # Guias de composição V168: terços, centro e limites da área segura.
    for moving_index, moving_value in enumerate(moving_anchors):
        for line in extra_lines:
            line_value = _finite(line, float("nan"))
            if not math.isfinite(line_value):
                continue
            delta = line_value - moving_value
            distance = abs(delta)
            if distance <= threshold_scene:
                priority = 1 if moving_index == 1 else 2
                candidates.append((distance, priority, line_value, f"guide:{anchor_names[moving_index]}", delta))

        # A grade só precisa testar o múltiplo mais próximo para cada âncora.
        step = _finite(grid_step, 0.0) if grid_step is not None else 0.0
        if step > 0:
            origin = _finite(grid_origin, 0.0)
            nearest = origin + round((moving_value - origin) / step) * step
            delta = nearest - moving_value
            distance = abs(delta)
            if distance <= threshold_scene:
                priority = 1 if moving_index == 1 else 2
                candidates.append((distance, priority, nearest, f"grid:{anchor_names[moving_index]}", delta))

    if not candidates:
        return {"delta": 0.0, "coordinate": None, "relation": None}
    # Distância é o critério principal; prioridades tornam os empates previsíveis.
    candidates.sort(key=lambda candidate: (candidate[0], candidate[1], candidate[2]))
    _distance, _priority, coordinate, relation, delta = candidates[0]
    return {
        "delta": round(delta, 6),
        "coordinate": round(coordinate, 6),
        "relation": relation,
    }


def compute_smart_snap(
    moving_bounds,
    target_bounds: Iterable,
    canvas_bounds,
    zoom: float,
    threshold_px: int = 8,
    *,
    snap_to_objects: bool = True,
    snap_to_page: bool = True,
    snap_to_grid: bool = False,
    grid_step: float | None = None,
    grid_origin: tuple[float, float] = (0.0, 0.0),
    extra_x_lines: Iterable[float] = (),
    extra_y_lines: Iterable[float] = (),
) -> dict:
    """Calcula deltas de encaixe em cena, recebendo tolerância em pixels de tela.

    Retorna deslocamento X/Y e coordenadas das linhas-guia. Retângulos usam
    (left, top, right, bottom) em coordenadas da cena.
    """
    moving = _rect(moving_bounds)
    canvas = _rect(canvas_bounds)
    scale = abs(_finite(zoom, 0.0))
    threshold = max(0.0, _finite(threshold_px, 8.0))
    if moving is None or canvas is None or scale <= 0:
        return {
            "dx": 0.0, "dy": 0.0, "x_guide": None, "y_guide": None,
            "x_relation": None, "y_relation": None, "threshold_scene": 0.0,
        }

    threshold_scene = threshold / max(0.001, scale)
    targets: list[tuple[float, float, float, float]] = []
    if snap_to_objects:
        try:
            candidates = target_bounds or ()
            for candidate in candidates:
                normalized = _rect(candidate)
                if normalized is not None:
                    targets.append(normalized)
        except TypeError:
            pass
    if snap_to_page:
        targets.append(canvas)

    extra_x_lines = tuple(extra_x_lines or ())
    extra_y_lines = tuple(extra_y_lines or ())
    use_grid = bool(snap_to_grid and _finite(grid_step, 0.0) > 0)
    if not targets and not extra_x_lines and not extra_y_lines and not use_grid:
        return {
            "dx": 0.0, "dy": 0.0, "x_guide": None, "y_guide": None,
            "x_relation": None, "y_relation": None,
            "threshold_scene": round(threshold_scene, 6),
        }

    origin_x = _finite(grid_origin[0], 0.0) if isinstance(grid_origin, Sequence) and len(grid_origin) > 0 else 0.0
    origin_y = _finite(grid_origin[1], 0.0) if isinstance(grid_origin, Sequence) and len(grid_origin) > 1 else 0.0
    x_snap = _best_axis_snap(
        moving, targets, "x", threshold_scene,
        extra_lines=extra_x_lines,
        grid_step=grid_step if use_grid else None,
        grid_origin=origin_x,
    )
    y_snap = _best_axis_snap(
        moving, targets, "y", threshold_scene,
        extra_lines=extra_y_lines,
        grid_step=grid_step if use_grid else None,
        grid_origin=origin_y,
    )
    return {
        "dx": x_snap["delta"],
        "dy": y_snap["delta"],
        "x_guide": x_snap["coordinate"],
        "y_guide": y_snap["coordinate"],
        "x_relation": x_snap["relation"],
        "y_relation": y_snap["relation"],
        "threshold_scene": round(threshold_scene, 6),
    }
