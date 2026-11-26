from __future__ import annotations

"""Cálculos puros da biblioteca visual, camadas e navegação V177."""

from math import isfinite


def library_grid_columns(
    available_width: int,
    *,
    min_card_width: int = 94,
    gap: int = 7,
    max_columns: int = 2,
) -> int:
    """Calcula colunas da biblioteca sem permitir cartões excessivamente estreitos."""
    width = max(0, int(available_width))
    card = max(72, int(min_card_width))
    spacing = max(0, int(gap))
    maximum = max(1, min(4, int(max_columns)))
    return max(1, min(maximum, (width + spacing) // (card + spacing)))


def layer_order_z_values(count: int) -> tuple[float, ...]:
    """Ordem de Z para lista na qual a primeira camada é a mais acima."""
    amount = max(0, int(count))
    return tuple(float(amount - index) for index in range(amount))


def layer_context_actions(
    *,
    selection_count: int,
    all_unlocked: bool,
    single_kind: str | None = None,
) -> tuple[str, ...]:
    """Determina ações do menu de camadas conforme seleção e proteção."""
    count = max(0, int(selection_count))
    if count == 0:
        return ()
    actions: list[str] = []
    if count == 1:
        actions.extend(("rename", "visibility", "lock"))
        if all_unlocked:
            actions.extend(("duplicate", "front", "back"))
        if single_kind == "group" and all_unlocked:
            actions.append("ungroup")
    else:
        actions.append("lock")
        if all_unlocked:
            actions.extend(("duplicate", "front", "back", "group"))
    # Excluir fica disponível mesmo com uma seleção mista: o mecanismo V170
    # remove somente as camadas desbloqueadas e preserva as protegidas.
    actions.append("delete")
    return tuple(actions)


def zoom_factor_to_target(current_percent: float, target_percent: float) -> float:
    """Fator relativo para zoom_by, validando os limites usados pelo editor."""
    current = float(current_percent)
    target = float(target_percent)
    if not isfinite(current) or not isfinite(target) or current <= 0 or target <= 0:
        raise ValueError("Os níveis de zoom precisam ser finitos e positivos.")
    if not 10 <= target <= 500:
        raise ValueError("O zoom desejado deve ficar entre 10% e 500%.")
    return target / current


def nearest_zoom_preset(current_percent: float, presets: tuple[int, ...] = (25, 50, 75, 100, 125, 150, 200, 300)) -> int:
    """Retorna o preset mais próximo para sincronizar o seletor após zoom manual."""
    current = float(current_percent)
    if not isfinite(current) or current <= 0:
        raise ValueError("O zoom atual precisa ser finito e positivo.")
    values = tuple(int(value) for value in presets if int(value) > 0)
    if not values:
        raise ValueError("Informe ao menos um preset válido.")
    return min(values, key=lambda value: (abs(value - current), value))
