from __future__ import annotations

"""Cálculos independentes de Qt para o refinamento da bancada V175."""

from math import isfinite


def thumbnail_dimensions(
    source_width: float,
    source_height: float,
    *,
    max_width: int = 48,
    max_height: int = 34,
) -> tuple[int, int]:
    """Calcula dimensões de uma miniatura sem distorcer a proporção da página."""
    width = float(source_width)
    height = float(source_height)
    if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0:
        raise ValueError("A dimensão de origem precisa ser finita e positiva.")
    bound_w = max(1, int(max_width))
    bound_h = max(1, int(max_height))
    ratio = min(bound_w / width, bound_h / height)
    return max(1, round(width * ratio)), max(1, round(height * ratio))


def splitter_sizes_for_visibility(
    available_width: int,
    expanded_sizes: tuple[int, int, int] | list[int],
    *,
    left_visible: bool = True,
    right_visible: bool = True,
) -> tuple[int, int, int]:
    """Redistribui a bancada mantendo o canvas com todo o espaço liberado.

    ``expanded_sizes`` guarda a última distribuição com ambos os painéis abertos.
    O resultado sempre soma ``available_width`` e painéis recolhidos recebem zero.
    """
    total = max(0, int(available_width))
    if total == 0:
        return 0, 0, 0
    if len(expanded_sizes) != 3:
        raise ValueError("A bancada exige três larguras de referência.")
    base = [max(0, int(value)) for value in expanded_sizes]
    if not any(base):
        base = [228, 900, 318]
    if not left_visible and not right_visible:
        return 0, total, 0
    if not left_visible:
        denominator = max(1, base[1] + base[2])
        right = min(total, max(0, round(total * base[2] / denominator)))
        return 0, total - right, right
    if not right_visible:
        denominator = max(1, base[0] + base[1])
        left = min(total, max(0, round(total * base[0] / denominator)))
        return left, total - left, 0

    denominator = max(1, sum(base))
    left = round(total * base[0] / denominator)
    right = round(total * base[2] / denominator)
    center = total - left - right
    if center < 0:
        center = 0
        left = min(total, left)
        right = total - left
    return left, center, right


def contextual_actions(
    *,
    selection_count: int,
    has_text: bool = False,
    has_shape: bool = False,
    has_group: bool = False,
    can_group: bool = False,
) -> tuple[str, ...]:
    """Lista ações da barra contextual sem expor operações inválidas."""
    count = max(0, int(selection_count))
    if count == 0:
        return ()
    actions = ["duplicate", "transform", "delete"]
    if count == 1 and has_text:
        actions.insert(1, "edit_text")
    if count == 1 and has_shape:
        actions.insert(1, "shape")
    if count == 1 and has_group:
        actions.insert(1, "ungroup")
    elif count > 1 and can_group:
        actions.insert(1, "group")
    return tuple(actions)
