from __future__ import annotations

"""Formatos de saída do Editor de Vídeo da Central."""

from typing import Any

ORIGINAL_FORMAT = "original"
LANDSCAPE_16_9_FORMAT = "landscape_16_9"
LANDSCAPE_RESOLUTION_PREFIX = "__CENTRAL_LANDSCAPE_16_9__:"

_FIXED_LANDSCAPE_HEIGHTS = {
    "360p": 360,
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}


def encode_resolution_choice(resolution: str, output_format: str) -> str:
    """Transporta o formato junto da resolução sem mudar a API do worker legado."""
    choice = str(resolution or "Original")
    if str(output_format or ORIGINAL_FORMAT) == LANDSCAPE_16_9_FORMAT:
        return LANDSCAPE_RESOLUTION_PREFIX + choice
    return choice


def decode_resolution_choice(value: str) -> tuple[str, str]:
    """Retorna (formato, resolução) a partir do valor recebido pelo worker."""
    choice = str(value or "Original")
    if choice.startswith(LANDSCAPE_RESOLUTION_PREFIX):
        resolution = choice[len(LANDSCAPE_RESOLUTION_PREFIX):] or "Original"
        return LANDSCAPE_16_9_FORMAT, resolution
    return ORIGINAL_FORMAT, choice


def _even(value: float | int) -> int:
    result = max(2, int(round(float(value))))
    return result - (result % 2)


def landscape_canvas_dimensions(
    source_info: dict[str, Any] | None,
    resolution: str = "Original",
) -> tuple[int, int]:
    """Calcula um quadro horizontal 16:9 sem ampliar/cortar por padrão.

    Em Original, o maior lado do primeiro vídeo define a largura do quadro,
    limitado a 1920 px, e o conteúdo é encaixado com preservação de proporção.
    Nas opções 360p–1080p, a altura do quadro segue a resolução escolhida.
    O worker aplica scale+pad, portanto não deforma nem elimina conteúdo.
    """
    info = source_info or {}
    try:
        source_w = max(2, int(info.get("width") or 1280))
    except (TypeError, ValueError):
        source_w = 1280
    try:
        source_h = max(2, int(info.get("height") or 720))
    except (TypeError, ValueError):
        source_h = 720

    label = str(resolution or "Original").strip()
    if label == "Original":
        long_side = min(1920, max(source_w, source_h))
        width = _even(long_side)
        height = _even(width * 9 / 16)
        return width, height

    target_height = _FIXED_LANDSCAPE_HEIGHTS.get(label, 720)
    height = _even(target_height)
    width = _even(height * 16 / 9)
    if width > 1920:
        scale = 1920 / float(width)
        width = _even(width * scale)
        height = _even(height * scale)
    return width, height
