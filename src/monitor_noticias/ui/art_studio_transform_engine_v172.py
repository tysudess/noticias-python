from __future__ import annotations

"""Operações geométricas puras para transformação e composição do Central Studio."""

from collections.abc import Callable, Iterable


def selected_roots(
    items: Iterable[object],
    parent_of: Callable[[object], object | None],
) -> list[object]:
    """Remove duplicatas e descendentes quando um grupo ancestral também está selecionado."""
    unique: list[object] = []
    seen: set[int] = set()
    for item in items:
        marker = id(item)
        if marker not in seen:
            unique.append(item)
            seen.add(marker)
    selected = set(unique)
    result: list[object] = []
    for item in unique:
        parent = parent_of(item)
        nested = False
        visited: set[int] = set()
        while parent is not None and id(parent) not in visited:
            visited.add(id(parent))
            if parent in selected:
                nested = True
                break
            parent = parent_of(parent)
        if not nested:
            result.append(item)
    return result


def proportional_size(
    current_width: float,
    current_height: float,
    target_width: float,
    target_height: float,
    *,
    keep_ratio: bool,
    changed_axis: str = "width",
) -> tuple[float, float]:
    """Normaliza tamanho e aplica proporção usando o último eixo editado."""
    width = max(1.0, float(target_width))
    height = max(1.0, float(target_height))
    current_width = max(1.0, float(current_width))
    current_height = max(1.0, float(current_height))
    if keep_ratio:
        ratio = current_height / current_width
        if changed_axis == "height":
            width = height / ratio
        else:
            height = width * ratio
    return width, height


def distribution_offsets(
    intervals: Iterable[tuple[float, float]],
) -> list[float]:
    """Retorna deslocamentos horizontais/verticais para espaçar 3+ itens igualmente.

    `intervals` contém (início, fim) no eixo escolhido. A ordem espacial é
    preservada, os itens extremos permanecem fixos e a distribuição pode
    produzir intervalos negativos quando os objetos se sobrepõem.
    """
    values = [(float(start), float(end), index) for index, (start, end) in enumerate(intervals)]
    if len(values) < 3:
        raise ValueError("A distribuição exige pelo menos três objetos.")
    values.sort(key=lambda value: (value[0], value[2]))
    widths = [max(0.0, end - start) for start, end, _ in values]
    total_width = sum(widths)
    first_start = values[0][0]
    last_end = values[-1][1]
    gap = (last_end - first_start - total_width) / (len(values) - 1)
    offsets = [0.0] * len(values)
    cursor = first_start
    for sorted_index, (start, _end, original_index) in enumerate(values):
        offsets[original_index] = cursor - start
        cursor += widths[sorted_index] + gap
    # Evita resíduos numéricos e mantém exatamente os extremos fixos.
    offsets[values[0][2]] = 0.0
    offsets[values[-1][2]] = 0.0
    return offsets


def alignment_delta(
    bounds: tuple[float, float, float, float],
    page: tuple[float, float, float, float],
    mode: str,
) -> tuple[float, float]:
    """Calcula o deslocamento de uma seleção (x, y, largura, altura) para a página."""
    x, y, width, height = map(float, bounds)
    px, py, pwidth, pheight = map(float, page)
    if mode == "left":
        return px - x, 0.0
    if mode == "center-h":
        return px + (pwidth - width) / 2.0 - x, 0.0
    if mode == "right":
        return px + pwidth - width - x, 0.0
    if mode == "top":
        return 0.0, py - y
    if mode == "center-v":
        return 0.0, py + (pheight - height) / 2.0 - y
    if mode == "bottom":
        return 0.0, py + pheight - height - y
    raise ValueError(f"Modo de alinhamento desconhecido: {mode}")


def clamp_opacity(value: int | float) -> float:
    """Converte opacidade em percentagem para o intervalo Qt [0, 1]."""
    return max(0.0, min(1.0, float(value) / 100.0))


def has_locked_descendant(
    item: object,
    *,
    children_of: Callable[[object], Iterable[object]],
    is_locked: Callable[[object], bool],
) -> bool:
    """Impede transformar um grupo que contenha qualquer descendente bloqueado."""
    stack = list(children_of(item))
    visited: set[int] = set()
    while stack:
        child = stack.pop()
        marker = id(child)
        if marker in visited:
            continue
        visited.add(marker)
        if is_locked(child):
            return True
        stack.extend(children_of(child))
    return False
