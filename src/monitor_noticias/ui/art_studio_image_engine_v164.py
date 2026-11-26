from __future__ import annotations

"""Motor independente de processamento de imagem usado pelo Estúdio V164.

Não depende de Qt. Mantém a fonte em PNG e sempre renderiza efeitos a partir
dela, permitindo alterar ou remover os ajustes sem degradar a imagem original.
"""

import base64
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

MAX_IMAGE_SOURCE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000

DEFAULT_IMAGE_EDIT_CONFIG = {
    "preset": "original",
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "sharpness": 1.0,
    "blur": 0.0,
    "crop": "original",
    "mask": "none",
    "border_width": 0,
    "border_color": "#FFFFFF",
}

IMAGE_EDIT_PRESETS = {
    "original": "Original",
    "vivid": "Vívido",
    "mono": "Preto e branco",
    "sepia": "Sépia",
    "cool": "Frio",
    "warm": "Quente",
    "cinematic": "Cinema",
}

CROP_RATIOS = {
    "original": None,
    "1:1": 1.0,
    "4:5": 4.0 / 5.0,
    "16:9": 16.0 / 9.0,
    "3:2": 3.0 / 2.0,
    "9:16": 9.0 / 16.0,
}

MASKS = {"none", "rounded", "circle", "hexagon", "arch"}
BORDER_COLORS = {
    "#FFFFFF", "#D6B66D", "#102A43", "#000000", "#3AAFA9", "#8C2735"
}


def _bounded_float(value, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not (number == number and abs(number) != float("inf")):
        return default
    return max(low, min(high, number))


def normalize_image_edit_config(value) -> dict:
    source = value if isinstance(value, dict) else {}
    config = dict(DEFAULT_IMAGE_EDIT_CONFIG)
    preset = str(source.get("preset", "original"))
    config["preset"] = preset if preset in IMAGE_EDIT_PRESETS else "original"
    config["brightness"] = _bounded_float(source.get("brightness"), 1.0, 0.2, 2.5)
    config["contrast"] = _bounded_float(source.get("contrast"), 1.0, 0.0, 3.0)
    config["saturation"] = _bounded_float(source.get("saturation"), 1.0, 0.0, 3.0)
    config["sharpness"] = _bounded_float(source.get("sharpness"), 1.0, 0.0, 3.0)
    config["blur"] = _bounded_float(source.get("blur"), 0.0, 0.0, 15.0)
    crop = str(source.get("crop", "original"))
    config["crop"] = crop if crop in CROP_RATIOS else "original"
    mask = str(source.get("mask", "none"))
    config["mask"] = mask if mask in MASKS else "none"
    try:
        border_width = int(source.get("border_width", 0))
    except (TypeError, ValueError, OverflowError):
        border_width = 0
    config["border_width"] = max(0, min(32, border_width))
    border_color = str(source.get("border_color", "#FFFFFF")).upper()
    config["border_color"] = border_color if border_color in BORDER_COLORS else "#FFFFFF"
    return config


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
        raise ValueError("Não foi possível ler a imagem original para aplicar os ajustes.") from exc


def _center_crop(image: Image.Image, ratio: float | None) -> Image.Image:
    if ratio is None or ratio <= 0:
        return image
    width, height = image.size
    current = width / max(1, height)
    if abs(current - ratio) < 0.0001:
        return image
    if current > ratio:
        new_width = max(1, min(width, round(height * ratio)))
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = max(1, min(height, round(width / ratio)))
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def _apply_preset(rgb: Image.Image, preset: str) -> Image.Image:
    if preset == "mono":
        return ImageOps.grayscale(rgb).convert("RGB")
    if preset == "sepia":
        gray = ImageOps.grayscale(rgb)
        return ImageOps.colorize(gray, black="#24180F", white="#F1D9AA").convert("RGB")
    if preset == "cool":
        tinted = Image.blend(rgb, Image.new("RGB", rgb.size, "#477FA8"), 0.10)
        return ImageEnhance.Contrast(tinted).enhance(1.08)
    if preset == "warm":
        tinted = Image.blend(rgb, Image.new("RGB", rgb.size, "#D98A45"), 0.10)
        return ImageEnhance.Color(tinted).enhance(1.05)
    if preset == "vivid":
        rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
        rgb = ImageEnhance.Color(rgb).enhance(1.22)
        return ImageEnhance.Sharpness(rgb).enhance(1.12)
    if preset == "cinematic":
        rgb = ImageEnhance.Brightness(rgb).enhance(0.96)
        rgb = ImageEnhance.Contrast(rgb).enhance(1.18)
        rgb = ImageEnhance.Color(rgb).enhance(0.82)
        return Image.blend(rgb, Image.new("RGB", rgb.size, "#17364D"), 0.045)
    return rgb


def _mask_image(image: Image.Image, mask_name: str) -> Image.Image:
    if mask_name == "none":
        return image
    width, height = image.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    minimum = max(1, min(width, height))
    if mask_name == "rounded":
        radius = max(1, round(minimum * 0.12))
        draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    elif mask_name == "circle":
        image = _center_crop(image, 1.0)
        width, height = image.size
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, width - 1, height - 1), fill=255)
    elif mask_name == "hexagon":
        inset_x = round(width * 0.18)
        draw.polygon(
            (
                (inset_x, 0), (width - 1 - inset_x, 0), (width - 1, height // 2),
                (width - 1 - inset_x, height - 1), (inset_x, height - 1), (0, height // 2),
            ),
            fill=255,
        )
    elif mask_name == "arch":
        draw.rectangle((0, height // 2, width - 1, height - 1), fill=255)
        draw.ellipse((0, 0, width - 1, height - 1), fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    return image


def _add_border(image: Image.Image, config: dict) -> Image.Image:
    width = int(config.get("border_width", 0))
    if width <= 0:
        return image
    width = min(width, max(1, min(image.size) // 5))
    color = str(config.get("border_color", "#FFFFFF"))
    draw = ImageDraw.Draw(image)
    w, h = image.size
    inset = max(0, width // 2)
    bounds = (inset, inset, max(inset, w - 1 - inset), max(inset, h - 1 - inset))
    mask_name = str(config.get("mask", "none"))
    if mask_name == "rounded":
        draw.rounded_rectangle(bounds, radius=max(1, min(w, h) // 9), outline=color, width=width)
    elif mask_name == "circle":
        draw.ellipse(bounds, outline=color, width=width)
    elif mask_name == "arch":
        mid = h // 2
        draw.arc(bounds, 180, 360, fill=color, width=width)
        draw.line((inset, mid, inset, h - 1 - inset), fill=color, width=width)
        draw.line((w - 1 - inset, mid, w - 1 - inset, h - 1 - inset), fill=color, width=width)
        draw.line((inset, h - 1 - inset, w - 1 - inset, h - 1 - inset), fill=color, width=width)
    elif mask_name == "hexagon":
        x = round(w * 0.18)
        draw.line(
            ((x, inset), (w - 1 - x, inset), (w - 1 - inset, h // 2),
             (w - 1 - x, h - 1 - inset), (x, h - 1 - inset), (inset, h // 2), (x, inset)),
            fill=color, width=width, joint="curve",
        )
    else:
        draw.rectangle(bounds, outline=color, width=width)
    return image


def render_image_source(source_b64: str, config_value) -> bytes:
    config = normalize_image_edit_config(config_value)
    image = _decode_source(source_b64)
    if config["mask"] == "circle":
        image = _center_crop(image, 1.0)
    else:
        image = _center_crop(image, CROP_RATIOS[config["crop"]])

    alpha = image.getchannel("A")
    rgb = Image.merge("RGB", image.split()[:3])
    rgb = _apply_preset(rgb, config["preset"])
    rgb = ImageEnhance.Brightness(rgb).enhance(config["brightness"])
    rgb = ImageEnhance.Contrast(rgb).enhance(config["contrast"])
    rgb = ImageEnhance.Color(rgb).enhance(config["saturation"])
    rgb = ImageEnhance.Sharpness(rgb).enhance(config["sharpness"])
    if config["blur"] > 0:
        rgb = rgb.filter(ImageFilter.GaussianBlur(radius=config["blur"]))
    rendered = rgb.convert("RGBA")
    if rendered.size == alpha.size:
        rendered.putalpha(alpha)
    rendered = _mask_image(rendered, config["mask"])
    rendered = _add_border(rendered, config)
    output = BytesIO()
    rendered.save(output, format="PNG", optimize=False)
    raw = output.getvalue()
    if not raw or len(raw) > MAX_IMAGE_SOURCE_BYTES * 2:
        raise ValueError("A imagem editada ultrapassou o limite de armazenamento permitido.")
    return raw


def encode_image_source(raw: bytes) -> str:
    if not raw or len(raw) > MAX_IMAGE_SOURCE_BYTES:
        raise ValueError("A imagem excede o limite de 20 MB para edição não destrutiva.")
    return base64.b64encode(raw).decode("ascii")
