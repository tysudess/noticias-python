from __future__ import annotations

"""V164 — laboratório de imagem não destrutivo.

Adiciona filtros fotográficos, enquadramento por proporção, máscaras e bordas
editáveis. A imagem original e os parâmetros são incorporados aos dados do
objeto já serializados pelo Estúdio; a renderização visível continua sendo um
QGraphicsPixmapItem, inclusive dentro de grupos. Projetos antigos continuam
abrindo sem migração e sem alteração do formato .centralart.
"""

import base64
import json
import logging
from PySide6.QtCore import QBuffer, QIODevice, QPointF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsPixmapItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_image_engine_v164 import (
    IMAGE_EDIT_PRESETS,
    encode_image_source,
    normalize_image_edit_config,
    render_image_source,
)
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import FRAME_DATA_KEY, _apply_frame
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave

log = logging.getLogger(__name__)

ORIGINAL_IMAGE_DATA_KEY = 164
IMAGE_EDIT_CONFIG_DATA_KEY = 165


def _config_from_item(item: QGraphicsPixmapItem) -> dict:
    raw = item.data(IMAGE_EDIT_CONFIG_DATA_KEY)
    try:
        parsed = json.loads(str(raw)) if raw else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = {}
    return normalize_image_edit_config(parsed)


def _pixmap_to_png_bytes(pixmap: QPixmap) -> bytes:
    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Não foi possível preparar a imagem original.")
    try:
        if not pixmap.save(buffer, "PNG"):
            raise OSError("O Qt não conseguiu codificar a imagem original.")
        raw = bytes(buffer.data())
    finally:
        buffer.close()
    return raw


def _set_pixmap_preserving_center(item: QGraphicsPixmapItem, pixmap: QPixmap) -> None:
    old_center = item.mapToScene(item.boundingRect().center())
    parent = item.parentItem()
    item.setPixmap(pixmap)
    item.setTransformOriginPoint(item.boundingRect().center())
    new_center = item.mapToScene(item.boundingRect().center())
    delta = old_center - new_center
    if parent is None:
        item.moveBy(delta.x(), delta.y())
    else:
        origin = parent.mapFromScene(QPointF(0.0, 0.0))
        target = parent.mapFromScene(delta)
        item.moveBy(target.x() - origin.x(), target.y() - origin.y())
    frame = item.data(FRAME_DATA_KEY)
    if isinstance(frame, dict):
        _apply_frame(item, dict(frame))


def _pixmap_from_png(raw: bytes) -> QPixmap:
    pixmap = QPixmap()
    if not pixmap.loadFromData(raw, "PNG") or pixmap.isNull():
        raise ValueError("O Qt não conseguiu carregar a imagem processada.")
    return pixmap


def _install_image_serialization(page) -> None:
    if getattr(page, "_v164_image_serialization_installed", False):
        return
    base_serialize = getattr(page, "_v146_base_serialize", None)
    base_build = getattr(page, "_v146_base_build", None)
    if not callable(base_serialize) or not callable(base_build):
        return

    def serialize_with_image_edits(item):
        data = base_serialize(item)
        if isinstance(item, QGraphicsPixmapItem):
            original = item.data(ORIGINAL_IMAGE_DATA_KEY)
            config_raw = item.data(IMAGE_EDIT_CONFIG_DATA_KEY)
            if original and config_raw:
                try:
                    config = normalize_image_edit_config(json.loads(str(config_raw)))
                    data["v164_image_source_png_base64"] = str(original)
                    data["v164_image_edit_config"] = config
                except (TypeError, ValueError, json.JSONDecodeError):
                    log.warning("Metadados de edição da imagem inválidos; salvando a imagem visível.")
        return data

    def build_with_image_edits(data):
        item = base_build(data)
        if isinstance(item, QGraphicsPixmapItem):
            source = data.get("v164_image_source_png_base64")
            config = data.get("v164_image_edit_config")
            if source and isinstance(config, dict):
                try:
                    normalized = normalize_image_edit_config(config)
                    rendered = render_image_source(str(source), normalized)
                    item.setPixmap(_pixmap_from_png(rendered))
                    item.setData(ORIGINAL_IMAGE_DATA_KEY, str(source))
                    item.setData(IMAGE_EDIT_CONFIG_DATA_KEY, json.dumps(normalized, separators=(",", ":")))
                except Exception as exc:
                    # O PNG visível já está no projeto base. Uma falha nos metadados
                    # não deve impedir a abertura do restante do documento.
                    log.warning("Não foi possível reaplicar os ajustes V164: %s", exc)
        return item

    page._v146_base_serialize = serialize_with_image_edits
    page._v146_base_build = build_with_image_edits
    page._v164_base_serialize = base_serialize
    page._v164_base_build = base_build
    page._v164_image_serialization_installed = True


def _selected_image(page) -> QGraphicsPixmapItem | None:
    selected = list(page.scene.selectedItems())
    if len(selected) != 1 or not isinstance(selected[0], QGraphicsPixmapItem):
        return None
    item = selected[0]
    if item.scene() is not page.scene or not item.isVisible() or bool(item.data(LOCKED_KEY)):
        return None
    return item


def _sync_image_controls(page) -> None:
    item = _selected_image(page)
    panel = getattr(page, "v164_image_panel", None)
    if panel is None:
        return
    enabled = item is not None
    for control in getattr(page, "v164_image_controls", []):
        control.setEnabled(enabled)
    if getattr(page, "v164_restore_button", None) is not None:
        page.v164_restore_button.setEnabled(enabled and bool(item.data(ORIGINAL_IMAGE_DATA_KEY)))
    if item is None:
        page.v164_image_info.setText("Selecione uma imagem visível e desbloqueada no canvas.")
        return

    config = _config_from_item(item)
    controls = (
        (page.v164_filter_combo, "preset"),
        (page.v164_crop_combo, "crop"),
        (page.v164_mask_combo, "mask"),
        (page.v164_border_color_combo, "border_color"),
    )
    for combo, key in controls:
        combo.blockSignals(True)
        index = combo.findData(config[key])
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)
    spin_values = (
        (page.v164_brightness, config["brightness"]),
        (page.v164_contrast, config["contrast"]),
        (page.v164_saturation, config["saturation"]),
        (page.v164_sharpness, config["sharpness"]),
        (page.v164_blur, config["blur"]),
        (page.v164_border_width, config["border_width"]),
    )
    for spin, value in spin_values:
        spin.blockSignals(True)
        spin.setValue(value)
        spin.blockSignals(False)
    pixmap = item.pixmap()
    page.v164_image_info.setText(
        f"Imagem selecionada · {pixmap.width()} × {pixmap.height()} px · "
        f"{IMAGE_EDIT_PRESETS[config['preset']]} · máscara: {config['mask']}"
    )


def _read_ui_config(page) -> dict:
    return normalize_image_edit_config({
        "preset": page.v164_filter_combo.currentData(),
        "brightness": page.v164_brightness.value(),
        "contrast": page.v164_contrast.value(),
        "saturation": page.v164_saturation.value(),
        "sharpness": page.v164_sharpness.value(),
        "blur": page.v164_blur.value(),
        "crop": page.v164_crop_combo.currentData(),
        "mask": page.v164_mask_combo.currentData(),
        "border_width": page.v164_border_width.value(),
        "border_color": page.v164_border_color_combo.currentData(),
    })


def _commit_image_change(page, item: QGraphicsPixmapItem, source_b64: str, config: dict) -> None:
    rendered = render_image_source(source_b64, config)
    pixmap = _pixmap_from_png(rendered)
    _set_pixmap_preserving_center(item, pixmap)
    item.setData(ORIGINAL_IMAGE_DATA_KEY, source_b64)
    item.setData(IMAGE_EDIT_CONFIG_DATA_KEY, json.dumps(config, separators=(",", ":")))
    if hasattr(page, "_refresh_layers"):
        page._refresh_layers(select_item=item)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v148_update_dimensions"):
        page._v148_update_dimensions()
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()
    _schedule_autosave(page)
    _sync_image_controls(page)


def _apply_image_edits(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v164_image_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return
    try:
        source_b64 = item.data(ORIGINAL_IMAGE_DATA_KEY)
        if not source_b64:
            source_b64 = encode_image_source(_pixmap_to_png_bytes(item.pixmap()))
        config = _read_ui_config(page)
        _commit_image_change(page, item, str(source_b64), config)
        page.status_label.setText(
            "Ajustes aplicados sem perder a imagem original. Use Restaurar original para desfazer todos os efeitos."
        )
    except Exception as exc:
        log.exception("Falha ao aplicar ajustes não destrutivos na imagem")
        page.v164_image_info.setText(f"Não foi possível aplicar os ajustes: {exc}")
        page.status_label.setText(f"Ajuste de imagem não aplicado: {exc}")


def _restore_original_image(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v164_image_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return
    source_b64 = item.data(ORIGINAL_IMAGE_DATA_KEY)
    if not source_b64:
        page.v164_image_info.setText("Esta imagem ainda não possui ajustes V164 para restaurar.")
        return
    try:
        raw = base64.b64decode(str(source_b64), validate=True)
        pixmap = _pixmap_from_png(raw)
        _set_pixmap_preserving_center(item, pixmap)
        item.setData(ORIGINAL_IMAGE_DATA_KEY, None)
        item.setData(IMAGE_EDIT_CONFIG_DATA_KEY, None)
        if hasattr(page, "_refresh_layers"):
            page._refresh_layers(select_item=item)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        if hasattr(page, "_v148_update_dimensions"):
            page._v148_update_dimensions()
        page.scene.update()
        timer = getattr(page, "_v145_history_timer", None)
        if timer is not None and not getattr(page, "_v145_history_suspended", False):
            timer.start()
        _schedule_autosave(page)
        _sync_image_controls(page)
        page.status_label.setText("Imagem original restaurada; filtros, máscaras e bordas removidos.")
    except Exception as exc:
        log.exception("Falha ao restaurar imagem original")
        page.status_label.setText(f"Não foi possível restaurar a imagem: {exc}")


def _install_image_tools(page) -> None:
    if getattr(page, "_v164_image_panel_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if tabs is None:
        return

    image_page = QWidget(tabs)
    image_page.setObjectName("artStudioImageToolsPageV164")
    outer = QVBoxLayout(image_page)
    outer.setContentsMargins(4, 4, 4, 4)
    outer.setSpacing(6)

    scroll = QScrollArea(image_page)
    scroll.setObjectName("artStudioImageToolsScrollV164")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = QWidget(scroll)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(8, 8, 8, 10)
    layout.setSpacing(9)

    title = QLabel("LABORATÓRIO DE IMAGEM", content)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel(
        "Ajuste fotografia, enquadramento e acabamento. A imagem original é preservada para restauração.",
        content,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    layout.addWidget(title)
    layout.addWidget(hint)

    preset_panel = QFrame(content)
    preset_panel.setObjectName("artStudioImagePresetCardV164")
    preset_layout = QVBoxLayout(preset_panel)
    preset_layout.setContentsMargins(9, 9, 9, 9)
    preset_layout.setSpacing(6)
    preset_layout.addWidget(QLabel("FILTRO FOTOGRÁFICO", preset_panel))
    page.v164_filter_combo = QComboBox(preset_panel)
    for key, label in IMAGE_EDIT_PRESETS.items():
        page.v164_filter_combo.addItem(label, key)
    preset_layout.addWidget(page.v164_filter_combo)
    layout.addWidget(preset_panel)

    adjust_panel = QFrame(content)
    adjust_panel.setObjectName("artStudioImageAdjustCardV164")
    adjust_layout = QVBoxLayout(adjust_panel)
    adjust_layout.setContentsMargins(9, 9, 9, 9)
    adjust_layout.setSpacing(6)
    adjust_layout.addWidget(QLabel("AJUSTES FINOS", adjust_panel))
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(6)

    def make_spin(low: float, high: float, step: float, decimals: int, suffix: str):
        spin = QDoubleSpinBox(adjust_panel)
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setSuffix(suffix)
        spin.setValue(1.0 if suffix == "×" else 0.0)
        spin.setMinimumWidth(92)
        return spin

    page.v164_brightness = make_spin(0.2, 2.5, 0.05, 2, "×")
    page.v164_contrast = make_spin(0.0, 3.0, 0.05, 2, "×")
    page.v164_saturation = make_spin(0.0, 3.0, 0.05, 2, "×")
    page.v164_sharpness = make_spin(0.0, 3.0, 0.05, 2, "×")
    page.v164_blur = make_spin(0.0, 15.0, 0.5, 1, " px")
    form.addRow("Brilho", page.v164_brightness)
    form.addRow("Contraste", page.v164_contrast)
    form.addRow("Saturação", page.v164_saturation)
    form.addRow("Nitidez", page.v164_sharpness)
    form.addRow("Desfoque", page.v164_blur)
    adjust_layout.addLayout(form)
    layout.addWidget(adjust_panel)

    framing_panel = QFrame(content)
    framing_panel.setObjectName("artStudioImageFramingCardV164")
    framing_layout = QVBoxLayout(framing_panel)
    framing_layout.setContentsMargins(9, 9, 9, 9)
    framing_layout.setSpacing(6)
    framing_layout.addWidget(QLabel("ENQUADRAMENTO E MÁSCARA", framing_panel))
    page.v164_crop_combo = QComboBox(framing_panel)
    for key, label in (
        ("original", "Proporção original"), ("1:1", "Quadrado · 1:1"),
        ("4:5", "Retrato · 4:5"), ("16:9", "Paisagem · 16:9"),
        ("3:2", "Fotografia · 3:2"), ("9:16", "Story · 9:16"),
    ):
        page.v164_crop_combo.addItem(label, key)
    page.v164_mask_combo = QComboBox(framing_panel)
    for key, label in (
        ("none", "Sem máscara"), ("rounded", "Cantos arredondados"),
        ("circle", "Círculo"), ("hexagon", "Hexágono"), ("arch", "Arco"),
    ):
        page.v164_mask_combo.addItem(label, key)
    framing_layout.addWidget(QLabel("Proporção de corte", framing_panel))
    framing_layout.addWidget(page.v164_crop_combo)
    framing_layout.addWidget(QLabel("Formato da máscara", framing_panel))
    framing_layout.addWidget(page.v164_mask_combo)
    layout.addWidget(framing_panel)

    border_panel = QFrame(content)
    border_panel.setObjectName("artStudioImageBorderCardV164")
    border_layout = QVBoxLayout(border_panel)
    border_layout.setContentsMargins(9, 9, 9, 9)
    border_layout.setSpacing(6)
    border_layout.addWidget(QLabel("BORDA DA IMAGEM", border_panel))
    border_form = QFormLayout()
    border_form.setContentsMargins(0, 0, 0, 0)
    page.v164_border_width = QSpinBox(border_panel)
    page.v164_border_width.setRange(0, 32)
    page.v164_border_width.setSuffix(" px")
    page.v164_border_width.setValue(0)
    page.v164_border_color_combo = QComboBox(border_panel)
    for color, label in (
        ("#FFFFFF", "Branco"), ("#D6B66D", "Dourado"), ("#102A43", "Marinho"),
        ("#000000", "Preto"), ("#3AAFA9", "Turquesa"), ("#8C2735", "Vermelho"),
    ):
        page.v164_border_color_combo.addItem(label, color)
    border_form.addRow("Espessura", page.v164_border_width)
    border_form.addRow("Cor", page.v164_border_color_combo)
    border_layout.addLayout(border_form)
    layout.addWidget(border_panel)

    actions = QHBoxLayout()
    page.v164_apply_button = QPushButton("Aplicar ajustes", content)
    page.v164_apply_button.setProperty("gold", True)
    page.v164_restore_button = QPushButton("Restaurar original", content)
    page.v164_restore_button.setProperty("secondary", True)
    actions.addWidget(page.v164_apply_button, 1)
    actions.addWidget(page.v164_restore_button, 1)
    layout.addLayout(actions)

    page.v164_image_info = QLabel(
        "Selecione uma imagem visível e desbloqueada no canvas.", content
    )
    page.v164_image_info.setObjectName("artStudioSectionHint")
    page.v164_image_info.setWordWrap(True)
    layout.addWidget(page.v164_image_info)
    layout.addStretch(1)

    scroll.setWidget(content)
    outer.addWidget(scroll, 1)
    tabs.addTab(image_page, "Imagem")

    page.v164_image_panel = image_page
    page.v164_image_controls = [
        page.v164_filter_combo, page.v164_brightness, page.v164_contrast,
        page.v164_saturation, page.v164_sharpness, page.v164_blur,
        page.v164_crop_combo, page.v164_mask_combo, page.v164_border_width,
        page.v164_border_color_combo, page.v164_apply_button, page.v164_restore_button,
    ]
    page.v164_apply_button.clicked.connect(lambda: _apply_image_edits(page))
    page.v164_restore_button.clicked.connect(lambda: _restore_original_image(page))
    page.scene.selectionChanged.connect(lambda: _sync_image_controls(page))
    page._v164_image_panel_installed = True
    _sync_image_controls(page)


def enhance_art_studio_page_v164(page) -> None:
    if getattr(page, "_v164_installed", False):
        return
    _install_image_serialization(page)
    if not getattr(page, "_v164_image_serialization_installed", False):
        return
    _install_image_tools(page)
    if getattr(page, "_v164_image_panel_installed", False):
        page._v164_installed = True


def install_art_studio_v164() -> None:
    """Instala o laboratório de imagem depois da biblioteca de componentes V163."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v164_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v164(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v164(page)

    MainWindow.__init__ = init_with_v164
    MainWindow._v164_integration_installed = True
