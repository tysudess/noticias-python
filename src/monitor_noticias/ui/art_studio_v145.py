from __future__ import annotations

"""Recursos V145 do Estúdio de Artes.

O módulo amplia a página existente sem reescrever o editor V143/V144.
Todos os recursos usam os itens nativos do QGraphicsScene já empregados
pela Central e não acrescentam dependências externas.
"""

import json
import math
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QKeySequence,
    QPainter,
    QPen,
    QUndoCommand,
    QUndoStack,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_page import (
    CANVAS_BG_KEY,
    ITEM_KIND_KEY,
    ITEM_NAME_KEY,
)

LOCKED_KEY = 3
HISTORY_ID_KEY = 4


class _SceneStateCommand(QUndoCommand):
    def __init__(self, page, before: dict[str, Any], after: dict[str, Any], label: str) -> None:
        super().__init__(label)
        self._page = page
        self._before = deepcopy(before)
        self._after = deepcopy(after)
        self._first_redo = True

    def undo(self) -> None:
        self._page._v145_restore_snapshot(self._before)

    def redo(self) -> None:
        # QUndoStack chama redo() imediatamente ao receber push().
        if self._first_redo:
            self._first_redo = False
            return
        self._page._v145_restore_snapshot(self._after)


class _CropSelectionView(QGraphicsView):
    selectionChanged = Signal(QRectF)

    def __init__(self, pixmap, parent=None) -> None:
        self._scene = QGraphicsScene(parent)
        super().__init__(self._scene, parent)
        self._pixmap = pixmap
        self._scene.addPixmap(pixmap)
        self._bounds = QRectF(0, 0, pixmap.width(), pixmap.height())
        self._scene.setSceneRect(self._bounds)
        self._selection = self._scene.addRect(
            QRectF(),
            QPen(QColor("#F2B93B"), 3, Qt.PenStyle.DashLine),
        )
        self._selection.setZValue(10)
        self._drag_start: QPointF | None = None
        self._dragging = False
        self.setMinimumSize(520, 360)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#17293A"))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def fit_image(self) -> None:
        self.fitInView(self._bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self.fit_image)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            if self._bounds.contains(point):
                self._drag_start = point
                self._dragging = True
                self._selection.setRect(QRectF(point, point))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._dragging and self._drag_start is not None:
            point = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._drag_start, point).normalized().intersected(self._bounds)
            self._selection.setRect(rect)
            self.selectionChanged.emit(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            if self._drag_start is not None:
                point = self.mapToScene(event.position().toPoint())
                rect = QRectF(self._drag_start, point).normalized().intersected(self._bounds)
                self._selection.setRect(rect)
                self.selectionChanged.emit(rect)
            self._drag_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def crop_rect(self):
        return self._selection.rect().normalized().intersected(self._bounds)


class _ImageCropDialog(QDialog):
    def __init__(self, pixmap, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recortar imagem")
        self.setMinimumSize(620, 470)
        layout = QVBoxLayout(self)
        help_text = QLabel(
            "Arraste sobre a imagem para marcar a área que deseja manter. "
            "A imagem original do projeto não é alterada fora deste recorte."
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.view = _CropSelectionView(pixmap, self)
        layout.addWidget(self.view, 1)
        self.dimensions = QLabel(f"Imagem original: {pixmap.width()} × {pixmap.height()} px")
        layout.addWidget(self.dimensions)
        self.view.selectionChanged.connect(self._show_dimensions)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _show_dimensions(self, rect: QRectF) -> None:
        self.dimensions.setText(
            f"Área selecionada: {max(0, round(rect.width()))} × "
            f"{max(0, round(rect.height()))} px"
        )

    def crop_rect(self):
        rect = self.view.crop_rect()
        left = max(0, math.floor(rect.left()))
        top = max(0, math.floor(rect.top()))
        right = min(self.view._pixmap.width(), math.ceil(rect.right()))
        bottom = min(self.view._pixmap.height(), math.ceil(rect.bottom()))
        if right - left < 2 or bottom - top < 2:
            return None
        from PySide6.QtCore import QRect
        return QRect(left, top, right - left, bottom - top)


# ---------------------------------------------------------------------------
# Histórico de edição
# ---------------------------------------------------------------------------
def _ensure_item_ids(page) -> None:
    for item in page._content_items():
        if not item.data(HISTORY_ID_KEY):
            item.setData(HISTORY_ID_KEY, uuid.uuid4().hex)


def _snapshot(page) -> dict[str, Any]:
    _ensure_item_ids(page)
    project = deepcopy(page._project_data())
    for data, item in zip(project.get("items", []), page._content_items()):
        data["history_id"] = str(item.data(HISTORY_ID_KEY))
        data["visible"] = bool(item.isVisible())
        data["locked"] = bool(item.data(LOCKED_KEY))
    selected = [
        str(item.data(HISTORY_ID_KEY))
        for item in page.scene.selectedItems()
        if item.data(HISTORY_ID_KEY)
    ]
    return {
        "project": project,
        "selected": selected,
        "current_file": str(page.current_file) if page.current_file else None,
    }


def _snapshot_key(state: dict[str, Any]) -> str:
    # A seleção não cria um passo de histórico por si só.
    return json.dumps(state.get("project", {}), sort_keys=True, ensure_ascii=False)


def _restore_snapshot(page, state: dict[str, Any]) -> None:
    project = deepcopy(state.get("project") or {})
    canvas = project.get("canvas") or {}
    width = max(64, min(5000, int(canvas.get("width", 1080))))
    height = max(64, min(5000, int(canvas.get("height", 1080))))
    color = QColor(str(canvas.get("background", "#FFFFFFFF")))
    if not color.isValid():
        color = QColor("#FFFFFF")

    page._v145_history_suspended = True
    page._v145_history_timer.stop()
    try:
        page.scene.clear()
        page._width, page._height = width, height
        page._canvas_color = color
        page.scene.setSceneRect(QRectF(0, 0, width, height))
        page._canvas_item = QGraphicsRectItem(0, 0, width, height)
        page._canvas_item.setBrush(color)
        page._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        page._canvas_item.setZValue(-100000)
        page._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        page._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        page.scene.addItem(page._canvas_item)

        for data in project.get("items", []):
            item = page._build_item_from_data(data)
            page.scene.addItem(item)

        current_file = state.get("current_file")
        page.current_file = Path(current_file) if current_file else None
        page.project_label.setText(page.current_file.name if page.current_file else "Projeto sem título")
        page.width_spin.setValue(width)
        page.height_spin.setValue(height)
        page.canvas_size_label.setText(f"{width} × {height} px")

        ids = set(state.get("selected") or [])
        page.scene.clearSelection()
        selected_item = None
        for item in page._content_items():
            if str(item.data(HISTORY_ID_KEY)) in ids and item.isVisible():
                item.setSelected(True)
                selected_item = item
        page._v145_active_item = selected_item
        page._refresh_layers(select_item=selected_item)
        page._update_selection_controls(selected_item)
        page.view_fit()
        page.status_label.setText("Edição restaurada pelo histórico.")
    finally:
        page._v145_history_suspended = False
        page._v145_last_snapshot = _snapshot(page)


def _schedule_history_commit(page, *_args) -> None:
    if getattr(page, "_v145_history_suspended", False):
        return
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.start()


def _commit_history(page) -> None:
    if getattr(page, "_v145_history_suspended", False):
        return
    after = _snapshot(page)
    before = getattr(page, "_v145_last_snapshot", after)
    if _snapshot_key(before) != _snapshot_key(after):
        page._v145_history.push(
            _SceneStateCommand(page, before, after, "Alteração na arte")
        )
    page._v145_last_snapshot = after



def _undo(page) -> None:
    if page._v145_history_timer.isActive():
        page._v145_history_timer.stop()
        _commit_history(page)
    page._v145_history.undo()


def _redo(page) -> None:
    if page._v145_history_timer.isActive():
        page._v145_history_timer.stop()
        _commit_history(page)
    page._v145_history.redo()


# ---------------------------------------------------------------------------
# Camadas e ferramentas
# ---------------------------------------------------------------------------
def _active_item(page):
    item = page._v145_active_item
    if item is not None:
        try:
            if item.scene() is page.scene:
                return item
        except RuntimeError:
            page._v145_active_item = None
    selected = page.scene.selectedItems()
    if selected:
        return selected[0]
    current = page.layers.currentItem()
    if current is not None:
        try:
            key = int(current.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            key = -1
        item = page._layer_objects.get(key)
        if item is not None and item.scene() is page.scene:
            return item
    return None


def _refresh_layers(page, *args, **kwargs) -> None:
    original = page._v145_original_refresh_layers
    original(*args, **kwargs)
    for index in range(page.layers.count()):
        row = page.layers.item(index)
        try:
            key = int(row.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            continue
        item = page._layer_objects.get(key)
        if item is None or item.scene() is not page.scene:
            continue
        kind = str(item.data(ITEM_KIND_KEY) or "objeto")
        name = str(item.data(ITEM_NAME_KEY) or "Objeto")
        prefix = {"image": "▧", "text": "T", "shape": "▱"}.get(kind, "•")
        eye = "◉" if item.isVisible() else "○"
        lock = "  🔒" if bool(item.data(LOCKED_KEY)) else ""
        row.setText(f"{eye} {prefix}  {name}{lock}")


def _sync_active_item(page, *_args) -> None:
    if getattr(page, "_loading", False):
        return
    selected = page.scene.selectedItems()
    if selected:
        page._v145_active_item = selected[0]
    else:
        current = page.layers.currentItem()
        item = None
        if current is not None:
            try:
                key = int(current.data(Qt.ItemDataRole.UserRole))
            except (TypeError, ValueError):
                key = -1
            item = page._layer_objects.get(key)
        page._v145_active_item = item if item is not None and item.scene() is page.scene else None
    page._v145_update_v145_controls()


def _toggle_visibility(page) -> None:
    item = _active_item(page)
    if item is None:
        return
    item.setVisible(not item.isVisible())
    page._v145_active_item = item
    page._refresh_layers(select_item=item)
    page._update_selection_controls(item)
    page._v145_update_v145_controls()
    page.scene.update()
    _schedule_history_commit(page)


def _toggle_lock(page) -> None:
    item = _active_item(page)
    if item is None:
        return
    locked = not bool(item.data(LOCKED_KEY))
    item.setData(LOCKED_KEY, locked)
    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
    page._v145_active_item = item
    page._refresh_layers(select_item=item)
    page._update_selection_controls(item)
    page._v145_update_v145_controls()
    page.status_label.setText("Camada bloqueada para movimentação." if locked else "Camada desbloqueada.")
    page.scene.update()
    _schedule_history_commit(page)


def _crop_selected_image(page) -> None:
    item = _active_item(page)
    if (
        not isinstance(item, QGraphicsPixmapItem)
        or not item.isVisible()
        or bool(item.data(LOCKED_KEY))
    ):
        return
    dialog = _ImageCropDialog(item.pixmap(), page)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    rect = dialog.crop_rect()
    if rect is None:
        QMessageBox.information(page, "Recorte", "Marque uma área maior para aplicar o recorte.")
        return

    # Guarda a posição visual do canto superior esquerdo do recorte para que
    # a imagem permaneça no mesmo lugar, mesmo quando estava girada ou ampliada.
    target_scene_point = item.mapToScene(QPointF(rect.left(), rect.top()))
    cropped = item.pixmap().copy(rect)
    item.setPixmap(cropped)
    item.setTransformOriginPoint(item.boundingRect().center())
    mapped_origin = item.mapToScene(QPointF(0, 0))
    correction = target_scene_point - mapped_origin
    item.setPos(item.pos() + correction)
    page._v145_active_item = item
    page._refresh_layers(select_item=item)
    page._v145_update_v145_controls()
    page.status_label.setText(f"Imagem recortada para {rect.width()} × {rect.height()} px.")
    page.scene.update()
    _schedule_history_commit(page)


def _align_objects(page) -> None:
    selected = list(page.scene.selectedItems())
    if not selected:
        item = _active_item(page)
        if item is not None:
            selected = [item]
    selected = [item for item in selected if not bool(item.data(LOCKED_KEY))]
    if not selected:
        page.status_label.setText("Desbloqueie ao menos uma camada para alinhá-la.")
        return
    scene_rect = page.scene.sceneRect()
    mode = str(page.align_combo.currentData() or "center")
    for item in selected:
        bounds = item.sceneBoundingRect()
        if mode == "left":
            dx = scene_rect.left() - bounds.left()
            dy = 0
        elif mode == "right":
            dx = scene_rect.right() - bounds.right()
            dy = 0
        elif mode == "top":
            dx = 0
            dy = scene_rect.top() - bounds.top()
        elif mode == "bottom":
            dx = 0
            dy = scene_rect.bottom() - bounds.bottom()
        elif mode == "middle":
            dx = 0
            dy = scene_rect.center().y() - bounds.center().y()
        else:  # centro horizontal
            dx = scene_rect.center().x() - bounds.center().x()
            dy = 0
        item.moveBy(dx, dy)
    page._v145_active_item = selected[0]
    page._refresh_layers(select_item=selected[0])
    page._v145_update_v145_controls()
    page.status_label.setText("Alinhamento aplicado em relação ao canvas.")
    _schedule_history_commit(page)


def _update_controls(page) -> None:
    item = _active_item(page)
    valid = item is not None and item.scene() is page.scene
    page.v145_visibility_button.setEnabled(valid)
    page.v145_lock_button.setEnabled(valid)
    is_image = valid and isinstance(item, QGraphicsPixmapItem)
    locked = bool(item.data(LOCKED_KEY)) if valid else False
    page.v145_crop_button.setEnabled(bool(is_image and item.isVisible() and not locked))
    if not valid:
        page.v145_visibility_button.setText("Mostrar / ocultar")
        page.v145_lock_button.setText("Bloquear camada")
        return
    page.v145_visibility_button.setText("Ocultar camada" if item.isVisible() else "Mostrar camada")
    page.v145_lock_button.setText(
        "Desbloquear camada" if bool(item.data(LOCKED_KEY)) else "Bloquear camada"
    )


def _install_locked_item_guards(page) -> None:
    original_update = page._update_selection_controls

    def update_with_lock_guard(item):
        original_update(item)
        locked = item is not None and (
            bool(item.data(LOCKED_KEY)) or not item.isVisible()
        )
        for name in (
            "edit_text_button",
            "font_button",
            "color_button",
            "center_button",
            "apply_transform_button",
            "duplicate_button",
            "forward_button",
            "backward_button",
            "delete_button",
        ):
            button = getattr(page, name, None)
            if button is not None and locked:
                button.setEnabled(False)

    page._update_selection_controls = update_with_lock_guard

    original_delete = page.delete_selected

    def delete_with_lock_guard():
        item = _active_item(page)
        if item is not None and bool(item.data(LOCKED_KEY)):
            page.status_label.setText("Desbloqueie a camada antes de excluí-la.")
            return
        original_delete()

    page.delete_selected = delete_with_lock_guard
    for action in page.actions():
        if action.text() == "Excluir objeto":
            try:
                action.triggered.disconnect()
            except (RuntimeError, TypeError):
                pass
            action.triggered.connect(lambda _checked=False: delete_with_lock_guard())


def _install_history_toolbar(page) -> None:
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return
    page._v145_history = QUndoStack(page)
    page.undo_button = QPushButton("↶ Desfazer")
    page.redo_button = QPushButton("↷ Refazer")
    for button in (page.undo_button, page.redo_button):
        button.setProperty("secondary", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setEnabled(False)
        layout.insertWidget(max(0, layout.count() - 2), button)
    page.undo_button.clicked.connect(lambda: _undo(page))
    page.redo_button.clicked.connect(lambda: _redo(page))
    page._v145_history.canUndoChanged.connect(page.undo_button.setEnabled)
    page._v145_history.canRedoChanged.connect(page.redo_button.setEnabled)

    undo_action = QAction("Desfazer", page)
    undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    undo_action.triggered.connect(lambda: _undo(page))
    page.addAction(undo_action)
    redo_action = QAction("Refazer", page)
    redo_action.setShortcuts([QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Shift+Z")])
    redo_action.triggered.connect(lambda: _redo(page))
    page.addAction(redo_action)


def _install_layer_tools(page) -> None:
    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next((label.parentWidget() for label in labels if label.text() == "CAMADAS E OBJETOS"), None)
    layout = panel.layout() if panel is not None else None
    if layout is None:
        return

    page.v145_visibility_button = QPushButton("Mostrar / ocultar")
    page.v145_lock_button = QPushButton("Bloquear camada")
    page.v145_crop_button = QPushButton("Recortar imagem")
    page.v145_align_combo = QComboBox()
    page.v145_align_combo.addItem("Centro horizontal", "center")
    page.v145_align_combo.addItem("Alinhar à esquerda", "left")
    page.v145_align_combo.addItem("Alinhar à direita", "right")
    page.v145_align_combo.addItem("Alinhar ao topo", "top")
    page.v145_align_combo.addItem("Centro vertical", "middle")
    page.v145_align_combo.addItem("Alinhar à base", "bottom")
    page.v145_align_button = QPushButton("Alinhar ao canvas")

    for button in (
        page.v145_visibility_button,
        page.v145_lock_button,
        page.v145_crop_button,
        page.v145_align_button,
    ):
        button.setProperty("secondary", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
    page.v145_crop_button.setProperty("purple", True)

    actions = QFrame()
    actions_layout = QVBoxLayout(actions)
    actions_layout.setContentsMargins(0, 5, 0, 5)
    actions_layout.setSpacing(5)
    row = QHBoxLayout()
    row.addWidget(page.v145_visibility_button, 1)
    row.addWidget(page.v145_lock_button, 1)
    actions_layout.addLayout(row)
    actions_layout.addWidget(page.v145_crop_button)
    actions_layout.addWidget(QLabel("ALINHAMENTO"))
    align_row = QHBoxLayout()
    align_row.addWidget(page.v145_align_combo, 1)
    align_row.addWidget(page.v145_align_button)
    actions_layout.addLayout(align_row)

    index = layout.indexOf(page.layers)
    layout.insertWidget(index + 1, actions)
    page.v145_visibility_button.clicked.connect(lambda: _toggle_visibility(page))
    page.v145_lock_button.clicked.connect(lambda: _toggle_lock(page))
    page.v145_crop_button.clicked.connect(lambda: _crop_selected_image(page))
    page.v145_align_button.clicked.connect(lambda: _align_objects(page))
    _update_controls(page)


def enhance_art_studio_page(page) -> None:
    """Instala V145 uma única vez em uma ArtStudioPage já construída."""
    if getattr(page, "_v145_installed", False):
        return
    page._v145_installed = True
    page._v145_history_suspended = False
    page._v145_active_item = None

    # Estende o formato de projeto sem invalidar arquivos V143/V144.
    original_serialize = page._serialize_item
    def serialize_with_layer_state(item):
        data = original_serialize(item)
        data["history_id"] = str(item.data(HISTORY_ID_KEY) or uuid.uuid4().hex)
        item.setData(HISTORY_ID_KEY, data["history_id"])
        data["visible"] = bool(item.isVisible())
        data["locked"] = bool(item.data(LOCKED_KEY))
        return data
    page._serialize_item = serialize_with_layer_state

    original_build = page._build_item_from_data
    def build_with_layer_state(data):
        item = original_build(data)
        item.setData(HISTORY_ID_KEY, str(data.get("history_id") or uuid.uuid4().hex))
        locked = bool(data.get("locked", False))
        item.setData(LOCKED_KEY, locked)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
        item.setVisible(bool(data.get("visible", True)))
        return item
    page._build_item_from_data = build_with_layer_state

    page._v145_original_refresh_layers = page._refresh_layers
    page._refresh_layers = lambda *args, **kwargs: _refresh_layers(page, *args, **kwargs)
    page._v145_update_v145_controls = lambda: _update_controls(page)

    _install_history_toolbar(page)
    _install_layer_tools(page)
    _install_locked_item_guards(page)
    # O sinal Qt já havia conectado os métodos originais durante __init__.
    # Acrescentamos observadores auxiliares para sincronizar as ferramentas V145
    # sem duplicar a atualização de seleção existente no editor.
    page.scene.selectionChanged.connect(lambda: _sync_active_item(page))
    page.layers.currentItemChanged.connect(lambda current, previous: _sync_active_item(page, current, previous))

    page._v145_history_timer = QTimer(page)
    page._v145_history_timer.setSingleShot(True)
    page._v145_history_timer.setInterval(260)
    page._v145_history_timer.timeout.connect(lambda: _commit_history(page))
    page.scene.changed.connect(lambda *_args: _schedule_history_commit(page))
    page._v145_last_snapshot = _snapshot(page)

    # Qualquer alteração feita no canvas (inclusive arrastar, adicionar,
    # excluir, mudar cor/rotação/opacidade ou aplicar modelo) entra no histórico.
    page.status_label.setText(
        "V145: use Ctrl+Z para desfazer e Ctrl+Shift+Z para refazer. "
        "Selecione uma camada para ocultar, bloquear, recortar ou alinhar."
    )
