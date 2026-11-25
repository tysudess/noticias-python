from __future__ import annotations

"""V152 — transformação em lote, espelhamento e estilos reutilizáveis.

Amplia o Estúdio V151 sem alterar o formato dos projetos .centralart. Usa
somente classes Qt e mecanismos de serialização já existentes nas camadas
V145–V151.
"""

from copy import deepcopy
import uuid

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QFont, QPen, QTransform
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import (
    EFFECT_DATA_KEY,
    FRAME_DATA_KEY,
    _apply_frame,
    _effect_from_data,
)
from monitor_noticias.ui.art_studio_v151 import _sync_controls as _v151_sync_controls


def _selected_roots(page) -> list[QGraphicsItem]:
    selected = list(page.scene.selectedItems())
    selected_set = set(selected)
    roots: list[QGraphicsItem] = []
    for item in selected:
        parent = item.parentItem()
        nested = False
        while parent is not None:
            if parent in selected_set:
                nested = True
                break
            parent = parent.parentItem()
        if not nested and item.data(ITEM_KIND_KEY) != "canvas-background":
            roots.append(item)
    return roots


def _editable_selection(page) -> tuple[list[QGraphicsItem], int]:
    roots = _selected_roots(page)
    editable = [item for item in roots if item.isVisible() and not bool(item.data(LOCKED_KEY))]
    return editable, len(roots) - len(editable)


def _move_scene_delta(item: QGraphicsItem, dx: float, dy: float) -> None:
    parent = item.parentItem()
    if parent is None:
        item.moveBy(float(dx), float(dy))
        return
    origin = parent.mapFromScene(QPointF(0.0, 0.0))
    target = parent.mapFromScene(QPointF(float(dx), float(dy)))
    item.moveBy(target.x() - origin.x(), target.y() - origin.y())


def _schedule_history(page) -> None:
    if getattr(page, "_v145_history_suspended", False):
        return
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.start()


def _refresh_after_batch(page, selected: list[QGraphicsItem], message: str) -> None:
    page._v145_active_item = selected[0] if selected else None
    page._refresh_layers(select_item=selected[0] if len(selected) == 1 else None)
    page._update_selection_controls(selected[0] if selected else None)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v149_sync_controls"):
        page._v149_sync_controls()
    page.status_label.setText(message)
    page.scene.update()
    _schedule_history(page)
    _sync_controls(page)
    _v151_sync_controls(page)


def _transform_selection(page, operation: str) -> None:
    items, skipped = _editable_selection(page)
    if not items:
        page.status_label.setText("Selecione objetos visíveis e desbloqueados para transformar.")
        return

    changed = 0
    for item in items:
        center_before = item.mapToScene(item.boundingRect().center())
        if operation in {"flip_h", "flip_v"}:
            transform = QTransform.fromScale(-1.0, 1.0) if operation == "flip_h" else QTransform.fromScale(1.0, -1.0)
            item.setTransform(transform, True)
        elif operation in {"rotate_left", "rotate_right"}:
            item.setTransformOriginPoint(item.boundingRect().center())
            delta = -90.0 if operation == "rotate_left" else 90.0
            item.setRotation(float(item.rotation()) + delta)
        else:
            page.status_label.setText("Transformação desconhecida.")
            return

        center_after = item.mapToScene(item.boundingRect().center())
        correction = center_before - center_after
        if abs(correction.x()) > 0.001 or abs(correction.y()) > 0.001:
            _move_scene_delta(item, correction.x(), correction.y())
        changed += 1

    labels = {
        "flip_h": "espelhados horizontalmente",
        "flip_v": "espelhados verticalmente",
        "rotate_left": "girados 90° à esquerda",
        "rotate_right": "girados 90° à direita",
    }
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _refresh_after_batch(page, items, f"{changed} objeto(s) {labels[operation]}{suffix}.")


def _apply_batch_opacity(page) -> None:
    items, skipped = _editable_selection(page)
    if not items:
        page.status_label.setText("Selecione objetos visíveis e desbloqueados para alterar a opacidade.")
        return
    opacity = max(0, min(100, int(page.v152_opacity_spin.value()))) / 100.0
    for item in items:
        item.setOpacity(opacity)
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _refresh_after_batch(page, items, f"Opacidade de {len(items)} objeto(s) ajustada para {round(opacity * 100)}%{suffix}.")


def _item_family(item: QGraphicsItem) -> str | None:
    if isinstance(item, QGraphicsTextItem):
        return "text"
    if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
        return "shape"
    if isinstance(item, QGraphicsPixmapItem):
        return "image"
    return None


def _copy_style(page) -> None:
    items, skipped = _editable_selection(page)
    if len(items) != 1:
        page.status_label.setText("Selecione exatamente um objeto desbloqueado para copiar seu estilo.")
        return
    item = items[0]
    family = _item_family(item)
    if family is None:
        page.status_label.setText("Este tipo de grupo não possui um estilo único para copiar.")
        return

    style: dict = {"family": family}
    if family == "text":
        style["font"] = QFont(item.font())
        style["text_color"] = item.defaultTextColor()
    elif family == "shape":
        style["brush"] = QBrush(item.brush())
        style["pen"] = QPen(item.pen())
    elif family == "image":
        frame = item.data(FRAME_DATA_KEY)
        style["frame"] = deepcopy(frame) if isinstance(frame, dict) else None

    effect = item.data(EFFECT_DATA_KEY)
    style["effect"] = deepcopy(effect) if isinstance(effect, dict) else None
    page._v152_style_clipboard = style
    page.v152_paste_style_button.setEnabled(True)
    name = str(item.data(ITEM_NAME_KEY) or "Objeto")
    page.status_label.setText(f"Estilo de '{name}' copiado. Selecione objetos compatíveis e aplique.")
    _sync_controls(page)


def _paste_style(page) -> None:
    style = getattr(page, "_v152_style_clipboard", None)
    if not isinstance(style, dict):
        page.status_label.setText("Copie o estilo de um objeto antes de aplicá-lo.")
        return
    items, skipped = _editable_selection(page)
    compatible = [item for item in items if _item_family(item) == style.get("family")]
    if not compatible:
        page.status_label.setText("Não há objetos selecionados compatíveis com o estilo copiado.")
        return

    for item in compatible:
        family = style["family"]
        if family == "text":
            item.setFont(QFont(style["font"]))
            item.setDefaultTextColor(style["text_color"])
        elif family == "shape":
            item.setBrush(QBrush(style["brush"]))
            item.setPen(QPen(style["pen"]))
        elif family == "image":
            _apply_frame(item, deepcopy(style.get("frame")))

        effect = style.get("effect")
        if isinstance(effect, dict):
            _effect_from_data(item, deepcopy(effect))
        else:
            item.setGraphicsEffect(None)
            item.setData(EFFECT_DATA_KEY, None)
        if family == "image":
            item.setData(FRAME_DATA_KEY, deepcopy(style.get("frame")))

    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _refresh_after_batch(page, compatible, f"Estilo aplicado a {len(compatible)} objeto(s) compatível(is){suffix}.")


def _renew_history_ids(item: QGraphicsItem) -> None:
    if item.data(HISTORY_ID_KEY):
        item.setData(HISTORY_ID_KEY, uuid.uuid4().hex)
    for child in item.childItems():
        _renew_history_ids(child)


def _duplicate_selection(page) -> None:
    items, skipped = _editable_selection(page)
    if not items:
        page.status_label.setText("Selecione objetos visíveis e desbloqueados para duplicar.")
        return
    clones: list[QGraphicsItem] = []
    highest_z = max((item.zValue() for item in page._content_items()), default=0.0)
    try:
        for index, item in enumerate(items):
            serialized = deepcopy(page._serialize_item(item))
            clone = page._build_item_from_data(serialized)
            clone.setPos(item.pos() + QPointF(24.0, 24.0))
            clone.setZValue(highest_z + index + 1.0)
            name = str(item.data(ITEM_NAME_KEY) or "Objeto")
            clone.setData(ITEM_NAME_KEY, f"{name} — cópia")
            _renew_history_ids(clone)
            page.scene.addItem(clone)
            clones.append(clone)
    except Exception as exc:
        # Remove apenas as cópias criadas nesta operação; os originais ficam intactos.
        for clone in clones:
            if clone.scene() is page.scene:
                page.scene.removeItem(clone)
        page.status_label.setText(f"Não foi possível duplicar a seleção: {exc}")
        return

    page.scene.clearSelection()
    for clone in clones:
        clone.setSelected(True)
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s) não duplicado(s)" if skipped else ""
    _refresh_after_batch(page, clones, f"{len(clones)} objeto(s) duplicado(s), incluindo grupos, com deslocamento de 24 px{suffix}.")


def _move_selection_to_extreme(page, direction: str) -> None:
    items, skipped = _editable_selection(page)
    if not items:
        page.status_label.setText("Selecione objetos visíveis e desbloqueados para organizar as camadas.")
        return
    all_items = [item for item in page._content_items() if item.parentItem() is None]
    selected = set(items)
    if direction == "front":
        base = max((item.zValue() for item in all_items), default=0.0)
        ordered = sorted(items, key=lambda item: item.zValue())
        for index, item in enumerate(ordered, 1):
            item.setZValue(base + index)
        label = "frente"
    else:
        base = min((item.zValue() for item in all_items), default=0.0)
        ordered = sorted(items, key=lambda item: item.zValue())
        for index, item in enumerate(ordered, 1):
            item.setZValue(base - len(ordered) + index - 1)
        label = "fundo"
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _refresh_after_batch(page, items, f"{len(items)} objeto(s) enviado(s) para a {label}{suffix}.")


def _sync_controls(page) -> None:
    if not getattr(page, "_v152_installed", False):
        return
    items, _skipped = _editable_selection(page)
    count = len(_selected_roots(page))
    has_selection = bool(items)
    page.v152_transform_buttons["flip_h"].setEnabled(has_selection)
    page.v152_transform_buttons["flip_v"].setEnabled(has_selection)
    page.v152_transform_buttons["rotate_left"].setEnabled(has_selection)
    page.v152_transform_buttons["rotate_right"].setEnabled(has_selection)
    page.v152_apply_opacity_button.setEnabled(has_selection)
    page.v152_duplicate_button.setEnabled(has_selection)
    page.v152_front_button.setEnabled(has_selection)
    page.v152_back_button.setEnabled(has_selection)
    family = _item_family(items[0]) if len(items) == 1 else None
    page.v152_copy_style_button.setEnabled(family is not None)
    clipboard = getattr(page, "_v152_style_clipboard", None)
    page.v152_paste_style_button.setEnabled(
        bool(items) and isinstance(clipboard, dict)
        and any(_item_family(item) == clipboard.get("family") for item in items)
    )
    page.v152_selection_label.setText(f"{count} objeto(s) selecionado(s) · {len(items)} editável(is)")
    if items:
        average = round(sum(item.opacity() * 100 for item in items) / len(items))
        page.v152_opacity_spin.blockSignals(True)
        page.v152_opacity_spin.setValue(average)
        page.v152_opacity_spin.blockSignals(False)


def _install_transform_panel(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    frame = QFrame(content)
    frame.setObjectName("artStudioTransformPanelV152")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(6)
    title = QLabel("TRANSFORMAÇÃO E EDIÇÃO EM LOTE")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    page.v152_selection_label = QLabel("0 objeto(s) selecionado(s)")
    page.v152_selection_label.setObjectName("muted")
    page.v152_selection_label.setWordWrap(True)
    box.addWidget(page.v152_selection_label)

    transform_grid = QGridLayout()
    transform_grid.setContentsMargins(0, 0, 0, 0)
    transform_grid.setHorizontalSpacing(5)
    transform_grid.setVerticalSpacing(5)
    page.v152_transform_buttons = {}
    specs = (
        ("flip_h", "Espelhar ↔", "Espelhar horizontalmente"),
        ("flip_v", "Espelhar ↕", "Espelhar verticalmente"),
        ("rotate_left", "Girar −90°", "Girar 90 graus à esquerda"),
        ("rotate_right", "Girar +90°", "Girar 90 graus à direita"),
    )
    for index, (key, label, tooltip) in enumerate(specs):
        button = QPushButton(label)
        button.setProperty("secondary", True)
        button.setMinimumHeight(32)
        button.setToolTip(tooltip + " os objetos selecionados.")
        button.clicked.connect(lambda _checked=False, action=key: _transform_selection(page, action))
        page.v152_transform_buttons[key] = button
        transform_grid.addWidget(button, index // 2, index % 2)
    box.addLayout(transform_grid)

    opacity_row = QHBoxLayout()
    opacity_row.addWidget(QLabel("Opacidade"))
    page.v152_opacity_spin = QSpinBox()
    page.v152_opacity_spin.setRange(0, 100)
    page.v152_opacity_spin.setSuffix(" %")
    page.v152_opacity_spin.setValue(100)
    opacity_row.addWidget(page.v152_opacity_spin, 1)
    box.addLayout(opacity_row)
    page.v152_apply_opacity_button = QPushButton("Aplicar opacidade à seleção")
    page.v152_apply_opacity_button.setProperty("secondary", True)
    box.addWidget(page.v152_apply_opacity_button)
    page.v152_apply_opacity_button.clicked.connect(lambda: _apply_batch_opacity(page))

    style_grid = QGridLayout()
    page.v152_copy_style_button = QPushButton("Copiar estilo")
    page.v152_paste_style_button = QPushButton("Aplicar estilo")
    page.v152_copy_style_button.setProperty("secondary", True)
    page.v152_paste_style_button.setProperty("secondary", True)
    style_grid.addWidget(page.v152_copy_style_button, 0, 0)
    style_grid.addWidget(page.v152_paste_style_button, 0, 1)
    box.addLayout(style_grid)
    page.v152_copy_style_button.clicked.connect(lambda: _copy_style(page))
    page.v152_paste_style_button.clicked.connect(lambda: _paste_style(page))

    page.v152_duplicate_button = QPushButton("Duplicar seleção")
    page.v152_front_button = QPushButton("Trazer seleção para frente")
    page.v152_back_button = QPushButton("Enviar seleção para trás")
    for button in (page.v152_duplicate_button, page.v152_front_button, page.v152_back_button):
        button.setProperty("secondary", True)
        button.setMinimumHeight(32)
        box.addWidget(button)
    page.v152_duplicate_button.clicked.connect(lambda: _duplicate_selection(page))
    page.v152_front_button.clicked.connect(lambda: _move_selection_to_extreme(page, "front"))
    page.v152_back_button.clicked.connect(lambda: _move_selection_to_extreme(page, "back"))

    hint = QLabel("As operações ignoram objetos bloqueados ou ocultos. A duplicação mantém os grupos e cria novos identificadores de histórico.")
    hint.setWordWrap(True)
    hint.setObjectName("muted")
    box.addWidget(hint)

    index = layout.indexOf(getattr(page, "v151_composition_frame", None))
    layout.insertWidget(index + 1 if index >= 0 else layout.count(), frame)
    page.v152_transform_frame = frame


def enhance_art_studio_page_v152(page) -> None:
    if getattr(page, "_v152_installed", False):
        return
    page._v152_installed = True
    page._v152_style_clipboard = None
    _install_transform_panel(page)
    if not hasattr(page, "v152_transform_frame"):
        page._v152_installed = False
        return
    page.scene.selectionChanged.connect(lambda: _sync_controls(page))
    page.layers.currentItemChanged.connect(lambda *_args: _sync_controls(page))
    _sync_controls(page)
    page.status_label.setText(
        "V152: espelhamento e rotação de vários objetos, opacidade em lote, "
        "cópia de estilos, duplicação de grupos e organização avançada de camadas."
    )


def install_art_studio_v152() -> None:
    """Conecta a V152 à página criada e ampliada pelas camadas anteriores."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v152_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v152(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v152(page)

    MainWindow.__init__ = init_with_v152
    MainWindow._v152_integration_installed = True
