from __future__ import annotations

"""Motor de recorte de fundo por cor para o Estúdio de Artes V166.

A remoção parte de um dos cantos da imagem e alcança somente pixels conectados
com cor semelhante. Não é segmentação por IA: funciona melhor em fundos
uniformes ou quase uniformes. O canal alfa original é preservado e a borda
pode receber suavização controlada.
"""

from io import BytesIO
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

MAX_IMAGE_PIXELS = 25_000_000
MAX_INPUT_BYTES = 40 * 1024 * 1024
VALID_CORNERS = {"top_left", "top_right", "bottom_left", "bottom_right"}


def _bounded_int(value, default: int, low: int, high: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(number):
        return default
    return max(low, min(high, int(round(number))))


def normalize_background_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    corner = str(source.get("corner", "top_left")).strip().lower()
    if corner not in VALID_CORNERS:
        corner = "top_left"
    return {
        "corner": corner,
        "tolerance": _bounded_int(source.get("tolerance", 38), 38, 0, 255),
        "softness": _bounded_int(source.get("softness", 2), 2, 0, 16),
    }


def _corner_point(corner: str, width: int, height: int) -> tuple[int, int]:
    return {
        "top_left": (0, 0),
        "top_right": (width - 1, 0),
        "bottom_left": (0, height - 1),
        "bottom_right": (width - 1, height - 1),
    }[corner]


def remove_background_by_corner_color(
    image_png: bytes,
    corner: str = "top_left",
    tolerance: int = 38,
    softness: int = 2,
) -> bytes:
    """Remove o fundo contíguo à área de amostra escolhida e devolve PNG RGBA."""
    if not isinstance(image_png, (bytes, bytearray, memoryview)):
        raise TypeError("A imagem precisa ser fornecida em bytes PNG.")
    raw = bytes(image_png)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("A imagem está vazia ou excede o limite de 40 MB.")

    config = normalize_background_config({
        "corner": corner,
        "tolerance": tolerance,
        "softness": softness,
    })
    try:
        with Image.open(BytesIO(raw)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("A imagem ultrapassa o limite de 25 milhões de pixels.")
            opened.load()
            source = opened.convert("RGBA")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Não foi possível abrir a imagem para remover o fundo.") from exc

    width, height = source.size
    if width < 2 or height < 2:
        raise ValueError("A imagem precisa ter pelo menos 2 × 2 pixels.")

    # Torna a cópia de trabalho totalmente opaca para que o alfa 0 seja um
    # marcador impossível de confundir com qualquer pixel original.
    rgb = source.convert("RGB")
    working = Image.merge("RGBA", (*rgb.split(), Image.new("L", source.size, 255)))
    marker = (0, 0, 0, 0)
    seed = _corner_point(config["corner"], width, height)
    ImageDraw.floodfill(
        working,
        seed,
        marker,
        thresh=config["tolerance"],
    )

    removed = working.getchannel("A").point(lambda value: 255 if value == 0 else 0)
    if removed.getbbox() is None:
        return raw

    softness = config["softness"]
    if softness:
        # Pequena expansão antes do desfoque reduz halos coloridos na borda.
        kernel = softness * 2 + 1
        removed = removed.filter(ImageFilter.MaxFilter(kernel))
        removed = removed.filter(ImageFilter.GaussianBlur(radius=max(0.5, softness * 0.65)))

    remaining = ImageOps.invert(removed)
    original_alpha = source.getchannel("A")
    final_alpha = ImageChops.multiply(original_alpha, remaining)
    source.putalpha(final_alpha)

    output = BytesIO()
    source.save(output, format="PNG", optimize=False)
    result = output.getvalue()
    if not result or len(result) > MAX_INPUT_BYTES:
        raise ValueError("A imagem processada excedeu o limite de armazenamento.")
    return result
