from __future__ import annotations

"""Operações geométricas puras para dimensionar a bancada do Central Studio."""


def workspace_split_sizes(
    available_width: int,
    *,
    min_left: int = 184,
    preferred_left: int = 228,
    max_left: int = 258,
    min_center: int = 560,
    min_right: int = 246,
    preferred_right: int = 318,
    max_right: int = 348,
) -> tuple[int, int, int]:
    """Calcula larguras iniciais dos painéis, priorizando o canvas central.

    A soma é exatamente ``available_width`` para evitar arredondamentos que
    deixem espaços vazios no QSplitter. Em janelas menores, os painéis laterais
    encolhem antes de consumir a largura mínima do canvas.
    """
    total = max(0, int(available_width))
    if total == 0:
        return 0, 0, 0

    left = min(max_left, max(min_left, min(preferred_left, round(total * 0.145))))
    right = min(max_right, max(min_right, min(preferred_right, round(total * 0.195))))

    center = total - left - right
    if center < min_center:
        deficit = min_center - center
        reducible_right = max(0, right - min_right)
        reduction = min(deficit, reducible_right)
        right -= reduction
        deficit -= reduction
        reducible_left = max(0, left - min_left)
        reduction = min(deficit, reducible_left)
        left -= reduction
        deficit -= reduction
        center = total - left - right

    # A janela pode ser menor que a soma dos mínimos. Nesse caso distribuímos
    # o espaço sem produzir medidas negativas; o canvas continua recebendo
    # a maior parte da largura disponível.
    if center < 0:
        left = min(left, max(1, round(total * 0.16)))
        right = min(right, max(1, round(total * 0.22)))
        if left + right >= total:
            left = max(1, round(total * 0.15))
            right = max(0, total - left - 1)
        center = max(0, total - left - right)

    return int(left), int(center), int(right)


def compact_pages_bar_metrics(
    *,
    expanded: bool = True,
) -> dict[str, int]:
    """Métricas padronizadas para a faixa de páginas expandida/recolhida."""
    if expanded:
        return {
            "height": 46,
            "vertical_margin": 4,
            "horizontal_margin": 7,
            "spacing": 4,
            "button_height": 28,
            "tab_vertical_padding": 4,
            "tab_horizontal_padding": 9,
        }
    return {
        "height": 0,
        "vertical_margin": 0,
        "horizontal_margin": 0,
        "spacing": 0,
        "button_height": 0,
        "tab_vertical_padding": 0,
        "tab_horizontal_padding": 0,
    }
