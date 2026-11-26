from __future__ import annotations

"""Cálculos puros para a visão geral de páginas e o inspetor V176."""

from math import isfinite
from typing import Iterable


def page_preview_size(
    source_width: float,
    source_height: float,
    *,
    max_width: int = 232,
    max_height: int = 142,
) -> tuple[int, int]:
    """Dimensiona uma prévia sem distorcer a proporção da página."""
    width = float(source_width)
    height = float(source_height)
    if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0:
        raise ValueError("A página precisa ter dimensões finitas e positivas.")
    bound_w = max(1, int(max_width))
    bound_h = max(1, int(max_height))
    factor = min(bound_w / width, bound_h / height)
    return max(1, round(width * factor)), max(1, round(height * factor))


def page_grid_columns(
    available_width: int,
    *,
    min_card_width: int = 244,
    gap: int = 14,
    max_columns: int = 4,
) -> int:
    """Calcula colunas responsivas para a grade de páginas."""
    width = max(0, int(available_width))
    card = max(120, int(min_card_width))
    spacing = max(0, int(gap))
    maximum = max(1, int(max_columns))
    return max(1, min(maximum, (width + spacing) // (card + spacing)))


def normalize_selection_bounds(
    rectangles: Iterable[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    """Combina retângulos no formato (x, y, largura, altura)."""
    values = []
    for rect in rectangles:
        if len(rect) != 4:
            raise ValueError("Cada retângulo deve conter quatro valores.")
        x, y, width, height = (float(value) for value in rect)
        if not all(isfinite(value) for value in (x, y, width, height)):
            raise ValueError("Os limites da seleção precisam ser finitos.")
        values.append((x, y, x + width, y + height))
    if not values:
        return None
    left = min(item[0] for item in values)
    top = min(item[1] for item in values)
    right = max(item[2] for item in values)
    bottom = max(item[3] for item in values)
    return left, top, max(0.0, right - left), max(0.0, bottom - top)


def selection_summary(
    rectangles: Iterable[tuple[float, float, float, float]],
    *,
    rotation: float | None = None,
    opacity: float | None = None,
) -> dict[str, float | None] | None:
    """Produz dados compactos de posição/tamanho para o inspetor contextual."""
    bounds = normalize_selection_bounds(rectangles)
    if bounds is None:
        return None
    x, y, width, height = bounds
    angle = None if rotation is None else float(rotation)
    alpha = None if opacity is None else max(0.0, min(1.0, float(opacity)))
    if angle is not None and not isfinite(angle):
        raise ValueError("A rotação precisa ser finita.")
    if alpha is not None and not isfinite(alpha):
        raise ValueError("A opacidade precisa ser finita.")
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "rotation": angle,
        "opacity": alpha,
    }
