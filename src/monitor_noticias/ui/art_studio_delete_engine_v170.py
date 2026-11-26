from __future__ import annotations

"""Operações puras de seleção e plano de exclusão do Estúdio V170."""

from collections.abc import Callable, Iterable


def selected_roots(
    items: Iterable[object],
    parent_of: Callable[[object], object | None],
) -> list[object]:
    """Remove duplicatas e descendentes quando um ancestral também está selecionado."""
    unique: list[object] = []
    seen: set[int] = set()
    for item in items:
        marker = id(item)
        if marker not in seen:
            unique.append(item)
            seen.add(marker)

    selected = set(unique)
    roots: list[object] = []
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
            roots.append(item)
    return roots


def deletion_plan(
    items: Iterable[object],
    *,
    parent_of: Callable[[object], object | None],
    belongs_to_scene: Callable[[object], bool],
    is_locked: Callable[[object], bool],
) -> tuple[list[object], list[object]]:
    """Retorna (excluíveis, preservados) após filtrar itens inválidos e descendentes."""
    valid = []
    for item in items:
        try:
            if belongs_to_scene(item):
                valid.append(item)
        except (RuntimeError, ReferenceError):
            continue

    roots = selected_roots(valid, parent_of)
    deletable: list[object] = []
    preserved: list[object] = []
    for item in roots:
        try:
            (preserved if is_locked(item) else deletable).append(item)
        except (RuntimeError, ReferenceError):
            continue
    return deletable, preserved
