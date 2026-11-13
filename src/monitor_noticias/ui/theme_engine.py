from __future__ import annotations

"""Transformação de cores QSS para os temas Claro e Escuro da Central.

O mecanismo adapta as folhas de estilo que já pertencem às páginas e aos
controles. Assim, não depende apenas de uma camada global que poderia perder
para estilos locais definidos pelos próprios módulos.
"""

import colorsys
import re

from monitor_noticias.ui.theme_store import THEME_CLARO, THEME_ESCURO, normalize_theme

_COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*(?:\d*\.?\d+))?\s*\)|\b(?:white|black)\b",
    re.IGNORECASE,
)
_BLOCK_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}")
_DECL_RE = re.compile(r"(?P<prop>[\w-]+\s*:\s*)(?P<value>[^;{}]*)(?P<end>;?)")

# Delegates que desenham os próprios cartões com QPainter e, portanto, não
# recebem as cores do QSS global.
THEME_AWARE_DELEGATE_NAMES = frozenset({
    "NewsDelegate",
    "HistoryDelegate",
    "SourceDelegate",
})

# Os seletores abaixo representam conteúdo, não a moldura da aplicação.
# A aparência de uma página, imagem ou vídeo aberto deve permanecer fiel.
_PRESERVE_OBJECT_NAMES = frozenset({
    "pdfPreview", "pdfPagePreview", "pdfCoverPreview", "coverPreview", "imagePreview",
    "videoPreview", "videoCanvas", "previewCanvas", "mediaPreview",
})


def _rgb(token: str) -> tuple[int, int, int, str] | None:
    value = token.strip()
    lower = value.lower()
    if lower == "white":
        return 255, 255, 255, "hex"
    if lower == "black":
        return 0, 0, 0, "hex"
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        if len(raw) not in (6, 8):
            return None
        try:
            return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), "hex"
        except ValueError:
            return None
    match = re.fullmatch(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*(\d*\.?\d+))?\s*\)",
        value,
        re.IGNORECASE,
    )
    if match:
        return (
            max(0, min(255, int(match.group(1)))),
            max(0, min(255, int(match.group(2)))),
            max(0, min(255, int(match.group(3)))),
            "rgba:" + (match.group(4) or ""),
        )
    return None


def _luminance(rgb: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        c = value / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*(value / 255.0 for value in rgb))


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _surface(selector: str, theme: str) -> str:
    lowered = selector.casefold()
    if theme == THEME_ESCURO:
        if "#root" in lowered or "qmainwindow" in lowered:
            return "#0D1926"
        if "sidebar" in lowered:
            return "#071D31"
        if any(name in lowered for name in ("qlineedit", "qcombobox", "qspinbox", "qdateedit", "qtimeedit")):
            return "#1A2B3B"
        if "qmenu" in lowered or "qtooltip" in lowered:
            return "#17293A"
        return "#152637"
    if "sidebarstatuscard" in lowered or "appearancecard" in lowered:
        return "#FFFFFF"
    if 'sidebarnavitem[active="true"]' in lowered:
        return "#E2ECF4"
    if "sidebarnavitem:hover" in lowered:
        return "#EAF1F6"
    if "sidebarnaviconwrap" in lowered:
        return "#E9EFF4"
    if "sidebar" in lowered:
        return "#F3F6FA"
    if any(name in lowered for name in ("qlineedit", "qcombobox", "qspinbox", "qdateedit", "qtimeedit")):
        return "#FFFFFF"
    if "#root" in lowered or "qmainwindow" in lowered:
        return "#F4F7FA"
    return "#FFFFFF"


def _as_rgb(value: str) -> tuple[int, int, int] | None:
    parsed = _rgb(value)
    return parsed[:3] if parsed else None


def _has_action_background(value: str) -> bool:
    """True para fundos de ação saturados, como botões azuis/verde/dourado."""
    for match in _COLOR_RE.finditer(value):
        rgb = _as_rgb(match.group(0))
        if rgb is None:
            continue
        _h, saturation, _v = _hsv(rgb)
        lum = _luminance(rgb)
        if saturation >= 0.42 and 0.07 <= lum <= 0.48:
            return True
    return False


def _transform_rgb(
    rgb: tuple[int, int, int],
    prop: str,
    theme: str,
    selector: str,
    action_background: bool,
) -> tuple[int, int, int]:
    r, g, b = rgb
    lum = _luminance(rgb)
    hue, saturation, value = _hsv(rgb)
    lowered_selector = selector.casefold()
    lowered_prop = prop.casefold()

    # As amostras de tema devem continuar exibindo a própria paleta escolhida.
    if "#themechoice" in lowered_selector:
        return rgb

    is_background = lowered_prop in {"background", "background-color", "selection-background-color", "alternate-background-color"}
    is_text = lowered_prop == "color"
    is_border = any(word in lowered_prop for word in ("border", "outline", "gridline"))

    if is_background:
        if theme == THEME_ESCURO:
            # Pastéis de status recebem versões escuras e discretas.
            if saturation >= 0.16 and lum >= 0.72:
                return tuple(round(v * 255) for v in colorsys.hsv_to_rgb(hue, min(0.58, max(0.34, saturation)), 0.29))
            if saturation < 0.24 and lum >= 0.72:
                surface = _as_rgb(_surface(selector, theme))
                return surface or rgb
            if saturation < 0.24 and lum >= 0.48:
                return (34, 53, 71)
            if saturation < 0.22 and lum <= 0.045:
                return (25, 43, 59)
            return rgb

        # No Claro, fundos estruturais escuros tornam-se superfícies claras.
        if "sidebar" in lowered_selector:
            if lum < 0.36:
                surface = _as_rgb(_surface(selector, theme))
                return surface or rgb
        if saturation < 0.24 and lum <= 0.20:
            surface = _as_rgb(_surface(selector, theme))
            return surface or rgb
        if saturation < 0.20 and 0.20 < lum <= 0.35:
            return (231, 237, 243)
        return rgb

    if is_text:
        if theme == THEME_ESCURO:
            if action_background and lum >= 0.72 and saturation < 0.22:
                return rgb  # mantém texto branco em botões de ação.
            if saturation < 0.24 and lum <= 0.32:
                return (229, 237, 244)
            if saturation < 0.24 and 0.32 < lum <= 0.60:
                return (171, 190, 205)
            if saturation >= 0.28 and lum <= 0.36 and value <= 0.74:
                return tuple(round(v * 255) for v in colorsys.hsv_to_rgb(hue, min(saturation, 0.42), 0.88))
            return rgb

        if action_background and lum >= 0.72 and saturation < 0.22:
            return rgb  # mantém texto branco em botões de ação.
        if saturation < 0.24 and lum >= 0.78:
            return (29, 53, 72)
        if saturation < 0.24 and 0.56 <= lum < 0.78:
            return (91, 115, 134)
        return rgb

    if is_border:
        if theme == THEME_ESCURO:
            if (saturation < 0.25 and lum >= 0.46) or lum < 0.10:
                return (54, 74, 93)
        else:
            if lum <= 0.16:
                return (202, 215, 226)
            if saturation < 0.25 and lum <= 0.42:
                return (214, 224, 233)
        return rgb

    return rgb


def _replace_color(match: re.Match[str], prop: str, theme: str, selector: str, action_background: bool) -> str:
    token = match.group(0)
    parsed = _rgb(token)
    if parsed is None:
        return token
    r, g, b, format_hint = parsed
    transformed = _transform_rgb((r, g, b), prop, theme, selector, action_background)
    if transformed == (r, g, b):
        return token
    if format_hint.startswith("rgba:"):
        alpha = format_hint.split(":", 1)[1]
        return f"rgba({transformed[0]}, {transformed[1]}, {transformed[2]}, {alpha or '1'})"
    return _hex(transformed)


def _transform_body(body: str, selector: str, theme: str) -> str:
    declarations = list(_DECL_RE.finditer(body))
    background_values = [
        match.group("value")
        for match in declarations
        if match.group("prop").split(":", 1)[0].strip().casefold() in {"background", "background-color", "alternate-background-color"}
    ]
    action_background = any(_has_action_background(value) for value in background_values)

    parts: list[str] = []
    cursor = 0
    for match in declarations:
        parts.append(body[cursor:match.start()])
        prop = match.group("prop").split(":", 1)[0].strip().casefold()
        value = _COLOR_RE.sub(
            lambda color_match: _replace_color(color_match, prop, theme, selector, action_background),
            match.group("value"),
        )
        parts.append(match.group("prop") + value + match.group("end"))
        cursor = match.end()
    parts.append(body[cursor:])
    return "".join(parts)


def transform_painter_color(value: str, usage: str, theme_id: str) -> str:
    """Adapta cores usadas por delegates que desenham itens com QPainter.

    Esses desenhos não passam pelo QSS; por isso precisam da mesma paleta
    escura aplicada às folhas de estilo das páginas.
    """
    selected = normalize_theme(theme_id)
    parsed = _rgb(str(value))
    if parsed is None or selected != THEME_ESCURO:
        return str(value)

    red, green, blue, _format_hint = parsed
    rgb = (red, green, blue)
    hue, saturation, brightness = _hsv(rgb)
    luminance = _luminance(rgb)

    if usage == "fill":
        # Superfícies brancas ou pastéis tornam-se azul-marinho profundo.
        if luminance >= 0.46:
            if saturation >= 0.12:
                dark_rgb = colorsys.hsv_to_rgb(
                    hue, min(0.58, max(0.28, saturation)), 0.25
                )
                return _hex(tuple(channel * 255 for channel in dark_rgb))
            return "#192D40"
        if saturation < 0.20 and luminance <= 0.05:
            return "#192D40"
        return str(value)

    if usage == "text":
        # Texto azul-marinho/cinza escuro precisa clarear para manter contraste.
        if luminance < 0.48:
            if saturation < 0.18:
                return "#E5EDF4"
            light_rgb = colorsys.hsv_to_rgb(
                hue, min(0.72, max(0.42, saturation)), max(0.86, brightness)
            )
            return _hex(tuple(channel * 255 for channel in light_rgb))
        return str(value)

    return str(value)


def transform_stylesheet(stylesheet: str, theme_id: str, object_name: str = "") -> str:
    """Converte cores de uma folha QSS sem mexer em geometria, textos ou ações."""
    source = str(stylesheet or "")
    selected = normalize_theme(theme_id)
    if not source.strip():
        return source
    if object_name in _PRESERVE_OBJECT_NAMES:
        return source

    if "{" not in source or "}" not in source:
        return _transform_body(source, f"QWidget#{object_name}" if object_name else "QWidget", selected)

    output: list[str] = []
    cursor = 0
    for match in _BLOCK_RE.finditer(source):
        output.append(source[cursor:match.start()])
        selector = match.group("selector")
        body = _transform_body(match.group("body"), selector, selected)
        output.append(selector + "{" + body + "}")
        cursor = match.end()
    output.append(source[cursor:])
    return "".join(output)
