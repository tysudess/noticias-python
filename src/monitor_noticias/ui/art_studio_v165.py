from __future__ import annotations

"""V165 — acabamento fotográfico avançado e enquadramento focal não destrutivo.

Amplia o Laboratório V164 com temperatura, matiz, realces, sombras, vinheta,
desbotamento, zoom/foco de corte, rotação e espelhamento. A fonte original,
os parâmetros V164/V165 e a imagem renderizada são preservados no mesmo item.
"""

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsPixmapItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_image_engine_v165 import (
    DEFAULT_ADVANCED_IMAGE_CONFIG,
    normalize_advanced_image_config,
    render_image_source_v165,
)
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.art_studio_v164 import (
    IMAGE_EDIT_CONFIG_DATA_KEY,
    ORIGINAL_IMAGE_DATA_KEY,
    _config_from_item,
    _pixmap_from_png,
    _pixmap_to_png_bytes,
    _read_ui_config,
    _restore_original_image,
    _selected_image,
    _set_pixmap_preserving_center,
    _sync_image_controls,
)
from monitor_noticias.ui.art_studio_image_engine_v164 import encode_image_source, normalize_image_edit_config

log = logging.getLogger(__name__)

ADVANCED_IMAGE_CONFIG_DATA_KEY = 166

IMAGE_FINISH_PRESETS = {
    "natural": {
        "label": "Natural e equilibrado",
        "base": {"preset": "vivid", "brightness": 1.05, "contrast": 1.04, "saturation": 1.08, "sharpness": 1.10},
        "advanced": {"temperature": 3, "highlights": -5, "shadows": 10, "vignette": 12},
    },
    "portrait": {
        "label": "Retrato quente",
        "base": {"preset": "warm", "brightness": 1.04, "contrast": 0.98, "saturation": 1.08, "sharpness": 0.95},
        "advanced": {"temperature": 10, "tint": 2, "highlights": -18, "shadows": 18, "vignette": 24, "fade": 4},
    },
    "editorial": {
        "label": "Editorial cinematográfico",
        "base": {"preset": "cinematic", "brightness": 1.0, "contrast": 1.15, "saturation": 0.88, "sharpness": 1.10},
        "advanced": {"temperature": -5, "highlights": -18, "shadows": 12, "vignette": 32, "fade": 8},
    },
    "night": {
        "label": "Noturno frio",
        "base": {"preset": "cool", "brightness": 1.12, "contrast": 1.18, "saturation": 0.90, "sharpness": 1.20},
        "advanced": {"temperature": -18, "tint": -6, "highlights": -28, "shadows": 24, "vignette": 35, "fade": 3},
    },
}


def _advanced_config_from_item(item: QGraphicsPixmapItem) -> dict:
    raw = item.data(ADVANCED_IMAGE_CONFIG_DATA_KEY)
    try:
        parsed = json.loads(str(raw)) if raw else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = {}
    return normalize_advanced_image_config(parsed)


def _set_spin(spin, value) -> None:
    spin.blockSignals(True)
    spin.setValue(value)
    spin.blockSignals(False)


def _sync_advanced_controls(page) -> None:
    item = _selected_image(page)
    controls = getattr(page, "v165_image_controls", [])
    for control in controls:
        control.setEnabled(item is not None)
    if item is None:
        if getattr(page, "v165_image_info", None) is not None:
            page.v165_image_info.setText("Selecione uma imagem para liberar o acabamento avançado.")
        return

    config = _advanced_config_from_item(item)
    for key, attr in (
        ("temperature", "v165_temperature"),
        ("tint", "v165_tint"),
        ("highlights", "v165_highlights"),
        ("shadows", "v165_shadows"),
        ("vignette", "v165_vignette"),
        ("fade", "v165_fade"),
        ("crop_zoom", "v165_crop_zoom"),
        ("focus_x", "v165_focus_x"),
        ("focus_y", "v165_focus_y"),
    ):
        spin = getattr(page, attr, None)
        if spin is not None:
            _set_spin(spin, config[key])

    rotation = page.v165_rotation_combo.findData(config["rotation"])
    page.v165_rotation_combo.blockSignals(True)
    page.v165_rotation_combo.setCurrentIndex(max(0, rotation))
    page.v165_rotation_combo.blockSignals(False)
    page.v165_flip_h.blockSignals(True)
    page.v165_flip_h.setChecked(config["flip_h"])
    page.v165_flip_h.blockSignals(False)
    page.v165_flip_v.blockSignals(True)
    page.v165_flip_v.setChecked(config["flip_v"])
    page.v165_flip_v.blockSignals(False)
    page.v165_image_info.setText(
        "Acabamento avançado carregado · "
        f"temperatura {config['temperature']:+.0f} · matiz {config['tint']:+.0f} · "
        f"zoom {config['crop_zoom']:.2f}× · giro {config['rotation']}°"
    )


def _apply_finish_preset_to_controls(page) -> None:
    key = str(page.v165_preset_combo.currentData() or "natural")
    preset = IMAGE_FINISH_PRESETS.get(key)
    if preset is None:
        return

    base = normalize_image_edit_config(preset.get("base", {}))
    for combo_attr, config_key in (
        ("v164_filter_combo", "preset"),
        ("v164_crop_combo", "crop"),
        ("v164_mask_combo", "mask"),
        ("v164_border_color_combo", "border_color"),
    ):
        combo = getattr(page, combo_attr)
        index = combo.findData(base[config_key])
        if index >= 0:
            combo.setCurrentIndex(index)
    for spin_attr, config_key in (
        ("v164_brightness", "brightness"),
        ("v164_contrast", "contrast"),
        ("v164_saturation", "saturation"),
        ("v164_sharpness", "sharpness"),
        ("v164_blur", "blur"),
        ("v164_border_width", "border_width"),
    ):
        getattr(page, spin_attr).setValue(base[config_key])

    advanced = normalize_advanced_image_config(preset.get("advanced", {}))
    for key_name, attr in (
        ("temperature", "v165_temperature"), ("tint", "v165_tint"),
        ("highlights", "v165_highlights"), ("shadows", "v165_shadows"),
        ("vignette", "v165_vignette"), ("fade", "v165_fade"),
        ("crop_zoom", "v165_crop_zoom"), ("focus_x", "v165_focus_x"),
        ("focus_y", "v165_focus_y"),
    ):
        getattr(page, attr).setValue(advanced[key_name])
    rotation_index = page.v165_rotation_combo.findData(advanced["rotation"])
    page.v165_rotation_combo.setCurrentIndex(max(0, rotation_index))
    page.v165_flip_h.setChecked(advanced["flip_h"])
    page.v165_flip_v.setChecked(advanced["flip_v"])
    page.v165_image_info.setText(
        f"Estilo '{preset['label']}' carregado. Confira os valores e clique em Aplicar todos os ajustes."
    )


def _read_advanced_config(page) -> dict:
    return normalize_advanced_image_config({
        "temperature": page.v165_temperature.value(),
        "tint": page.v165_tint.value(),
        "highlights": page.v165_highlights.value(),
        "shadows": page.v165_shadows.value(),
        "vignette": page.v165_vignette.value(),
        "fade": page.v165_fade.value(),
        "crop_zoom": page.v165_crop_zoom.value(),
        "focus_x": page.v165_focus_x.value(),
        "focus_y": page.v165_focus_y.value(),
        "rotation": page.v165_rotation_combo.currentData(),
        "flip_h": page.v165_flip_h.isChecked(),
        "flip_v": page.v165_flip_v.isChecked(),
    })


def _refresh_image_state(page, item: QGraphicsPixmapItem) -> None:
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
    _sync_advanced_controls(page)
    page.scene.update()


def _apply_all_image_edits(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v165_image_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return

    try:
        source_b64 = item.data(ORIGINAL_IMAGE_DATA_KEY)
        if not source_b64:
            source_b64 = encode_image_source(_pixmap_to_png_bytes(item.pixmap()))
        base_config = normalize_image_edit_config(_read_ui_config(page))
        advanced_config = _read_advanced_config(page)
        rendered = render_image_source_v165(str(source_b64), base_config, advanced_config)
        pixmap = _pixmap_from_png(rendered)
        _set_pixmap_preserving_center(item, pixmap)
        item.setData(ORIGINAL_IMAGE_DATA_KEY, str(source_b64))
        item.setData(IMAGE_EDIT_CONFIG_DATA_KEY, json.dumps(base_config, separators=(",", ":")))
        item.setData(
            ADVANCED_IMAGE_CONFIG_DATA_KEY,
            json.dumps(advanced_config, separators=(",", ":")),
        )
        _refresh_image_state(page, item)
        page.status_label.setText(
            "Ajustes fotográficos e enquadramento aplicados. A imagem original continua preservada."
        )
    except Exception as exc:
        log.exception("Falha ao aplicar acabamento avançado V165")
        page.v165_image_info.setText(f"Não foi possível aplicar os ajustes: {exc}")
        page.status_label.setText(f"Acabamento de imagem não aplicado: {exc}")


def _restore_all_image_edits(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v165_image_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return
    try:
        _restore_original_image(page)
        item.setData(ADVANCED_IMAGE_CONFIG_DATA_KEY, None)
        for attr, value in DEFAULT_ADVANCED_IMAGE_CONFIG.items():
            if attr == "rotation":
                index = page.v165_rotation_combo.findData(value)
                page.v165_rotation_combo.setCurrentIndex(max(0, index))
            elif attr == "flip_h":
                page.v165_flip_h.setChecked(value)
            elif attr == "flip_v":
                page.v165_flip_v.setChecked(value)
            else:
                spin = getattr(page, f"v165_{attr}", None)
                if spin is not None:
                    spin.setValue(value)
        _sync_advanced_controls(page)
        page.status_label.setText(
            "Imagem original restaurada. Todos os filtros, cortes e acabamentos V164/V165 foram removidos."
        )
    except Exception as exc:
        log.exception("Falha ao restaurar a imagem original V165")
        page.status_label.setText(f"Não foi possível restaurar a imagem: {exc}")


def _center_crop_focus(page) -> None:
    page.v165_focus_x.setValue(50.0)
    page.v165_focus_y.setValue(50.0)
    page.v165_crop_zoom.setValue(1.0)


def _install_advanced_image_controls(page) -> None:
    if getattr(page, "_v165_advanced_controls_installed", False):
        return
    image_page = getattr(page, "v164_image_panel", None)
    scroll = image_page.findChild(QScrollArea, "artStudioImageToolsScrollV164") if image_page else None
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    panel = QFrame(content)
    panel.setObjectName("artStudioImageAdvancedCardV165")
    box = QVBoxLayout(panel)
    box.setContentsMargins(9, 9, 9, 9)
    box.setSpacing(7)

    title = QLabel("ACABAMENTO AVANÇADO", panel)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel(
        "Ajustes adicionais e controle do ponto focal. Todos são reprocessados a partir da imagem original.",
        panel,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    box.addWidget(title)
    box.addWidget(hint)

    preset_row = QHBoxLayout()
    page.v165_preset_combo = QComboBox(panel)
    page.v165_preset_combo.setObjectName("artStudioImageFinishPresetV165")
    for key, preset in IMAGE_FINISH_PRESETS.items():
        page.v165_preset_combo.addItem(preset["label"], key)
    page.v165_apply_preset_button = QPushButton("Carregar estilo", panel)
    page.v165_apply_preset_button.setProperty("secondary", True)
    preset_row.addWidget(page.v165_preset_combo, 1)
    preset_row.addWidget(page.v165_apply_preset_button)
    box.addLayout(preset_row)

    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(6)

    def make_spin(low: float, high: float, step: float, suffix: str = ""):
        spin = QDoubleSpinBox(panel)
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setDecimals(1 if step < 1 else 0)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(104)
        return spin

    page.v165_temperature = make_spin(-100, 100, 5)
    page.v165_tint = make_spin(-100, 100, 5)
    page.v165_highlights = make_spin(-100, 100, 5)
    page.v165_shadows = make_spin(-100, 100, 5)
    page.v165_vignette = make_spin(0, 100, 5, " %")
    page.v165_fade = make_spin(0, 100, 5, " %")
    page.v165_crop_zoom = make_spin(1, 3, 0.05, "×")
    page.v165_crop_zoom.setDecimals(2)
    page.v165_focus_x = make_spin(0, 100, 5, " %")
    page.v165_focus_y = make_spin(0, 100, 5, " %")

    for label, control in (
        ("Temperatura · frio / quente", page.v165_temperature),
        ("Matiz · verde / magenta", page.v165_tint),
        ("Realces", page.v165_highlights),
        ("Sombras", page.v165_shadows),
        ("Vinheta", page.v165_vignette),
        ("Desbotamento", page.v165_fade),
        ("Zoom do corte", page.v165_crop_zoom),
        ("Ponto focal horizontal", page.v165_focus_x),
        ("Ponto focal vertical", page.v165_focus_y),
    ):
        form.addRow(label, control)
    box.addLayout(form)

    orientation = QHBoxLayout()
    page.v165_rotation_combo = QComboBox(panel)
    for value, label in ((0, "0°"), (90, "90° direita"), (180, "180°"), (270, "90° esquerda")):
        page.v165_rotation_combo.addItem(label, value)
    page.v165_flip_h = QCheckBox("Espelhar horizontal")
    page.v165_flip_v = QCheckBox("Espelhar vertical")
    orientation.addWidget(page.v165_rotation_combo, 1)
    box.addLayout(orientation)
    flips = QHBoxLayout()
    flips.addWidget(page.v165_flip_h)
    flips.addWidget(page.v165_flip_v)
    box.addLayout(flips)

    page.v165_center_focus_button = QPushButton("Centralizar corte e zoom")
    page.v165_center_focus_button.setProperty("secondary", True)
    page.v165_center_focus_button.setToolTip(
        "Volta o ponto focal para o centro e o zoom para 1,00×."
    )
    box.addWidget(page.v165_center_focus_button)

    border_panel = content.findChild(QFrame, "artStudioImageBorderCardV164")
    insert_at = layout.indexOf(border_panel) + 1 if border_panel is not None else max(0, layout.count() - 3)
    layout.insertWidget(insert_at, panel)

    page.v165_image_info = QLabel("Selecione uma imagem para liberar o acabamento avançado.", panel)
    page.v165_image_info.setObjectName("artStudioSectionHint")
    page.v165_image_info.setWordWrap(True)
    box.addWidget(page.v165_image_info)

    page.v165_image_controls = [
        page.v165_temperature, page.v165_tint, page.v165_highlights,
        page.v165_shadows, page.v165_vignette, page.v165_fade,
        page.v165_crop_zoom, page.v165_focus_x, page.v165_focus_y,
        page.v165_rotation_combo, page.v165_flip_h, page.v165_flip_v,
        page.v165_center_focus_button, page.v165_preset_combo,
        page.v165_apply_preset_button,
    ]
    page.v165_center_focus_button.clicked.connect(lambda: _center_crop_focus(page))
    page.v165_apply_preset_button.clicked.connect(lambda: _apply_finish_preset_to_controls(page))

    # O clique original do V164 é substituído por uma única operação combinada,
    # que aplica todos os parâmetros a partir da fonte original, sem dupla compressão.
    page.v164_apply_button.clicked.disconnect()
    page.v164_apply_button.setText("Aplicar todos os ajustes")
    page.v164_apply_button.clicked.connect(lambda: _apply_all_image_edits(page))
    page.v164_restore_button.clicked.disconnect()
    page.v164_restore_button.clicked.connect(lambda: _restore_all_image_edits(page))
    page.scene.selectionChanged.connect(lambda: _sync_advanced_controls(page))
    page._v165_advanced_controls_installed = True
    page.v165_image_panel = panel
    _sync_advanced_controls(page)


def _install_advanced_image_serialization(page) -> None:
    if getattr(page, "_v165_image_serialization_installed", False):
        return
    previous_serialize = getattr(page, "_v146_base_serialize", None)
    previous_build = getattr(page, "_v146_base_build", None)
    if not callable(previous_serialize) or not callable(previous_build):
        return

    def serialize_with_advanced_image(item):
        data = previous_serialize(item)
        if isinstance(item, QGraphicsPixmapItem):
            raw = item.data(ADVANCED_IMAGE_CONFIG_DATA_KEY)
            if raw:
                try:
                    config = normalize_advanced_image_config(json.loads(str(raw)))
                    data["v165_image_advanced_config"] = config
                except (TypeError, ValueError, json.JSONDecodeError):
                    log.warning("Metadados avançados V165 inválidos; preservando a imagem renderizada.")
        return data

    def build_with_advanced_image(data):
        item = previous_build(data)
        if isinstance(item, QGraphicsPixmapItem):
            source = data.get("v164_image_source_png_base64")
            base_config = data.get("v164_image_edit_config")
            advanced_config = data.get("v165_image_advanced_config")
            if source and isinstance(base_config, dict) and isinstance(advanced_config, dict):
                try:
                    normalized_advanced = normalize_advanced_image_config(advanced_config)
                    rendered = render_image_source_v165(str(source), base_config, normalized_advanced)
                    _set_pixmap_preserving_center(item, _pixmap_from_png(rendered))
                    item.setData(
                        ADVANCED_IMAGE_CONFIG_DATA_KEY,
                        json.dumps(normalized_advanced, separators=(",", ":")),
                    )
                except Exception as exc:
                    # O objeto já foi reconstruído pelo V164; uma falha no acabamento
                    # avançado não deve impedir que o restante do projeto abra.
                    log.warning("Não foi possível reaplicar o acabamento V165: %s", exc)
        return item

    page._v146_base_serialize = serialize_with_advanced_image
    page._v146_base_build = build_with_advanced_image
    page._v165_previous_base_serialize = previous_serialize
    page._v165_previous_base_build = previous_build
    page._v165_image_serialization_installed = True


def enhance_art_studio_page_v165(page) -> None:
    if getattr(page, "_v165_installed", False):
        return
    _install_advanced_image_serialization(page)
    if not getattr(page, "_v165_image_serialization_installed", False):
        return
    _install_advanced_image_controls(page)
    if getattr(page, "_v165_advanced_controls_installed", False):
        page._v165_installed = True


def install_art_studio_v165() -> None:
    """Instala o acabamento avançado depois do Laboratório de Imagem V164."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v165_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v165(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v165(page)

    MainWindow.__init__ = init_with_v165
    MainWindow._v165_integration_installed = True
