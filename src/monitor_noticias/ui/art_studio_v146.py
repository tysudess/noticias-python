from __future__ import annotations

"""V146 — agrupamento, molduras, efeitos e ajustes fotográficos.

Esta camada amplia o Estúdio existente sem substituir os módulos V143–V145.
Os recursos usam Qt e Pillow, que já fazem parte das dependências da Central.
"""

from io import BytesIO
from typing import Any

from PIL import Image, ImageEnhance
from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QAction, QColor, QBrush, QKeySequence, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY

EFFECT_DATA_KEY = 20
FRAME_DATA_KEY = 21
FRAME_CHILD_KEY = 22


def _pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Não foi possível preparar a imagem para edição.")
    if not pixmap.save(buffer, "PNG"):
        raise OSError("Não foi possível converter a imagem do objeto.")
    return Image.open(BytesIO(bytes(buffer.data()))).convert("RGBA")


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    output = BytesIO()
    image.save(output, format="PNG")
    pixmap = QPixmap()
    if not pixmap.loadFromData(output.getvalue(), "PNG"):
        raise OSError("Não foi possível carregar a prévia da imagem editada.")
    return pixmap


def _adjust_pixmap(
    original: QPixmap,
    *,
    brightness: int,
    contrast: int,
    saturation: int,
    sharpness: int,
) -> QPixmap:
    image = _pixmap_to_pil(original)
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(max(0, brightness) / 100.0)
    rgb = ImageEnhance.Contrast(rgb).enhance(max(0, contrast) / 100.0)
    rgb = ImageEnhance.Color(rgb).enhance(max(0, saturation) / 100.0)
    rgb = ImageEnhance.Sharpness(rgb).enhance(max(0, sharpness) / 100.0)
    rgb.putalpha(alpha)
    return _pil_to_pixmap(rgb)


class _PhotoAdjustDialog(QDialog):
    """Ajustes básicos com prévia, sem alterar a imagem antes de confirmar."""

    def __init__(self, original: QPixmap, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustes da fotografia")
        self.setMinimumWidth(480)
        self._original = QPixmap(original)
        self._result = QPixmap(original)

        root = QVBoxLayout(self)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 210)
        self.preview.setStyleSheet("background:#17293A;border:1px solid #40566B;border-radius:8px;")
        root.addWidget(self.preview)

        form = QFormLayout()
        self.sliders: dict[str, QSlider] = {}
        for key, label in (
            ("brightness", "Brilho"),
            ("contrast", "Contraste"),
            ("saturation", "Saturação"),
            ("sharpness", "Nitidez"),
        ):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 200)
            slider.setValue(100)
            slider.setToolTip("100% mantém o valor original")
            slider.valueChanged.connect(self._refresh_preview)
            self.sliders[key] = slider
            form.addRow(label, slider)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar ajustes")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._refresh_preview()

    def _refresh_preview(self, *_args) -> None:
        values = {key: slider.value() for key, slider in self.sliders.items()}
        try:
            self._result = _adjust_pixmap(self._original, **values)
            self.preview.setPixmap(
                self._result.scaled(
                    self.preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception as exc:
            self.preview.setText(f"Não foi possível gerar a prévia: {exc}")

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._refresh_preview()

    def result_pixmap(self) -> QPixmap:
        return QPixmap(self._result)


def _top_level_items(page) -> list[QGraphicsItem]:
    return [
        item
        for item in page.scene.items()
        if item.parentItem() is None
        and item.data(ITEM_KIND_KEY) != "canvas-background"
    ]


def _active_item(page):
    item = getattr(page, "_v145_active_item", None)
    if item is not None:
        try:
            if item.scene() is page.scene:
                return item
        except RuntimeError:
            page._v145_active_item = None
    selected = page.scene.selectedItems()
    return selected[0] if selected else None


def _selected_items(page) -> list[QGraphicsItem]:
    selected = list(page.scene.selectedItems())
    if not selected:
        item = _active_item(page)
        if item is not None:
            selected = [item]
    # Um pai selecionado já representa seus filhos; evita grupos aninhados acidentais.
    return [
        item for item in selected
        if not any(item.parentItem() is candidate for candidate in selected)
    ]


def _schedule_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()


def _refresh(page, selected: QGraphicsItem | None = None) -> None:
    page._refresh_layers(select_item=selected)
    page._v145_active_item = selected
    page._update_selection_controls(selected)
    page._v146_update_controls()


def _group_selected(page) -> None:
    selected = _selected_items(page)
    if len(selected) < 2:
        page.status_label.setText("Selecione pelo menos dois objetos no canvas usando Ctrl ou seleção por área.")
        return
    if any(bool(item.data(LOCKED_KEY)) for item in selected):
        page.status_label.setText("Desbloqueie as camadas antes de agrupá-las.")
        return
    group = page.scene.createItemGroup(selected)
    group.setData(ITEM_KIND_KEY, "group")
    group.setData(ITEM_NAME_KEY, f"Grupo ({len(selected)} objetos)")
    group.setData(HISTORY_ID_KEY, __import__("uuid").uuid4().hex)
    group.setData(LOCKED_KEY, False)
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
    group.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    group.setTransformOriginPoint(group.boundingRect().center())
    page.scene.clearSelection()
    group.setSelected(True)
    _refresh(page, group)
    page.status_label.setText(f"{len(selected)} objetos agrupados. Arraste o grupo para movê-los juntos.")
    _schedule_history(page)


def _ungroup_selected(page) -> None:
    item = _active_item(page)
    if not isinstance(item, QGraphicsItemGroup):
        page.status_label.setText("Selecione um grupo para desagrupá-lo.")
        return
    if bool(item.data(LOCKED_KEY)):
        page.status_label.setText("Desbloqueie o grupo antes de desagrupá-lo.")
        return
    children = list(item.childItems())
    page.scene.destroyItemGroup(item)
    for child in children:
        if child.data(FRAME_CHILD_KEY):
            continue
        child.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        child.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            not bool(child.data(LOCKED_KEY)),
        )
    page.scene.clearSelection()
    active = next((child for child in children if not child.data(FRAME_CHILD_KEY)), None)
    if active is not None:
        active.setSelected(True)
    _refresh(page, active)
    page.status_label.setText("Grupo desfeito. Os objetos voltaram a ser camadas independentes.")
    _schedule_history(page)


def _remove_frame_child(item: QGraphicsItem) -> None:
    for child in list(item.childItems()):
        if child.data(FRAME_CHILD_KEY):
            child.setParentItem(None)
            if child.scene() is not None:
                child.scene().removeItem(child)
            del child


def _apply_frame(item: QGraphicsItem, config: dict[str, Any] | None) -> None:
    if not isinstance(item, QGraphicsPixmapItem):
        return
    _remove_frame_child(item)
    item.setData(FRAME_DATA_KEY, config)
    if not config:
        return
    color = QColor(str(config.get("color", "#D6B66D")))
    width = max(1.0, min(48.0, float(config.get("width", 12))))
    frame = QGraphicsRectItem(item.boundingRect(), item)
    frame.setBrush(Qt.BrushStyle.NoBrush)
    frame.setPen(QPen(color, width))
    frame.setZValue(5)
    frame.setData(FRAME_CHILD_KEY, True)
    frame.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
    frame.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
    frame.setAcceptedMouseButtons(Qt.MouseButton.NoButton)


def _apply_image_frame(page) -> None:
    item = _active_item(page)
    if not isinstance(item, QGraphicsPixmapItem) or bool(item.data(LOCKED_KEY)):
        page.status_label.setText("Selecione uma imagem desbloqueada para aplicar uma moldura.")
        return
    choices = ["Dourada", "Branca", "Azul-marinho", "Preta", "Remover moldura"]
    choice, accepted = __import__("PySide6.QtWidgets", fromlist=["QInputDialog"]).QInputDialog.getItem(
        page, "Moldura da imagem", "Escolha o estilo:", choices, 0, False
    )
    if not accepted:
        return
    if choice == "Remover moldura":
        _apply_frame(item, None)
        page.status_label.setText("Moldura removida.")
    else:
        color = {
            "Dourada": "#D6B66D",
            "Branca": "#FFFFFF",
            "Azul-marinho": "#0B263D",
            "Preta": "#101010",
        }[choice]
        _apply_frame(item, {"color": color, "width": 14})
        page.status_label.setText(f"Moldura {choice.lower()} aplicada à imagem.")
    page.scene.update()
    _schedule_history(page)


def _apply_visual_effect(page) -> None:
    item = _active_item(page)
    if item is None or bool(item.data(LOCKED_KEY)):
        page.status_label.setText("Selecione um objeto desbloqueado para aplicar um efeito.")
        return
    choices = ["Contorno dourado", "Contorno branco", "Sombra suave", "Sombra intensa", "Remover efeito"]
    from PySide6.QtWidgets import QInputDialog
    choice, accepted = QInputDialog.getItem(page, "Contorno e sombra", "Escolha um efeito:", choices, 0, False)
    if not accepted:
        return
    if choice == "Remover efeito":
        item.setGraphicsEffect(None)
        item.setData(EFFECT_DATA_KEY, None)
        page.status_label.setText("Efeito removido.")
    else:
        outline = choice.startswith("Contorno")
        color = "#D6B66D" if "dourado" in choice.lower() else "#FFFFFF" if outline else "#000000"
        blur = 1.5 if outline else 18.0 if choice == "Sombra suave" else 30.0
        y_offset = 0.0 if outline else 7.0 if choice == "Sombra suave" else 12.0
        alpha = 235 if outline else 145
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(blur)
        effect.setOffset(0.0, y_offset)
        selected_color = QColor(color)
        selected_color.setAlpha(alpha)
        effect.setColor(selected_color)
        item.setGraphicsEffect(effect)
        item.setData(
            EFFECT_DATA_KEY,
            {"color": selected_color.name(QColor.NameFormat.HexArgb), "blur": blur, "x": 0.0, "y": y_offset},
        )
        page.status_label.setText(f"{choice} aplicado.")
    page.scene.update()
    _schedule_history(page)


def _refresh_frame_after_crop(page) -> None:
    item = _active_item(page)
    if isinstance(item, QGraphicsPixmapItem):
        config = item.data(FRAME_DATA_KEY)
        if isinstance(config, dict):
            _apply_frame(item, dict(config))


def _apply_photo_adjustments(page) -> None:
    item = _active_item(page)
    if not isinstance(item, QGraphicsPixmapItem) or bool(item.data(LOCKED_KEY)):
        page.status_label.setText("Selecione uma imagem desbloqueada para ajustar a fotografia.")
        return
    dialog = _PhotoAdjustDialog(item.pixmap(), page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    item.setPixmap(dialog.result_pixmap())
    frame = item.data(FRAME_DATA_KEY)
    if frame:
        _apply_frame(item, dict(frame))
    page.status_label.setText("Brilho, contraste, saturação e nitidez aplicados à fotografia.")
    page.scene.update()
    _schedule_history(page)


def _serialize_item(page, item: QGraphicsItem) -> dict[str, Any]:
    if isinstance(item, QGraphicsItemGroup):
        pos = item.pos()
        children = [child for child in item.childItems() if not child.data(FRAME_CHILD_KEY)]
        data: dict[str, Any] = {
            "kind": "group",
            "name": item.data(ITEM_NAME_KEY) or "Grupo",
            "x": float(pos.x()),
            "y": float(pos.y()),
            "rotation": float(item.rotation()),
            "scale": float(item.scale()),
            "opacity": float(item.opacity()),
            "z": float(item.zValue()),
            "history_id": str(item.data(HISTORY_ID_KEY) or ""),
            "visible": bool(item.isVisible()),
            "locked": bool(item.data(LOCKED_KEY)),
            "v146_effect": item.data(EFFECT_DATA_KEY),
            "children": [_serialize_item(page, child) for child in children],
        }
    else:
        data = page._v146_base_serialize(item)
        if item.data(EFFECT_DATA_KEY):
            data["v146_effect"] = item.data(EFFECT_DATA_KEY)
        if item.data(FRAME_DATA_KEY):
            data["v146_frame"] = item.data(FRAME_DATA_KEY)
    return data


def _effect_from_data(item: QGraphicsItem, data: dict[str, Any]) -> None:
    config = data.get("v146_effect")
    if not isinstance(config, dict):
        return
    effect = QGraphicsDropShadowEffect()
    effect.setColor(QColor(str(config.get("color", "#99000000"))))
    effect.setBlurRadius(max(0.0, min(64.0, float(config.get("blur", 18.0)))))
    effect.setOffset(float(config.get("x", 0.0)), float(config.get("y", 7.0)))
    item.setGraphicsEffect(effect)
    item.setData(EFFECT_DATA_KEY, config)


def _build_item(page, data: dict[str, Any]) -> QGraphicsItem:
    if data.get("kind") == "group":
        item = QGraphicsItemGroup()
        item.setData(ITEM_KIND_KEY, "group")
        item.setData(ITEM_NAME_KEY, str(data.get("name", "Grupo")))
        item.setData(HISTORY_ID_KEY, str(data.get("history_id") or ""))
        item.setData(LOCKED_KEY, bool(data.get("locked", False)))
        for child_data in data.get("children", []):
            child = _build_item(page, child_data)
            item.addToGroup(child)
        _effect_from_data(item, data)
    else:
        item = page._v146_base_build(data)
        _effect_from_data(item, data)
        if isinstance(item, QGraphicsPixmapItem):
            _apply_frame(item, data.get("v146_frame"))
    item.setPos(float(data.get("x", 0.0)), float(data.get("y", 0.0)))
    item.setRotation(float(data.get("rotation", 0.0)))
    item.setScale(float(data.get("scale", 1.0)))
    item.setOpacity(max(0.0, min(1.0, float(data.get("opacity", 1.0)))))
    item.setZValue(float(data.get("z", 1.0)))
    item.setVisible(bool(data.get("visible", True)))
    locked = bool(data.get("locked", False))
    item.setData(LOCKED_KEY, locked)
    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
    if data.get("history_id"):
        item.setData(HISTORY_ID_KEY, str(data["history_id"]))
    if isinstance(item, QGraphicsItemGroup):
        item.setTransformOriginPoint(item.boundingRect().center())
    return item


def _update_controls(page) -> None:
    selected = _selected_items(page)
    item = _active_item(page)
    is_group = isinstance(item, QGraphicsItemGroup)
    page.v146_group_button.setEnabled(len(selected) >= 2 and all(not bool(i.data(LOCKED_KEY)) for i in selected))
    page.v146_ungroup_button.setEnabled(is_group and not bool(item.data(LOCKED_KEY)))
    is_image = isinstance(item, QGraphicsPixmapItem) and not bool(item.data(LOCKED_KEY))
    page.v146_photo_button.setEnabled(bool(is_image))
    page.v146_frame_button.setEnabled(bool(is_image))
    page.v146_effect_button.setEnabled(item is not None and not bool(item.data(LOCKED_KEY)))


def enhance_art_studio_page_v146(page) -> None:
    """Instala os recursos V146 uma única vez na página já integrada à Central."""
    if getattr(page, "_v146_installed", False):
        return
    page._v146_installed = True

    # O canvas continua permitindo seleção por área e Ctrl+clique para múltiplos objetos.
    page.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
    page._v146_base_content_items = page._content_items
    page._content_items = lambda: _top_level_items(page)

    page._v146_base_serialize = page._serialize_item
    page._serialize_item = lambda item: _serialize_item(page, item)
    page._v146_base_build = page._build_item_from_data
    page._build_item_from_data = lambda data: _build_item(page, data)

    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next((label.parentWidget() for label in labels if label.text() == "CAMADAS E OBJETOS"), None)
    layout = panel.layout() if panel is not None else None
    if layout is None:
        return

    page.v146_group_button = QPushButton("Agrupar selecionados")
    page.v146_ungroup_button = QPushButton("Desagrupar")
    page.v146_photo_button = QPushButton("Ajustar fotografia")
    page.v146_frame_button = QPushButton("Moldura da imagem")
    page.v146_effect_button = QPushButton("Contorno e sombra")
    for button in (
        page.v146_group_button,
        page.v146_ungroup_button,
        page.v146_photo_button,
        page.v146_frame_button,
        page.v146_effect_button,
    ):
        button.setProperty("secondary", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
    page.v146_photo_button.setProperty("purple", True)

    tools = QFrame()
    tools.setObjectName("artStudioAdvancedTools")
    tools_layout = QVBoxLayout(tools)
    tools_layout.setContentsMargins(0, 5, 0, 5)
    tools_layout.setSpacing(5)
    row = QHBoxLayout()
    row.addWidget(page.v146_group_button, 1)
    row.addWidget(page.v146_ungroup_button, 1)
    tools_layout.addLayout(row)
    tools_layout.addWidget(page.v146_photo_button)
    tools_layout.addWidget(page.v146_frame_button)
    tools_layout.addWidget(page.v146_effect_button)
    index = layout.indexOf(page.layers)
    layout.insertWidget(index + 2, tools)

    page.v146_group_button.clicked.connect(lambda: _group_selected(page))
    page.v146_ungroup_button.clicked.connect(lambda: _ungroup_selected(page))
    page.v146_photo_button.clicked.connect(lambda: _apply_photo_adjustments(page))
    page.v146_frame_button.clicked.connect(lambda: _apply_image_frame(page))
    page.v146_effect_button.clicked.connect(lambda: _apply_visual_effect(page))
    # O recorte V145 é mantido; após sua janela fechar, redimensiona a moldura
    # interna caso o usuário tenha recortado uma imagem que já tinha borda.
    if hasattr(page, "v145_crop_button"):
        page.v145_crop_button.clicked.connect(lambda: _refresh_frame_after_crop(page))

    page._v146_update_controls = lambda: _update_controls(page)
    original_update = page._update_selection_controls

    def update_with_v146(item):
        original_update(item)
        page._v146_update_controls()

    page._update_selection_controls = update_with_v146
    page.scene.selectionChanged.connect(lambda: page._v146_update_controls())

    group_action = QAction("Agrupar selecionados", page)
    group_action.setShortcut(QKeySequence("Ctrl+G"))
    group_action.triggered.connect(lambda: _group_selected(page))
    page.addAction(group_action)
    ungroup_action = QAction("Desagrupar", page)
    ungroup_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
    ungroup_action.triggered.connect(lambda: _ungroup_selected(page))
    page.addAction(ungroup_action)

    # Uma mudança nas camadas e nos objetos continua entrando no histórico V145.
    page.scene.changed.connect(lambda *_args: _schedule_history(page))
    page._v146_update_controls()
    page.status_label.setText(
        "V146: Ctrl+clique ou arraste para selecionar vários objetos; "
        "Ctrl+G agrupa e Ctrl+Shift+G desagrupa. Também há ajustes de fotografia, molduras, contorno e sombra."
    )
