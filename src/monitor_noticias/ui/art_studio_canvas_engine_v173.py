from __future__ import annotations

"""Operações geométricas puras para as alças diretas do Central Studio V173."""

from math import atan2, degrees, isfinite
from typing import Iterable


def resized_rect(
    rect: tuple[float, float, float, float],
    pointer: tuple[float, float],
    direction: tuple[int, int],
    *,
    minimum: float = 16.0,
    keep_ratio: bool = False,
) -> tuple[float, float, float, float]:
    """Calcula um novo retângulo mantendo fixo o canto/lado oposto.

    O retângulo usa (x, y, largura, altura). A direção contém -1, 0 ou 1
    para cada eixo e o ponto recebido já está no espaço local original.
    """
    x, y, width, height = (float(value) for value in rect)
    px, py = (float(value) for value in pointer)
    if not all(isfinite(value) for value in (x, y, width, height, px, py)):
        raise ValueError("Coordenadas de redimensionamento precisam ser finitas.")
    if width <= 0 or height <= 0:
        raise ValueError("O retângulo original precisa ter dimensões positivas.")
    dx, dy = int(direction[0]), int(direction[1])
    if dx not in (-1, 0, 1) or dy not in (-1, 0, 1) or (dx == 0 and dy == 0):
        raise ValueError("Direção de alça inválida.")
    minimum = max(1.0, float(minimum))

    left, top, right, bottom = x, y, x + width, y + height
    if dx < 0:
        left = min(px, right - minimum)
    elif dx > 0:
        right = max(px, left + minimum)
    if dy < 0:
        top = min(py, bottom - minimum)
    elif dy > 0:
        bottom = max(py, top + minimum)

    if keep_ratio and dx and dy:
        ratio = width / height
        new_width, new_height = right - left, bottom - top
        # Usa o eixo que mais se afastou proporcionalmente da medida inicial.
        width_change = abs(new_width / width - 1.0)
        height_change = abs(new_height / height - 1.0)
        if width_change >= height_change:
            new_height = max(minimum, new_width / ratio)
            if dy < 0:
                top = bottom - new_height
            else:
                bottom = top + new_height
        else:
            new_width = max(minimum, new_height * ratio)
            if dx < 0:
                left = right - new_width
            else:
                right = left + new_width

    return left, top, max(minimum, right - left), max(minimum, bottom - top)


def uniform_scale_factor(
    start_rect: tuple[float, float, float, float],
    pointer: tuple[float, float],
    direction: tuple[int, int],
    *,
    minimum_factor: float = 0.05,
    maximum_factor: float = 8.0,
) -> float:
    """Calcula escala uniforme a partir do canto oposto de um grupo/imagem."""
    x, y, width, height = (float(value) for value in start_rect)
    px, py = (float(value) for value in pointer)
    dx, dy = int(direction[0]), int(direction[1])
    if dx == 0 or dy == 0:
        raise ValueError("Escala uniforme por alça requer um canto.")
    anchor_x = x + width if dx < 0 else x
    anchor_y = y + height if dy < 0 else y
    moving_x = x if dx < 0 else x + width
    moving_y = y if dy < 0 else y + height
    factor_x = (px - anchor_x) / (moving_x - anchor_x)
    factor_y = (py - anchor_y) / (moving_y - anchor_y)
    # A escolha do eixo com maior alteração relativa reduz tremor quando o
    # usuário arrasta quase na diagonal, mas um eixo fica ligeiramente atrás.
    factor = factor_x if abs(factor_x - 1.0) >= abs(factor_y - 1.0) else factor_y
    return max(float(minimum_factor), min(float(maximum_factor), factor))


def rotation_delta(start: tuple[float, float], current: tuple[float, float]) -> float:
    """Ângulo incremental em graus entre dois vetores em torno do centro."""
    sx, sy = map(float, start)
    cx, cy = map(float, current)
    if (sx == 0 and sy == 0) or (cx == 0 and cy == 0):
        return 0.0
    angle = degrees(atan2(cy, cx) - atan2(sy, sx))
    while angle <= -180.0:
        angle += 360.0
    while angle > 180.0:
        angle -= 360.0
    return angle


def snap_rotation(angle: float, step: float = 15.0) -> float:
    """Arredonda ângulo para incremento, mantendo sentido e precisão."""
    value = float(angle)
    step = float(step)
    if not isfinite(value) or not isfinite(step) or step <= 0:
        raise ValueError("Ângulo e incremento precisam ser finitos e positivos.")
    return round(value / step) * step


def normalize_stroke_style(value: str) -> str:
    style = str(value or "solid").strip().lower()
    return style if style in {"solid", "dash", "dot"} else "solid"


def normalize_stroke_width(value: float) -> float:
    width = float(value)
    if not isfinite(width):
        return 0.0
    return max(0.0, min(48.0, width))


def resize_bounds_for_handles(
    rect: tuple[float, float, float, float],
    directions: Iterable[tuple[int, int]],
) -> list[tuple[float, float]]:
    """Devolve posições locais das alças, útil para validar layouts e hit areas."""
    x, y, width, height = map(float, rect)
    result = []
    for dx, dy in directions:
        px = x if dx < 0 else x + width if dx > 0 else x + width / 2.0
        py = y if dy < 0 else y + height if dy > 0 else y + height / 2.0
        result.append((px, py))
    return result
