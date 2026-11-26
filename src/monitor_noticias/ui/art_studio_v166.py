from __future__ import annotations

"""V166 — recorte de fundo por cor, integrado ao fluxo não destrutivo V164/V165."""

import json
import logging

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QCheckBox,
)

from monitor_noticias.ui import art_studio_v165 as v165
from monitor_noticias.ui.art_studio_image_engine_v164 import (
    encode_image_source,
    normalize_image_edit_config,
)
from monitor_noticias.ui.art_studio_image_engine_v166 import (
    normalize_background_config,
    remove_background_by_corner_color,
)
from monitor_noticias.ui.art_studio_v164 import (
    IMAGE_EDIT_CONFIG_DATA_KEY,
    ORIGINAL_IMAGE_DATA_KEY,
    _pixmap_from_png,
    _pixmap_to_png_bytes,
    _selected_image,
    _set_pixmap_preserving_center,
)

log = logging.getLogger(__name__)
BACKGROUND_CONFIG_DATA_KEY = 167


def _background_config_from_item(item) -> dict | None:
    raw = item.data(BACKGROUND_CONFIG_DATA_KEY)
    if not raw:
        return None
    try:
        parsed = json.loads(str(raw)) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return normalize_background_config(parsed)


def _set_spin(spin, value: int) -> None:
    spin.blockSignals(True)
    spin.setValue(value)
    spin.blockSignals(False)


def _sync_background_controls(page) -> None:
    controls = getattr(page, "v166_background_controls", [])
    item = _selected_image(page)
    for control in controls:
        control.setEnabled(item is not None)
    if item is None:
        page.v166_background_info.setText("Selecione uma imagem para configurar o recorte de fundo.")
        return

    config = _background_config_from_item(item)
    if config is None:
        config = {"corner": "top_left", "tolerance": 38, "softness": 2}
        page.v166_background_enabled.blockSignals(True)
        page.v166_background_enabled.setChecked(False)
        page.v166_background_enabled.blockSignals(False)
    else:
        page.v166_background_enabled.blockSignals(True)
        page.v166_background_enabled.setChecked(True)
        page.v166_background_enabled.blockSignals(False)

    page.v166_background_corner.blockSignals(True)
    index = page.v166_background_corner.findData(config["corner"])
    page.v166_background_corner.setCurrentIndex(max(0, index))
    page.v166_background_corner.blockSignals(False)
    _set_spin(page.v166_background_tolerance, config["tolerance"])
    _set_spin(page.v166_background_softness, config["softness"])

    if config and item.data(BACKGROUND_CONFIG_DATA_KEY):
        page.v166_background_info.setText(
            "Recorte salvo neste objeto · "
            f"canto {config['corner'].replace('_', ' ')} · tolerância {config['tolerance']} · "
            f"suavização {config['softness']}"
        )
    else:
        page.v166_background_info.setText(
            "O recorte por cor funciona melhor quando o fundo uniforme toca o canto escolhido. "
            "Evite usar um canto ocupado pelo assunto da foto."
        )


def _read_background_controls(page) -> dict | None:
    if not page.v166_background_enabled.isChecked():
        return None
    return normalize_background_config({
        "corner": page.v166_background_corner.currentData(),
        "tolerance": page.v166_background_tolerance.value(),
        "softness": page.v166_background_softness.value(),
    })


def _apply_all_image_edits_v166(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v166_background_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return

    try:
        # Recalcula filtros, corte e acabamento a partir da fonte original V164,
        # e só depois aplica o recorte de fundo. Não há processamento cumulativo.
        source_b64 = item.data(ORIGINAL_IMAGE_DATA_KEY)
        if not source_b64:
            source_b64 = encode_image_source(_pixmap_to_png_bytes(item.pixmap()))

        base_config = normalize_image_edit_config(v165._read_ui_config(page))
        advanced_config = v165._read_advanced_config(page)
        rendered = v165.render_image_source_v165(str(source_b64), base_config, advanced_config)
        background_config = _read_background_controls(page)
        if background_config is not None:
            rendered = remove_background_by_corner_color(
                rendered,
                corner=background_config["corner"],
                tolerance=background_config["tolerance"],
                softness=background_config["softness"],
            )

        _set_pixmap_preserving_center(item, _pixmap_from_png(rendered))
        item.setData(ORIGINAL_IMAGE_DATA_KEY, str(source_b64))
        item.setData(IMAGE_EDIT_CONFIG_DATA_KEY, json.dumps(base_config, separators=(",", ":")))
        item.setData(
            v165.ADVANCED_IMAGE_CONFIG_DATA_KEY,
            json.dumps(advanced_config, separators=(",", ":")),
        )
        item.setData(
            BACKGROUND_CONFIG_DATA_KEY,
            json.dumps(background_config, separators=(",", ":")) if background_config else None,
        )
        v165._refresh_image_state(page, item)
        _sync_background_controls(page)
        if background_config:
            page.status_label.setText(
                "Ajustes aplicados com recorte de fundo por cor. A imagem original permanece preservada."
            )
        else:
            page.status_label.setText(
                "Ajustes fotográficos aplicados. O recorte de fundo está desativado."
            )
    except Exception as exc:
        log.exception("Falha ao aplicar recorte de fundo V166")
        page.v166_background_info.setText(f"Não foi possível aplicar o recorte: {exc}")
        page.status_label.setText(f"Recorte de fundo não aplicado: {exc}")


def _restore_all_image_edits_v166(page) -> None:
    item = _selected_image(page)
    if item is None:
        page.v166_background_info.setText("Selecione uma única imagem visível e desbloqueada.")
        return
    try:
        v165._restore_all_image_edits(page)
        item.setData(BACKGROUND_CONFIG_DATA_KEY, None)
        _sync_background_controls(page)
        page.status_label.setText(
            "Imagem original restaurada. Filtros, cortes, acabamento e recorte de fundo foram removidos."
        )
    except Exception as exc:
        log.exception("Falha ao restaurar imagem V166")
        page.status_label.setText(f"Não foi possível restaurar a imagem: {exc}")


def _install_background_serialization(page) -> None:
    if getattr(page, "_v166_background_serialization_installed", False):
        return
    previous_serialize = getattr(page, "_v146_base_serialize", None)
    previous_build = getattr(page, "_v146_base_build", None)
    if not callable(previous_serialize) or not callable(previous_build):
        return

    from PySide6.QtWidgets import QGraphicsPixmapItem

    def serialize_with_background(item):
        data = previous_serialize(item)
        if isinstance(item, QGraphicsPixmapItem):
            config = _background_config_from_item(item)
            if config is not None:
                data["v166_background_removal"] = config
        return data

    def build_with_background(data):
        item = previous_build(data)
        config = data.get("v166_background_removal")
        if isinstance(item, QGraphicsPixmapItem) and isinstance(config, dict):
            try:
                normalized = normalize_background_config(config)
                rendered = remove_background_by_corner_color(
                    _pixmap_to_png_bytes(item.pixmap()),
                    corner=normalized["corner"],
                    tolerance=normalized["tolerance"],
                    softness=normalized["softness"],
                )
                _set_pixmap_preserving_center(item, _pixmap_from_png(rendered))
                item.setData(
                    BACKGROUND_CONFIG_DATA_KEY,
                    json.dumps(normalized, separators=(",", ":")),
                )
            except Exception as exc:
                # A imagem reconstruída pelo V165 continua disponível mesmo se
                # uma configuração antiga do recorte não puder ser reaplicada.
                log.warning("Não foi possível reaplicar o recorte V166: %s", exc)
        return item

    page._v146_base_serialize = serialize_with_background
    page._v146_base_build = build_with_background
    page._v166_previous_base_serialize = previous_serialize
    page._v166_previous_base_build = previous_build
    page._v166_background_serialization_installed = True


def _install_background_controls(page) -> None:
    if getattr(page, "_v166_background_controls_installed", False):
        return
    image_panel = getattr(page, "v164_image_panel", None)
    scroll = image_panel.findChild(QScrollArea, "artStudioImageToolsScrollV164") if image_panel else None
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    panel = QFrame(content)
    panel.setObjectName("artStudioImageBackgroundCardV166")
    box = QVBoxLayout(panel)
    box.setContentsMargins(9, 9, 9, 9)
    box.setSpacing(7)

    title = QLabel("RECORTE DE FUNDO", panel)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel(
        "Remove uma área de cor conectada ao canto escolhido. Ideal para fundos lisos; não é recorte automático por IA.",
        panel,
    )
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    box.addWidget(title)
    box.addWidget(hint)

    page.v166_background_enabled = QCheckBox("Ativar remoção do fundo", panel)
    page.v166_background_enabled.setToolTip(
        "Quando ativado, o fundo selecionado será removido ao aplicar os ajustes da imagem."
    )
    box.addWidget(page.v166_background_enabled)

    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setVerticalSpacing(6)

    page.v166_background_corner = QComboBox(panel)
    for value, label in (
        ("top_left", "Superior esquerdo"),
        ("top_right", "Superior direito"),
        ("bottom_left", "Inferior esquerdo"),
        ("bottom_right", "Inferior direito"),
    ):
        page.v166_background_corner.addItem(label, value)

    page.v166_background_tolerance = QSpinBox(panel)
    page.v166_background_tolerance.setRange(0, 255)
    page.v166_background_tolerance.setValue(38)
    page.v166_background_tolerance.setToolTip(
        "Aumente para incluir tons mais diferentes do pixel de referência. Valores altos podem apagar partes do assunto."
    )

    page.v166_background_softness = QSpinBox(panel)
    page.v166_background_softness.setRange(0, 16)
    page.v166_background_softness.setValue(2)
    page.v166_background_softness.setToolTip(
        "Suaviza a transição do recorte e ajuda a reduzir bordas serrilhadas."
    )

    form.addRow("Canto de referência", page.v166_background_corner)
    form.addRow("Tolerância de cor", page.v166_background_tolerance)
    form.addRow("Suavização da borda", page.v166_background_softness)
    box.addLayout(form)

    page.v166_background_apply_button = QPushButton("Aplicar ajustes + recorte de fundo", panel)
    page.v166_background_apply_button.setToolTip(
        "Reprocessa os ajustes V164/V165 a partir do original e aplica a remoção por cor."
    )
    box.addWidget(page.v166_background_apply_button)

    page.v166_background_info = QLabel(
        "Selecione uma imagem para configurar o recorte de fundo.", panel
    )
    page.v166_background_info.setObjectName("artStudioSectionHint")
    page.v166_background_info.setWordWrap(True)
    box.addWidget(page.v166_background_info)

    advanced_panel = getattr(page, "v165_image_panel", None)
    insert_at = layout.indexOf(advanced_panel) + 1 if advanced_panel is not None else layout.count()
    layout.insertWidget(insert_at, panel)

    page.v166_background_controls = [
        page.v166_background_enabled,
        page.v166_background_corner,
        page.v166_background_tolerance,
        page.v166_background_softness,
        page.v166_background_apply_button,
    ]
    page.v166_background_apply_button.clicked.connect(lambda: _apply_all_image_edits_v166(page))

    # O botão principal também passa a incluir o recorte ativo. Assim o fluxo
    # de trabalho tem um único ponto de aplicação e não cria resultados divergentes.
    try:
        page.v164_apply_button.clicked.disconnect()
    except (TypeError, RuntimeError):
        pass
    page.v164_apply_button.setText("Aplicar ajustes + recorte")
    page.v164_apply_button.clicked.connect(lambda: _apply_all_image_edits_v166(page))

    try:
        page.v164_restore_button.clicked.disconnect()
    except (TypeError, RuntimeError):
        pass
    page.v164_restore_button.clicked.connect(lambda: _restore_all_image_edits_v166(page))
    page.scene.selectionChanged.connect(lambda: _sync_background_controls(page))
    page._v166_background_controls_installed = True
    page.v166_background_panel = panel
    _sync_background_controls(page)


def enhance_art_studio_page_v166(page) -> None:
    if getattr(page, "_v166_installed", False):
        return
    _install_background_serialization(page)
    if not getattr(page, "_v166_background_serialization_installed", False):
        return
    _install_background_controls(page)
    if getattr(page, "_v166_background_controls_installed", False):
        page._v166_installed = True


def install_art_studio_v166() -> None:
    """Instala o recorte de fundo após o laboratório e acabamento V165."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v166_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v166(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v166(page)

    MainWindow.__init__ = init_with_v166
    MainWindow._v166_integration_installed = True
