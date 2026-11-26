from __future__ import annotations

"""Motor de acabamento avançado e enquadramento focal do Estúdio V165.

A renderização sempre parte do PNG original e das configurações V164/V165.
Assim, alterar um ajuste não reaplica filtros sobre uma imagem já degradada.
O módulo não depende de Qt e pode ser testado com Pillow isoladamente.
"""

import base64
from io import BytesIO
import math

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps

from monitor_noticias.ui.art_studio_image_engine_v164 import (
    CROP_RATIOS,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_SOURCE_BYTES,
    normalize_image_edit_config,
    render_image_source,
)

DEFAULT_ADVANCED_IMAGE_CONFIG = {
    "temperature": 0.0,
    "tint": 0.0,
    "highlights": 0.0,
    "shadows": 0.0,
    "vignette": 0.0,
    "fade": 0.0,
    "crop_zoom": 1.0,
    "focus_x": 50.0,
    "focus_y": 50.0,
    "rotation": 0,
    "flip_h": False,
    "flip_v": False,
}


def _number(value, default: float, low: float, high: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(result):
        return default
    return max(low, min(high, result))


def _as_bool(value, default: bool = False) -> bool:
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


def normalize_advanced_image_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    result = dict(DEFAULT_ADVANCED_IMAGE_CONFIG)
    for key in ("temperature", "tint", "highlights", "shadows"):
        result[key] = _number(source.get(key), 0.0, -100.0, 100.0)
    for key in ("vignette", "fade"):
        result[key] = _number(source.get(key), 0.0, 0.0, 100.0)
    result["crop_zoom"] = _number(source.get("crop_zoom"), 1.0, 1.0, 3.0)
    result["focus_x"] = _number(source.get("focus_x"), 50.0, 0.0, 100.0)
    result["focus_y"] = _number(source.get("focus_y"), 50.0, 0.0, 100.0)
    try:
        rotation = int(source.get("rotation", 0))
    except (TypeError, ValueError, OverflowError):
        rotation = 0
    result["rotation"] = rotation if rotation in {0, 90, 180, 270} else 0
    result["flip_h"] = _as_bool(source.get("flip_h", False))
    result["flip_v"] = _as_bool(source.get("flip_v", False))
    return result


def _decode_source(source_b64: str) -> Image.Image:
    try:
        raw = base64.b64decode(source_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("A imagem original armazenada está inválida.") from exc
    if not raw or len(raw) > MAX_IMAGE_SOURCE_BYTES:
        raise ValueError("A imagem original excede o limite permitido para edição.")
    try:
        with Image.open(BytesIO(raw)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("A imagem ultrapassa o limite de 25 milhões de pixels.")
            opened.load()
            return opened.convert("RGBA")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Não foi possível ler a imagem original para o enquadramento.") from exc


def _encode_source(image: Image.Image) -> str:
    output = BytesIO()
    image.save(output, format="PNG", optimize=False)
    raw = output.getvalue()
    if not raw or len(raw) > MAX_IMAGE_SOURCE_BYTES:
        raise ValueError("O enquadramento temporário excede o limite de 20 MB.")
    return base64.b64encode(raw).decode("ascii")


def _focal_crop(image: Image.Image, ratio: float | None, config: dict) -> Image.Image:
    width, height = image.size
    target_ratio = ratio if ratio and ratio > 0 else width / max(1, height)
    current_ratio = width / max(1, height)

    if current_ratio > target_ratio:
        base_height = float(height)
        base_width = base_height * target_ratio
    else:
        base_width = float(width)
        base_height = base_width / target_ratio

    zoom = float(config["crop_zoom"])
    crop_width = max(1, min(width, round(base_width / zoom)))
    crop_height = max(1, min(height, round(base_height / zoom)))
    remaining_x = max(0, width - crop_width)
    remaining_y = max(0, height - crop_height)
    left = round(remaining_x * float(config["focus_x"]) / 100.0)
    top = round(remaining_y * float(config["focus_y"]) / 100.0)
    left = max(0, min(remaining_x, left))
    top = max(0, min(remaining_y, top))
    return image.crop((left, top, left + crop_width, top + crop_height))


def _blend_tone(rgb: Image.Image, color: str, strength: float) -> Image.Image:
    if strength <= 0:
        return rgb
    overlay = Image.new("RGB", rgb.size, color)
    return Image.blend(rgb, overlay, max(0.0, min(0.28, strength)))


def _apply_temperature_and_tint(rgb: Image.Image, config: dict) -> Image.Image:
    temperature = float(config["temperature"])
    if temperature > 0:
        rgb = _blend_tone(rgb, "#FF9B55", temperature / 360.0)
    elif temperature < 0:
        rgb = _blend_tone(rgb, "#599AD4", abs(temperature) / 360.0)

    tint = float(config["tint"])
    if tint > 0:
        rgb = _blend_tone(rgb, "#D982B8", tint / 420.0)
    elif tint < 0:
        rgb = _blend_tone(rgb, "#65B78A", abs(tint) / 420.0)
    return rgb


def _apply_tonal_range(rgb: Image.Image, amount: float, *, highlights: bool) -> Image.Image:
    if abs(amount) < 0.01:
        return rgb
    luminance = ImageOps.grayscale(rgb)
    if highlights:
        mask = luminance.point(lambda value: max(0, min(255, round((value - 72) * 255 / 183))))
    else:
        mask = luminance.point(lambda value: max(0, min(255, round((184 - value) * 255 / 184))))
    mask = mask.filter(ImageFilterBoxBlur(1.2))
    factor = 1.0 + (amount / 100.0) * (0.62 if highlights else 0.72)
    adjusted = ImageEnhance.Brightness(rgb).enhance(max(0.25, min(1.7, factor)))
    return Image.composite(adjusted, rgb, mask)


def ImageFilterBoxBlur(radius: float):
    # Helper local para manter o conjunto de filtros explicitamente limitado.
    from PIL import ImageFilter
    return ImageFilter.GaussianBlur(radius=max(0.0, float(radius)))


def _radial_vignette_mask(size: tuple[int, int]) -> Image.Image:
    width, height = size
    small_w = 160
    small_h = max(1, round(small_w * height / max(1, width)))
    pixels = bytearray(small_w * small_h)
    for y in range(small_h):
        ny = (2.0 * y / max(1, small_h - 1)) - 1.0
        for x in range(small_w):
            nx = (2.0 * x / max(1, small_w - 1)) - 1.0
            distance = math.sqrt(nx * nx + ny * ny)
            edge = max(0.0, min(1.0, (distance - 0.28) / 0.78))
            pixels[y * small_w + x] = round(edge * 255)
    mask = Image.frombytes("L", (small_w, small_h), bytes(pixels))
    return mask.resize((width, height), Image.Resampling.BICUBIC)


def _apply_vignette(rgb: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return rgb
    mask = _radial_vignette_mask(rgb.size)
    mask = mask.point(lambda value: round(value * amount / 100.0))
    darkened = ImageEnhance.Brightness(rgb).enhance(0.48)
    return Image.composite(darkened, rgb, mask)


def _apply_fade(rgb: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return rgb
    neutral = Image.new("RGB", rgb.size, (128, 128, 128))
    return Image.blend(rgb, neutral, amount / 100.0 * 0.22)


def _apply_advanced_finish(image: Image.Image, config: dict) -> Image.Image:
    alpha = image.getchannel("A")
    rgb = Image.merge("RGB", image.split()[:3])
    rgb = _apply_temperature_and_tint(rgb, config)
    rgb = _apply_tonal_range(rgb, float(config["highlights"]), highlights=True)
    rgb = _apply_tonal_range(rgb, float(config["shadows"]), highlights=False)
    rgb = _apply_vignette(rgb, float(config["vignette"]))
    rgb = _apply_fade(rgb, float(config["fade"]))
    image = rgb.convert("RGBA")
    image.putalpha(alpha)

    rotation = int(config["rotation"])
    if rotation == 90:
        image = image.transpose(Image.Transpose.ROTATE_270)
    elif rotation == 180:
        image = image.transpose(Image.Transpose.ROTATE_180)
    elif rotation == 270:
        image = image.transpose(Image.Transpose.ROTATE_90)
    if config["flip_h"]:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if config["flip_v"]:
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image


def render_image_source_v165(source_b64: str, base_config_value, advanced_config_value) -> bytes:
    """Renderiza os ajustes V164 e V165 sempre a partir da fonte original."""
    base_config = normalize_image_edit_config(base_config_value)
    advanced_config = normalize_advanced_image_config(advanced_config_value)
    source = _decode_source(source_b64)

    # O recorte focal é calculado antes dos efeitos V164, para que zoom e ponto
    # focal também sejam aplicados corretamente às máscaras e bordas existentes.
    ratio = 1.0 if base_config["mask"] == "circle" else CROP_RATIOS[base_config["crop"]]
    zoom = float(advanced_config["crop_zoom"])
    needs_crop = ratio is not None or zoom > 1.0001
    if needs_crop:
        source = _focal_crop(source, ratio, advanced_config)
        working_source = _encode_source(source)
        render_config = dict(base_config)
        render_config["crop"] = "original"
    else:
        working_source = source_b64
        render_config = base_config

    base_render = render_image_source(working_source, render_config)
    try:
        with Image.open(BytesIO(base_render)) as opened:
            opened.load()
            result = opened.convert("RGBA")
    except OSError as exc:
        raise ValueError("A renderização base da imagem ficou inválida.") from exc

    result = _apply_advanced_finish(result, advanced_config)
    output = BytesIO()
    result.save(output, format="PNG", optimize=False)
    raw = output.getvalue()
    if not raw or len(raw) > MAX_IMAGE_SOURCE_BYTES * 2:
        raise ValueError("A imagem final ultrapassou o limite de armazenamento permitido.")
    return raw
