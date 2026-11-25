from __future__ import annotations

"""V150 — páginas, fundos avançados, biblioteca e guias inteligentes.

A camada amplia o Estúdio existente sem substituir V143–V149. Projetos antigos
(.centralart com canvas/items) continuam abrindo como documentos de uma página.
Usa somente PySide6 e Pillow, já presentes na Central.
"""

import base64
import json
import logging
import os
import tempfile
import uuid
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PySide6.QtCore import QBuffer, QEvent, QIODevice, QObject, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QLinearGradient,
    QPen,
    QPixmap,
    QPalette,
    QUndoStack,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabBar,
    QInputDialog,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import (
    CANVAS_BG_KEY,
    ITEM_KIND_KEY,
    ITEM_NAME_KEY,
    PROJECT_FORMAT,
    PROJECT_VERSION,
)
from monitor_noticias.ui.art_studio_v145 import _commit_history as _v145_commit_history
from monitor_noticias.ui.art_studio_v145 import _snapshot as _v145_snapshot
from monitor_noticias.ui.art_studio_v148 import RESIZE_HANDLE_KEY
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY
from monitor_noticias.ui.art_studio_v147 import InlineTextItem

log = logging.getLogger(__name__)

MAX_PAGES = 30
MAX_ITEMS_PER_PAGE = 500
MAX_BACKGROUND_BYTES = 20 * 1024 * 1024
MAX_BACKGROUND_PIXELS = 25_000_000
MAX_TOTAL_RENDER_PIXELS = 80_000_000


def _page_background_default(page) -> dict[str, Any]:
    return {
        "mode": "solid",
        "color": page._canvas_color.name(QColor.NameFormat.HexArgb),
    }


def _capture_page(page) -> dict[str, Any]:
    data = deepcopy(page._project_data())
    data["v150_background"] = deepcopy(
        getattr(page, "_v150_background", _page_background_default(page))
    )
    return data


def _image_to_base64(pixmap: QPixmap) -> str:
    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Não foi possível preparar a imagem de fundo.")
    if not pixmap.save(buffer, "PNG"):
        raise OSError("Não foi possível incorporar a imagem de fundo ao projeto.")
    raw = bytes(buffer.data())
    if len(raw) > MAX_BACKGROUND_BYTES:
        raise ValueError("A imagem de fundo excede o limite de 20 MB.")
    return base64.b64encode(raw).decode("ascii")


def _pixmap_from_base64(encoded: str) -> QPixmap:
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > MAX_BACKGROUND_BYTES:
        raise ValueError("A imagem de fundo excede o limite permitido.")
    pixmap = QPixmap()
    if not pixmap.loadFromData(raw, "PNG"):
        raise ValueError("A imagem de fundo do projeto está inválida.")
    return pixmap


def _gradient_brush(width: int, height: int, config: dict[str, Any]) -> QBrush:
    start = QColor(str(config.get("start", "#0B263D")))
    end = QColor(str(config.get("end", "#1D5B83")))
    if not start.isValid() or not end.isValid():
        raise ValueError("As cores do degradê são inválidas.")
    direction = str(config.get("direction", "Diagonal"))
    if direction == "Horizontal":
        gradient = QLinearGradient(0, 0, width, 0)
    elif direction == "Vertical":
        gradient = QLinearGradient(0, 0, 0, height)
    elif direction == "Diagonal inverso":
        gradient = QLinearGradient(width, 0, 0, height)
    else:
        gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, start)
    gradient.setColorAt(1.0, end)
    return QBrush(gradient)


def _remove_background_image(page) -> None:
    for item in list(page.scene.items()):
        if (
            item is not page._canvas_item
            and isinstance(item, QGraphicsPixmapItem)
            and item.data(ITEM_KIND_KEY) == CANVAS_BG_KEY
            and item.data(ITEM_NAME_KEY) == "Imagem de fundo"
        ):
            page.scene.removeItem(item)
            del item


def _apply_background(page, config: dict[str, Any] | None) -> None:
    config = deepcopy(config or _page_background_default(page))
    mode = str(config.get("mode", "solid"))
    _remove_background_image(page)

    if mode == "gradient":
        page._canvas_item.setBrush(_gradient_brush(page._width, page._height, config))
        page._canvas_color = QColor(str(config.get("start", "#0B263D")))
    elif mode == "image":
        pixmap = _pixmap_from_base64(str(config.get("image_png_base64", "")))
        scaled = pixmap.scaled(
            QSize(page._width, page._height),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        background = QGraphicsPixmapItem(scaled)
        background.setPos(
            (page._width - scaled.width()) / 2,
            (page._height - scaled.height()) / 2,
        )
        background.setZValue(-99999)
        background.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        background.setData(ITEM_NAME_KEY, "Imagem de fundo")
        background.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        background.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        page.scene.addItem(background)
        page._canvas_color = QColor("#FFFFFF")
        page._canvas_item.setBrush(QBrush(page._canvas_color))
    else:
        color = QColor(str(config.get("color", "#FFFFFFFF")))
        if not color.isValid():
            color = QColor("#FFFFFF")
        page._canvas_color = color
        page._canvas_item.setBrush(QBrush(color))

    page._v150_background = config
    page.scene.update()


def _install_history_snapshot_compatibility(page) -> None:
    """Inclui o fundo V150 no histórico e implementa o restaurador esperado por V145."""
    original_project_data = page._project_data

    def project_data_with_background() -> dict[str, Any]:
        data = original_project_data()
        data["v150_background"] = deepcopy(
            getattr(page, "_v150_background", _page_background_default(page))
        )
        return data

    page._project_data = project_data_with_background

    def restore_history_snapshot(state: dict[str, Any]) -> None:
        project = deepcopy(state.get("project") or {})
        _restore_page_data(page, project, fit=True, reset_history=False)

        current_file = state.get("current_file")
        page.current_file = Path(current_file) if current_file else None
        page.project_label.setText(
            page.current_file.name if page.current_file else "Projeto sem título"
        )

        selected_ids = {str(value) for value in (state.get("selected") or [])}
        page.scene.clearSelection()
        selected_item = None
        if selected_ids:
            for item in page._content_items():
                if str(item.data(HISTORY_ID_KEY) or "") in selected_ids and item.isVisible():
                    item.setSelected(True)
                    selected_item = item
                    break
        page._v145_active_item = selected_item
        page._refresh_layers(select_item=selected_item)
        page._update_selection_controls(selected_item)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        if hasattr(page, "v149_sync_controls"):
            page.v149_sync_controls()
        page._v145_last_snapshot = _v145_snapshot(page)
        page.status_label.setText("Alteração restaurada pelo histórico.")

    # O comando de histórico V145 chama esta função em undo/redo.
    page._v145_restore_snapshot = restore_history_snapshot


def _reset_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.stop()
    history = getattr(page, "_v145_history", None)
    if history is not None:
        history.clear()
    try:
        page._v145_last_snapshot = _v145_snapshot(page)
    except Exception:
        log.exception("Não foi possível reiniciar o histórico de edição V150")


def _restore_page_data(
    page,
    data: dict[str, Any],
    *,
    fit: bool = True,
    reset_history: bool = True,
) -> None:
    canvas = data.get("canvas") or {}
    width = max(64, min(5000, int(canvas.get("width", 1080))))
    height = max(64, min(5000, int(canvas.get("height", 1080))))
    color = QColor(str(canvas.get("background", "#FFFFFFFF")))
    if not color.isValid():
        color = QColor("#FFFFFF")
    items = data.get("items", [])
    if not isinstance(items, list) or len(items) > MAX_ITEMS_PER_PAGE:
        raise ValueError(f"Cada página pode conter até {MAX_ITEMS_PER_PAGE} objetos.")

    previous_restoring = getattr(page, "_v150_restoring", False)
    previous_history_suspended = getattr(page, "_v145_history_suspended", False)
    page._v150_restoring = True
    page._v145_history_suspended = True
    try:
        if hasattr(page, "_v148_handles"):
            page._v148_handles = []
        _clear_guides(page)
        _clear_grid(page)
        for overlay in list(getattr(page, "_v150_overlay_items", [])):
            try:
                if overlay.scene() is page.scene:
                    page.scene.removeItem(overlay)
            except RuntimeError:
                pass
        page._v150_overlay_items = []
        page.scene.clear()
        page._width, page._height = width, height
        page._canvas_color = color
        page.scene.setSceneRect(QRectF(0, 0, width, height))
        page._canvas_item = QGraphicsRectItem(0, 0, width, height)
        page._canvas_item.setBrush(QBrush(color))
        page._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        page._canvas_item.setZValue(-100000)
        page._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        page._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        page.scene.addItem(page._canvas_item)

        _apply_background(page, data.get("v150_background"))
        for item_data in items:
            item = page._build_item_from_data(item_data)
            page.scene.addItem(item)
            stack = [item]
            while stack:
                current = stack.pop()
                if isinstance(current, InlineTextItem):
                    current._v148_page = page
                stack.extend(current.childItems())

        page.width_spin.setValue(width)
        page.height_spin.setValue(height)
        page.canvas_size_label.setText(f"{width} × {height} px")
        page.scene.clearSelection()
        page._refresh_layers()
        page._update_selection_controls(None)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
            page._v148_update_dimensions()
        if hasattr(page, "v149_sync_controls"):
            page.v149_sync_controls()
        if fit:
            page.view_fit()
    finally:
        page._v145_history_suspended = previous_history_suspended
        page._v150_restoring = previous_restoring
    if reset_history:
        _reset_history(page)
    if getattr(page, "v150_grid_check", None) is not None and page.v150_grid_check.isChecked():
        _set_grid(page, True)
    page.scene.update()


def _validate_document(page, raw: dict[str, Any]) -> list[dict[str, Any]]:
    pages_raw = raw.get("pages")
    if "pages" in raw and not isinstance(pages_raw, list):
        raise ValueError("A lista de páginas do projeto está inválida.")
    if "pages" not in raw:
        # Compatibilidade total: documentos V143–V149 têm canvas/items na raiz.
        pages_raw = [{"name": "Página 1", "data": _legacy_page_data(raw)}]
    if not 1 <= len(pages_raw) <= MAX_PAGES:
        raise ValueError(f"O projeto deve conter entre 1 e {MAX_PAGES} páginas.")

    validated: list[dict[str, Any]] = []
    seen_page_ids: set[str] = set()
    for index, entry in enumerate(pages_raw, 1):
        if not isinstance(entry, dict):
            raise ValueError(f"A página {index} possui uma estrutura inválida.")
        data = entry.get("data")
        if not isinstance(data, dict):
            # Aceita também uma representação direta para facilitar intercâmbio.
            data = {key: value for key, value in entry.items() if key != "name"}
        canvas = data.get("canvas") or {}
        width = int(canvas.get("width", 1080))
        height = int(canvas.get("height", 1080))
        if not (64 <= width <= 5000 and 64 <= height <= 5000):
            raise ValueError(f"Dimensões inválidas na página {index}.")
        canvas_color = QColor(str(canvas.get("background", "#FFFFFFFF")))
        if not canvas_color.isValid():
            raise ValueError(f"A cor base do canvas da página {index} é inválida.")
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) > MAX_ITEMS_PER_PAGE:
            raise ValueError(f"A página {index} excede o limite de objetos.")
        bg = data.get("v150_background") or {"mode": "solid", "color": canvas_color.name(QColor.NameFormat.HexArgb)}
        mode = str(bg.get("mode", "solid"))
        if mode == "solid":
            if not QColor(str(bg.get("color", canvas_color.name()))).isValid():
                raise ValueError(f"A cor do fundo da página {index} é inválida.")
        elif mode == "gradient":
            if not QColor(str(bg.get("start", "#0B263D"))).isValid() or not QColor(str(bg.get("end", "#1D5B83"))).isValid():
                raise ValueError(f"As cores do degradê da página {index} são inválidas.")
            if str(bg.get("direction", "Diagonal")) not in {"Diagonal", "Horizontal", "Vertical", "Diagonal inverso"}:
                raise ValueError(f"A direção do degradê da página {index} é inválida.")
        elif mode == "image":
            encoded = str(bg.get("image_png_base64", ""))
            raw_image = base64.b64decode(encoded, validate=True)
            if len(raw_image) > MAX_BACKGROUND_BYTES:
                raise ValueError(f"A imagem de fundo da página {index} excede 20 MB.")
            background_pixmap = _pixmap_from_base64(encoded)
            if background_pixmap.isNull():
                raise ValueError(f"A imagem de fundo da página {index} não pôde ser lida.")
            if background_pixmap.width() * background_pixmap.height() > MAX_BACKGROUND_PIXELS:
                raise ValueError(f"A imagem de fundo da página {index} excede 25 milhões de pixels.")
            del background_pixmap
        else:
            raise ValueError(f"Tipo de fundo desconhecido na página {index}.")
        # Verifica a capacidade de reconstrução de cada camada antes de trocar
        # a arte em uso. Os objetos temporários não são inseridos na cena.
        for item_data in items:
            built = page._build_item_from_data(item_data)
            del built
        normalized = deepcopy(data)
        normalized["v150_background"] = deepcopy(bg)
        page_id = str(entry.get("id") or uuid.uuid4().hex)
        if page_id in seen_page_ids:
            page_id = uuid.uuid4().hex
        seen_page_ids.add(page_id)
        validated.append({
            "id": page_id,
            "name": str(entry.get("name") or f"Página {index}")[:80],
            "data": normalized,
        })
    return validated


def _legacy_page_data(raw: dict[str, Any]) -> dict[str, Any]:
    canvas = raw.get("canvas") or {}
    return {
        "canvas": deepcopy(canvas),
        "items": deepcopy(raw.get("items") or []),
        "v150_background": deepcopy(
            raw.get("v150_background")
            or {"mode": "solid", "color": canvas.get("background", "#FFFFFFFF")}
        ),
    }


def _update_tabs(page) -> None:
    bar = page.v150_tab_bar
    page._v150_tab_guard = True
    try:
        bar.blockSignals(True)
        while bar.count():
            bar.removeTab(0)
        for entry in page._v150_pages:
            bar.addTab(str(entry.get("name") or "Página"))
        bar.setCurrentIndex(page._v150_active_index)
        bar.blockSignals(False)
    finally:
        bar.blockSignals(False)
        page._v150_tab_guard = False
    page.v150_page_count_label.setText(f"{len(page._v150_pages)} páginas")


def _capture_active_page(page) -> None:
    if getattr(page, "_v150_restoring", False):
        return
    if not getattr(page, "_v150_pages", None):
        return
    page._v150_pages[page._v150_active_index]["data"] = _capture_page(page)


def _flush_active_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and timer.isActive():
        timer.stop()
        _v145_commit_history(page)


def _bind_history_stack(page, stack) -> None:
    current = getattr(page, "_v145_history", None)
    undo_slot = getattr(page, "_v150_undo_state_slot", None)
    redo_slot = getattr(page, "_v150_redo_state_slot", None)
    if current is stack:
        page.undo_button.setEnabled(stack.canUndo())
        page.redo_button.setEnabled(stack.canRedo())
        return
    if current is not None:
        if undo_slot is not None:
            try:
                current.canUndoChanged.disconnect(undo_slot)
            except (RuntimeError, TypeError):
                pass
        if redo_slot is not None:
            try:
                current.canRedoChanged.disconnect(redo_slot)
            except (RuntimeError, TypeError):
                pass
    page._v145_history = stack
    if undo_slot is None:
        undo_slot = page.undo_button.setEnabled
        redo_slot = page.redo_button.setEnabled
        page._v150_undo_state_slot = undo_slot
        page._v150_redo_state_slot = redo_slot
    stack.canUndoChanged.connect(undo_slot)
    stack.canRedoChanged.connect(redo_slot)
    page.undo_button.setEnabled(stack.canUndo())
    page.redo_button.setEnabled(stack.canRedo())


def _activate_page_history(page, entry: dict[str, Any]) -> None:
    entry_id = str(entry.get("id") or "")
    if not entry_id:
        entry_id = uuid.uuid4().hex
        entry["id"] = entry_id
    histories = page._v150_page_histories
    stack = histories.get(entry_id)
    if stack is None:
        stack = QUndoStack(page)
        histories[entry_id] = stack
    _bind_history_stack(page, stack)


def _mark_history_baseline(page) -> None:
    page._v145_last_snapshot = _v145_snapshot(page)


def _switch_page(page, index: int) -> None:
    if getattr(page, "_v150_tab_guard", False):
        return
    if not 0 <= index < len(page._v150_pages) or index == page._v150_active_index:
        return
    _flush_active_history(page)
    _capture_active_page(page)
    page._v150_active_index = index
    entry = page._v150_pages[index]
    _activate_page_history(page, entry)
    _restore_page_data(page, entry["data"], reset_history=False)
    _mark_history_baseline(page)
    page._v150_update_page_chrome()
    page.status_label.setText(f"Exibindo {entry['name']}. O histórico desta página foi preservado.")


def _add_page(page) -> None:
    if len(page._v150_pages) >= MAX_PAGES:
        QMessageBox.information(page, "Limite de páginas", f"O Estúdio permite até {MAX_PAGES} páginas por projeto.")
        return
    _flush_active_history(page)
    _capture_active_page(page)
    active = page._v150_pages[page._v150_active_index]["data"]
    blank = deepcopy(active)
    blank["items"] = []
    name = f"Página {len(page._v150_pages) + 1}"
    entry = {"id": uuid.uuid4().hex, "name": name, "data": blank}
    page._v150_pages.append(entry)
    page._v150_active_index = len(page._v150_pages) - 1
    _activate_page_history(page, entry)
    _update_tabs(page)
    _restore_page_data(page, blank, reset_history=False)
    _mark_history_baseline(page)
    page._v150_update_page_chrome()
    page.status_label.setText(f"{name} criada. O histórico de cada página é independente.")


def _duplicate_page(page) -> None:
    if len(page._v150_pages) >= MAX_PAGES:
        QMessageBox.information(page, "Limite de páginas", f"O Estúdio permite até {MAX_PAGES} páginas por projeto.")
        return
    _flush_active_history(page)
    _capture_active_page(page)
    source = page._v150_pages[page._v150_active_index]
    clone = deepcopy(source)
    clone["id"] = uuid.uuid4().hex
    clone["name"] = f"{source['name']} — cópia"
    page._v150_pages.insert(page._v150_active_index + 1, clone)
    page._v150_active_index += 1
    _activate_page_history(page, clone)
    _update_tabs(page)
    _restore_page_data(page, clone["data"], reset_history=False)
    _mark_history_baseline(page)
    page._v150_update_page_chrome()
    page.status_label.setText("Página duplicada com todos os seus elementos e histórico independente.")


def _delete_page(page, index: int) -> None:
    if len(page._v150_pages) <= 1:
        page.status_label.setText("O projeto precisa manter pelo menos uma página.")
        return
    if not 0 <= index < len(page._v150_pages):
        return
    name = page._v150_pages[index]["name"]
    answer = QMessageBox.question(
        page,
        "Excluir página",
        f"Deseja excluir '{name}'? Essa ação será registrada no projeto ao salvar.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return

    _flush_active_history(page)
    _capture_active_page(page)
    old_active = page._v150_active_index
    deleted_was_active = index == old_active
    deleted = page._v150_pages.pop(index)
    deleted_stack = page._v150_page_histories.pop(str(deleted.get("id") or ""), None)
    if deleted_stack is not None:
        deleted_stack.clear()
        deleted_stack.deleteLater()

    if index < old_active:
        old_active -= 1
    elif deleted_was_active:
        old_active = min(index, len(page._v150_pages) - 1)
    page._v150_active_index = max(0, min(old_active, len(page._v150_pages) - 1))
    _update_tabs(page)

    # Excluir uma página fora do foco não deve reconstruir nem limpar o histórico da atual.
    if not deleted_was_active:
        page._v150_update_page_chrome()
        page.status_label.setText(f"Página '{name}' excluída.")
        return

    entry = page._v150_pages[page._v150_active_index]
    _activate_page_history(page, entry)
    _restore_page_data(page, entry["data"], reset_history=False)
    _mark_history_baseline(page)
    page._v150_update_page_chrome()
    page.status_label.setText(f"Página '{name}' excluída.")


def _rename_page(page) -> None:
    current = page._v150_pages[page._v150_active_index]["name"]
    value, accepted = QInputDialog.getText(page, "Renomear página", "Nome da página:", text=current)
    if not accepted or not value.strip():
        return
    page._v150_pages[page._v150_active_index]["name"] = value.strip()[:80]
    _update_tabs(page)
    page.v150_tab_bar.setCurrentIndex(page._v150_active_index)
    page._v150_update_page_chrome()
    page.status_label.setText("Nome da página atualizado.")


def _tab_moved(page, source: int, target: int) -> None:
    if getattr(page, "_v150_tab_guard", False) or source == target:
        return
    _capture_active_page(page)
    active_entry = page._v150_pages[page._v150_active_index]
    moved = page._v150_pages.pop(source)
    page._v150_pages.insert(target, moved)
    page._v150_active_index = next(
        index for index, entry in enumerate(page._v150_pages) if entry is active_entry
    )
    _update_tabs(page)  # recria os botões de fechar com os índices atualizados
    page._v150_update_page_chrome()


def _document_payload(page) -> dict[str, Any]:
    _capture_active_page(page)
    active = page._v150_pages[page._v150_active_index]["data"]
    payload = {
        "format": PROJECT_FORMAT,
        "version": PROJECT_VERSION,
        "canvas": deepcopy(active.get("canvas", {})),
        "items": deepcopy(active.get("items", [])),
        "v150_background": deepcopy(active.get("v150_background", {})),
        "pages": deepcopy(page._v150_pages),
        "active_page_index": int(page._v150_active_index),
        "v150_document_version": 1,
    }
    return payload


def _save_project(page) -> None:
    if page.current_file is None:
        path, _ = QFileDialog.getSaveFileName(
            page,
            "Salvar projeto de arte",
            str(page.projects_dir / "Minha arte.centralart"),
            "Projeto da Central (*.centralart)",
        )
        if not path:
            return
        page.current_file = Path(path)
        if page.current_file.suffix.lower() != ".centralart":
            page.current_file = page.current_file.with_suffix(".centralart")
    try:
        payload = json.dumps(_document_payload(page), ensure_ascii=False, indent=2)
        page.current_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{page.current_file.name}.", suffix=".tmp", dir=str(page.current_file.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, page.current_file)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
    except Exception as exc:
        log.exception("Falha ao salvar projeto multipágina do Estúdio")
        QMessageBox.critical(page, "Erro ao salvar", f"Não foi possível salvar o projeto.\n\n{exc}")
        return
    page.project_label.setText(page.current_file.name)
    page.status_label.setText(f"Projeto com {len(page._v150_pages)} páginas salvo: {page.current_file.name}")
    page.project_changed.emit(str(page.current_file))


def _open_project(page) -> None:
    path, _ = QFileDialog.getOpenFileName(
        page, "Abrir projeto de arte", str(page.projects_dir), "Projeto da Central (*.centralart *.json)"
    )
    if not path:
        return
    if page._content_items() or len(page._v150_pages) > 1:
        answer = QMessageBox.question(
            page,
            "Abrir outro projeto",
            "O documento atual será substituído. Salve-o antes, se desejar mantê-lo. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
    try:
        project_path = Path(path)
        if project_path.stat().st_size > 250 * 1024 * 1024:
            raise ValueError("O projeto excede o limite de segurança de 250 MB.")
        raw = json.loads(project_path.read_text(encoding="utf-8"))
        if raw.get("format") != PROJECT_FORMAT:
            raise ValueError("Esse arquivo não é um projeto compatível do Estúdio de Artes.")
        if int(raw.get("version", 0)) > PROJECT_VERSION:
            raise ValueError("O projeto foi criado por uma versão mais recente do Estúdio de Artes.")
        pages = _validate_document(page, raw)
        active = max(0, min(len(pages) - 1, int(raw.get("active_page_index", 0))))
    except Exception as exc:
        log.exception("Falha ao abrir projeto multipágina")
        QMessageBox.critical(page, "Não foi possível abrir", str(exc))
        return

    current_stack = page._v145_history
    for stack in set(page._v150_page_histories.values()):
        stack.clear()
        if stack is not current_stack:
            stack.deleteLater()
    current_stack.clear()
    page._v150_pages = pages
    page._v150_active_index = active
    page._v150_page_histories = {pages[active]["id"]: current_stack}
    _bind_history_stack(page, current_stack)
    page.current_file = Path(path)
    _update_tabs(page)
    _restore_page_data(page, pages[active]["data"], reset_history=False)
    _mark_history_baseline(page)
    page.project_label.setText(page.current_file.name)
    page._v150_update_page_chrome()
    page.status_label.setText(f"Projeto aberto: {page.current_file.name} · {len(pages)} páginas")


def _new_project(page) -> None:
    if page._content_items() or len(page._v150_pages) > 1:
        answer = QMessageBox.question(
            page,
            "Criar nova arte",
            "Deseja encerrar o documento atual e começar um novo? Salve-o antes, se necessário.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
    blank = {
        "canvas": {"width": 1080, "height": 1080, "background": "#FFFFFFFF"},
        "items": [],
        "v150_background": {"mode": "solid", "color": "#FFFFFFFF"},
    }
    _flush_active_history(page)
    current_stack = page._v145_history
    for stack in set(page._v150_page_histories.values()):
        stack.clear()
        if stack is not current_stack:
            stack.deleteLater()
    current_stack.clear()
    page._v150_pages = [{"id": uuid.uuid4().hex, "name": "Página 1", "data": blank}]
    page._v150_page_histories = {page._v150_pages[0]["id"]: current_stack}
    _bind_history_stack(page, current_stack)
    page._v150_active_index = 0
    page.current_file = None
    _update_tabs(page)
    _restore_page_data(page, blank, reset_history=False)
    _mark_history_baseline(page)
    page.project_label.setText("Projeto sem título")
    page._v150_update_page_chrome()
    page.status_label.setText("Novo documento iniciado.")


def _choose_solid_background(page) -> None:
    color = QColorDialog.getColor(page._canvas_color, page, "Cor do fundo da página")
    if not color.isValid():
        return
    _apply_background(page, {"mode": "solid", "color": color.name(QColor.NameFormat.HexArgb)})
    _capture_active_page(page)
    _schedule_history(page)
    page.status_label.setText("Fundo sólido aplicado à página atual.")


def _choose_gradient_background(page) -> None:
    first = QColorDialog.getColor(QColor("#0B263D"), page, "Primeira cor do degradê")
    if not first.isValid():
        return
    second = QColorDialog.getColor(QColor("#1D5B83"), page, "Segunda cor do degradê")
    if not second.isValid():
        return
    directions = ["Diagonal", "Horizontal", "Vertical", "Diagonal inverso"]
    direction, accepted = QInputDialog.getItem(page, "Direção do degradê", "Escolha a direção:", directions, 0, False)
    if not accepted:
        return
    config = {
        "mode": "gradient",
        "start": first.name(QColor.NameFormat.HexArgb),
        "end": second.name(QColor.NameFormat.HexArgb),
        "direction": direction,
    }
    _apply_background(page, config)
    _capture_active_page(page)
    _schedule_history(page)
    page.status_label.setText("Degradê aplicado e incluído no projeto.")


def _choose_background_image(page) -> None:
    path, _ = QFileDialog.getOpenFileName(
        page, "Escolher imagem de fundo", str(Path.home()), "Imagens (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"
    )
    if not path:
        return
    pixmap = QPixmap(path)
    if pixmap.isNull():
        QMessageBox.warning(page, "Imagem inválida", "Não foi possível abrir a imagem escolhida.")
        return
    if pixmap.width() * pixmap.height() > MAX_BACKGROUND_PIXELS:
        QMessageBox.warning(page, "Imagem muito grande", "A imagem de fundo deve ter até 25 milhões de pixels.")
        return
    try:
        encoded = _image_to_base64(pixmap)
        config = {"mode": "image", "image_png_base64": encoded, "source_name": Path(path).name, "fit": "cover"}
        _apply_background(page, config)
    except Exception as exc:
        QMessageBox.warning(page, "Fundo não aplicado", str(exc))
        return
    _capture_active_page(page)
    _schedule_history(page)
    page.status_label.setText(f"Imagem '{Path(path).name}' aplicada como fundo da página.")


def _install_background_tools(page) -> None:
    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next((label.parentWidget() for label in labels if label.text() == "ELEMENTOS"), None)
    layout = panel.layout() if panel is not None else None
    if layout is None:
        return
    title = QLabel("FUNDOS AVANÇADOS")
    title.setObjectName("artSmallLabel")
    insert_at = max(0, layout.count() - 1)  # antes do stretch original do painel
    layout.insertSpacing(insert_at, 8)
    layout.insertWidget(insert_at + 1, title)
    insert_at += 2
    page.v150_solid_bg_button = QPushButton("Cor sólida")
    page.v150_gradient_bg_button = QPushButton("Degradê")
    page.v150_image_bg_button = QPushButton("Imagem de fundo")
    for button in (page.v150_solid_bg_button, page.v150_gradient_bg_button, page.v150_image_bg_button):
        button.setProperty("secondary", True)
        button.setMinimumHeight(34)
        layout.insertWidget(insert_at, button)
        insert_at += 1
    page.v150_solid_bg_button.clicked.connect(lambda: _choose_solid_background(page))
    page.v150_gradient_bg_button.clicked.connect(lambda: _choose_gradient_background(page))
    page.v150_image_bg_button.clicked.connect(lambda: _choose_background_image(page))


def _insert_library_asset(page, asset: str) -> None:
    from PySide6.QtGui import QFont

    presets = {
        "Etiqueta": ("ETIQUETA", "rect", 420, 135, "#D6B66D", "#102A43", 38),
        "Faixa de título": ("TÍTULO EM DESTAQUE", "rect", 760, 150, "#0B263D", "#FFFFFF", 48),
        "Selo": ("SELO", "ellipse", 270, 270, "#D6B66D", "#102A43", 42),
        "Botão": ("SAIBA MAIS", "rect", 390, 112, "#1677E8", "#FFFFFF", 34),
        "Chamada": ("INFORMAÇÃO IMPORTANTE", "rect", 700, 230, "#102A43", "#FFFFFF", 42),
        "Número": ("01", "ellipse", 190, 190, "#1677E8", "#FFFFFF", 68),
    }
    text, shape, width, height, fill, foreground, font_size = presets[asset]
    if shape == "ellipse":
        background: QGraphicsItem = QGraphicsEllipseItem(QRectF(0, 0, width, height))
    else:
        background = QGraphicsRectItem(QRectF(0, 0, width, height))
    background.setBrush(QBrush(QColor(fill)))
    background.setPen(QPen(Qt.PenStyle.NoPen))
    background.setData(ITEM_KIND_KEY, "shape")
    background.setData(ITEM_NAME_KEY, f"{asset} · fundo")
    background.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
    background.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    text_item = InlineTextItem(text)
    text_item._v148_page = page
    text_item.setData(ITEM_KIND_KEY, "text")
    text_item.setData(ITEM_NAME_KEY, f"{asset} · texto")
    font = QFont("Segoe UI")
    font.setPixelSize(font_size)
    font.setBold(True)
    text_item.setFont(font)
    text_item.setDefaultTextColor(QColor(foreground))
    text_item.setTextWidth(width * 0.88)
    bounds = text_item.boundingRect()
    text_item.setPos((width - bounds.width()) / 2, (height - bounds.height()) / 2)
    text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
    text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    group = page.scene.createItemGroup([background, text_item])
    group.setData(ITEM_KIND_KEY, "group")
    group.setData(ITEM_NAME_KEY, asset)
    group.setTransformOriginPoint(group.boundingRect().center())
    group.setPos((page._width - group.boundingRect().width()) / 2, (page._height - group.boundingRect().height()) / 2)
    page._make_movable(group, "group", asset)
    page.status_label.setText(f"Elemento '{asset}' inserido. Edite o texto com duplo clique.")
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()


def _install_element_library(page) -> None:
    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next((label.parentWidget() for label in labels if label.text() == "ELEMENTOS"), None)
    layout = panel.layout() if panel is not None else None
    if layout is None:
        return
    title = QLabel("BIBLIOTECA DE ELEMENTOS")
    title.setObjectName("artSmallLabel")
    insert_at = max(0, layout.count() - 1)  # antes do stretch original do painel
    layout.insertSpacing(insert_at, 8)
    layout.insertWidget(insert_at + 1, title)
    insert_at += 2
    for asset in ("Etiqueta", "Faixa de título", "Selo", "Botão", "Chamada", "Número"):
        button = QPushButton(asset)
        button.setProperty("secondary", True)
        button.setMinimumHeight(32)
        button.clicked.connect(lambda _checked=False, name=asset: _insert_library_asset(page, name))
        layout.insertWidget(insert_at, button)
        insert_at += 1


def _install_left_panel_scroll(page) -> None:
    labels = page.findChildren(QLabel, "artPanelTitle")
    panel = next((label.parentWidget() for label in labels if label.text() == "ELEMENTOS"), None)
    layout = panel.layout() if panel is not None else None
    if layout is None or panel.property("v150Scrollable"):
        return
    title_item = layout.takeAt(0)
    title = title_item.widget() if title_item is not None else None
    if title_item is not None:
        del title_item
    content = QWidget()
    content.setObjectName("artStudioElementsContent")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(2, 4, 2, 6)
    content_layout.setSpacing(6)
    while layout.count():
        entry = layout.takeAt(0)
        widget = entry.widget()
        child_layout = entry.layout()
        if widget is not None:
            content_layout.addWidget(widget)
        elif child_layout is not None:
            content_layout.addLayout(child_layout)
        else:
            content_layout.addItem(entry)
    for button in content.findChildren(QPushButton):
        button.setMinimumHeight(max(32, button.minimumHeight()))
        from PySide6.QtWidgets import QSizePolicy
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    scroll = QScrollArea(panel)
    scroll.setObjectName("artStudioElementsScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(content)
    scroll.setStyleSheet(
        "QScrollArea#artStudioElementsScroll {background:transparent;border:0;}"
        "QScrollBar:vertical {width:7px;background:transparent;margin:2px;}"
        "QScrollBar::handle:vertical {background:#45647D;border-radius:3px;min-height:28px;}"
    )
    if title is not None:
        layout.addWidget(title)
    layout.addWidget(scroll, 1)
    panel.setProperty("v150Scrollable", True)


def _install_pages_bar(page) -> None:
    root = page.layout()
    if root is None:
        return
    bar = QFrame(page)
    bar.setObjectName("artStudioPagesBar")
    window_color = page.palette().color(QPalette.ColorRole.Window)
    dark_theme = window_color.lightness() < 128
    bar_background = "#132B3F" if dark_theme else "#EAF0F7"
    bar_border = "#37536B" if dark_theme else "#C7D5E4"
    tab_background = "#17344D" if dark_theme else "#FFFFFF"
    tab_foreground = "#DCE7EF" if dark_theme else "#18334A"
    selected_background = "#D6B66D" if dark_theme else "#E7D19A"
    selected_foreground = "#102A43"
    bar.setStyleSheet(
        f"QFrame#artStudioPagesBar {{background:{bar_background};border:1px solid {bar_border};border-radius:9px;}}"
        f"QTabBar::tab {{background:{tab_background};color:{tab_foreground};border:1px solid {bar_border};border-radius:6px;padding:7px 13px;margin:3px;}}"
        f"QTabBar::tab:selected {{background:{selected_background};color:{selected_foreground};font-weight:800;}}"
    )
    row = QHBoxLayout(bar)
    row.setContentsMargins(8, 5, 8, 5)
    row.setSpacing(6)
    page.v150_tab_bar = QTabBar(bar)
    page.v150_tab_bar.setMovable(True)
    page.v150_tab_bar.setTabsClosable(True)
    page.v150_tab_bar.setExpanding(False)
    page.v150_tab_bar.setUsesScrollButtons(True)
    row.addWidget(QLabel("PÁGINAS"))
    row.addWidget(page.v150_tab_bar, 1)
    page.v150_add_page_button = QPushButton("+ Página")
    page.v150_duplicate_page_button = QPushButton("Duplicar")
    page.v150_rename_page_button = QPushButton("Renomear")
    page.v150_export_pages_button = QPushButton("PDF completo")
    page.v150_page_count_label = QLabel("1 página")
    for button in (page.v150_add_page_button, page.v150_duplicate_page_button, page.v150_rename_page_button, page.v150_export_pages_button):
        button.setProperty("secondary", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(button)
    row.addWidget(page.v150_page_count_label)
    root.insertWidget(1, bar)
    page.v150_pages_bar = bar
    page.v150_tab_bar.currentChanged.connect(
        lambda _index: QTimer.singleShot(0, lambda: _switch_page(page, page.v150_tab_bar.currentIndex()))
    )
    page.v150_tab_bar.tabMoved.connect(lambda source, target: _tab_moved(page, source, target))
    page.v150_tab_bar.tabCloseRequested.connect(lambda index: _delete_page(page, index))
    page.v150_add_page_button.clicked.connect(lambda: _add_page(page))
    page.v150_duplicate_page_button.clicked.connect(lambda: _duplicate_page(page))
    page.v150_rename_page_button.clicked.connect(lambda: _rename_page(page))
    page.v150_export_pages_button.clicked.connect(lambda: _export_all_pages_pdf(page))
    _update_tabs(page)


class _SmartGuideEventFilter(QObject):
    """Observa arrastes no viewport sem substituir métodos virtuais do Qt."""

    def __init__(self, page, parent=None) -> None:
        super().__init__(parent)
        self._page = page

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt API
        if event.type() == QEvent.Type.MouseMove:
            if event.buttons() & Qt.MouseButton.LeftButton:
                QTimer.singleShot(0, lambda: _snap_current_grabber(self._page))
        elif event.type() == QEvent.Type.MouseButtonRelease:
            QTimer.singleShot(0, lambda: _clear_guides(self._page))
        return False


def _snap_current_grabber(page) -> None:
    if not page.v150_snap_check.isChecked():
        _clear_guides(page)
        return
    focus_item = page.scene.focusItem()
    if isinstance(focus_item, QGraphicsTextItem) and focus_item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        return
    target = page.scene.mouseGrabberItem()
    if target is not None and not target.data(RESIZE_HANDLE_KEY):
        _snap_dragged_item(page, target)


def _install_guides(page) -> None:
    # As opções ficam na barra de páginas para permanecerem visíveis sem
    # ocupar o painel direito que já reúne as propriedades do objeto.
    page.v150_grid_check = QCheckBox("Grade")
    page.v150_snap_check = QCheckBox("Guias inteligentes")
    page.v150_grid_check.setToolTip("Exibe uma grade visual de 50 px no canvas; não aparece na exportação.")
    page.v150_snap_check.setToolTip("Encaixa bordas e centros dos objetos próximos de outros objetos e do canvas.")
    row = page.v150_pages_bar.layout()
    row.insertWidget(row.count() - 2, page.v150_grid_check)
    row.insertWidget(row.count() - 2, page.v150_snap_check)
    page.v150_grid_check.toggled.connect(lambda enabled: _set_grid(page, enabled))
    page.v150_grid_lines = []
    page.v150_guide_lines = []
    page.v150_snap_active = False
    view = page.__dict__.get("_art_studio_view_actual") or page.view
    page._v150_snap_filter = _SmartGuideEventFilter(page, page)
    view.viewport().installEventFilter(page._v150_snap_filter)
    page._v150_original_render_art = page._render_art

    def render_without_guides():
        overlays = (
            list(page._v150_grid_lines)
            + list(page._v150_guide_lines)
            + list(getattr(page, "_v148_handles", []))
        )
        previous = []
        for item in overlays:
            previous.append((item, item.isVisible()))
            item.hide()
        try:
            return page._v150_original_render_art()
        finally:
            for item, visible in previous:
                item.setVisible(visible)

    page._render_art = render_without_guides


def _set_grid(page, enabled: bool) -> None:
    _clear_grid(page)
    if not enabled:
        return
    rect = page.scene.sceneRect()
    pen = QPen(QColor(214, 182, 109, 65), 1, Qt.PenStyle.DotLine)
    for x in range(50, int(rect.width()), 50):
        line = QGraphicsLineItem(float(x), rect.top(), float(x), rect.bottom())
        line.setPen(pen)
        line.setZValue(-99990)
        line.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        line.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        page.scene.addItem(line)
        page._v150_grid_lines.append(line)
    for y in range(50, int(rect.height()), 50):
        line = QGraphicsLineItem(rect.left(), float(y), rect.right(), float(y))
        line.setPen(pen)
        line.setZValue(-99990)
        line.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        line.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        page.scene.addItem(line)
        page._v150_grid_lines.append(line)


def _clear_grid(page) -> None:
    for item in list(getattr(page, "_v150_grid_lines", [])):
        try:
            if item.scene() is page.scene:
                page.scene.removeItem(item)
        except RuntimeError:
            pass
    page._v150_grid_lines = []


def _clear_guides(page) -> None:
    for item in list(getattr(page, "_v150_guide_lines", [])):
        try:
            if item.scene() is page.scene:
                page.scene.removeItem(item)
        except RuntimeError:
            pass
    page._v150_guide_lines = []


def _move_by_scene_delta(item: QGraphicsItem, dx: float, dy: float) -> None:
    parent = item.parentItem()
    delta = QPointF(dx, dy)
    if parent is None:
        item.moveBy(dx, dy)
    else:
        origin = parent.mapFromScene(QPointF(0, 0))
        target = parent.mapFromScene(delta)
        item.moveBy(target.x() - origin.x(), target.y() - origin.y())


def _snap_axis(own: tuple[float, float, float], references: list[float], tolerance: float = 9.0):
    best = None
    for own_value in own:
        for reference in references:
            delta = reference - own_value
            if abs(delta) <= tolerance and (best is None or abs(delta) < abs(best)):
                best = delta
    return best


def _snap_dragged_item(page, item: QGraphicsItem) -> None:
    if bool(item.data(LOCKED_KEY)):
        return
    rect = item.sceneBoundingRect()
    canvas = page.scene.sceneRect()
    own_x = (rect.left(), rect.center().x(), rect.right())
    own_y = (rect.top(), rect.center().y(), rect.bottom())
    refs_x = [canvas.left(), canvas.center().x(), canvas.right()]
    refs_y = [canvas.top(), canvas.center().y(), canvas.bottom()]
    for other in page._content_items():
        if other is item or not other.isVisible():
            continue
        other_rect = other.sceneBoundingRect()
        refs_x.extend((other_rect.left(), other_rect.center().x(), other_rect.right()))
        refs_y.extend((other_rect.top(), other_rect.center().y(), other_rect.bottom()))
    dx = _snap_axis(own_x, refs_x)
    dy = _snap_axis(own_y, refs_y)
    _clear_guides(page)
    if dx is not None:
        _move_by_scene_delta(item, dx, 0)
        snapped = item.sceneBoundingRect()
        x = min((snapped.left(), snapped.center().x(), snapped.right()), key=lambda v: min(abs(v-r) for r in refs_x))
        line = QGraphicsLineItem(x, canvas.top(), x, canvas.bottom())
        _add_guide(page, line)
    if dy is not None:
        _move_by_scene_delta(item, 0, dy)
        snapped = item.sceneBoundingRect()
        y = min((snapped.top(), snapped.center().y(), snapped.bottom()), key=lambda v: min(abs(v-r) for r in refs_y))
        line = QGraphicsLineItem(canvas.left(), y, canvas.right(), y)
        _add_guide(page, line)
    if dx is not None or dy is not None:
        page.scene.update()
        if hasattr(page, "v149_sync_controls"):
            page.v149_sync_controls()


def _add_guide(page, line: QGraphicsLineItem) -> None:
    line.setPen(QPen(QColor("#16A6F5"), 2, Qt.PenStyle.DashLine))
    line.setZValue(99999)
    line.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
    line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
    line.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
    page.scene.addItem(line)
    page._v150_guide_lines.append(line)


def _install_advanced_typography(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return
    frame = QFrame(content)
    frame.setObjectName("artStudioAdvancedTypography")
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    title = QLabel("TIPOGRAFIA AVANÇADA")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    form = QFormLayout()
    page.v150_letter_spacing = QDoubleSpinBox()
    page.v150_letter_spacing.setRange(-5.0, 40.0)
    page.v150_letter_spacing.setDecimals(1)
    page.v150_letter_spacing.setSuffix(" px")
    page.v150_letter_spacing.setToolTip("Espaçamento entre caracteres")
    page.v150_line_spacing = QComboBox()
    for value in (80, 90, 100, 110, 120, 130, 140, 150, 175, 200):
        page.v150_line_spacing.addItem(f"{value}%", value)
    form.addRow("Espaçamento de letras", page.v150_letter_spacing)
    form.addRow("Espaçamento de linhas", page.v150_line_spacing)
    box.addLayout(form)
    page.v150_apply_typography = QPushButton("Aplicar tipografia")
    page.v150_apply_typography.setProperty("secondary", True)
    box.addWidget(page.v150_apply_typography)
    page.v150_apply_typography.clicked.connect(lambda: _apply_advanced_typography(page))
    layout.addWidget(frame)


def _apply_advanced_typography(page) -> None:
    selected = page.scene.selectedItems()
    item = selected[0] if len(selected) == 1 else None
    if not isinstance(item, QGraphicsTextItem):
        page.status_label.setText("Selecione um texto para aplicar a tipografia avançada.")
        return
    if bool(item.data(LOCKED_KEY)):
        page.status_label.setText("Desbloqueie o texto antes de alterar a tipografia.")
        return
    cursor = item.textCursor()
    had_selection = cursor.hasSelection()
    if not had_selection:
        cursor.select(QTextCursor.SelectionType.Document)
    char_format = QTextCharFormat()
    char_format.setFontLetterSpacingType(QFont.SpacingType.AbsoluteSpacing)
    char_format.setFontLetterSpacing(float(page.v150_letter_spacing.value()))
    cursor.mergeCharFormat(char_format)
    block = QTextBlockFormat()
    block.setLineHeight(
        float(page.v150_line_spacing.currentData()),
        QTextBlockFormat.LineHeightTypes.ProportionalHeight,
    )
    cursor.mergeBlockFormat(block)
    item.setTextCursor(cursor)
    page.status_label.setText("Espaçamento de caracteres e linhas aplicado.")
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.start()


def _install_document_methods(page) -> None:
    page._v150_original_new_project = page.new_project
    page._v150_original_open_project = page.open_project
    page._v150_original_save_project = page.save_project
    page.new_project = lambda: _new_project(page)
    page.open_project = lambda: _open_project(page)
    page.save_project = lambda: _save_project(page)

    # As conexões feitas no __init__ guardam as referências antigas; reconecta
    # os botões e atalhos para os métodos multipágina da V150.
    for button, callback in (
        (page.new_button, page.new_project),
        (page.open_button, page.open_project),
        (page.save_button, page.save_project),
    ):
        try:
            button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        button.clicked.connect(callback)
    for action in page.actions():
        if action.text() in {"Abrir projeto", "Salvar projeto"}:
            try:
                action.triggered.disconnect()
            except (RuntimeError, TypeError):
                pass
            callback = {
                "Abrir projeto": page.open_project,
                "Salvar projeto": page.save_project,
            }.get(action.text())
            if callback:
                action.triggered.connect(lambda _checked=False, fn=callback: fn())


def _update_page_chrome(page) -> None:
    index = page._v150_active_index
    total = len(page._v150_pages)
    page.v150_page_count_label.setText(f"{total} página(s)")
    page.v150_tab_bar.setCurrentIndex(index)
    page.v150_duplicate_page_button.setEnabled(total < MAX_PAGES)
    page.v150_add_page_button.setEnabled(total < MAX_PAGES)
    page.v150_tab_bar.setTabToolTip(index, "Duplo clique para renomear a página")


def _export_all_pages_pdf(page) -> None:
    path, _ = QFileDialog.getSaveFileName(
        page,
        "Exportar todas as páginas em PDF",
        str(page.projects_dir / "Projeto completo.pdf"),
        "Documento PDF (*.pdf)",
    )
    if not path:
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    _capture_active_page(page)
    total_pixels = sum(
        int((entry["data"].get("canvas") or {}).get("width", 1080))
        * int((entry["data"].get("canvas") or {}).get("height", 1080))
        for entry in page._v150_pages
    )
    if total_pixels > MAX_TOTAL_RENDER_PIXELS:
        QMessageBox.warning(
            page,
            "Exportação muito grande",
            "A soma das resoluções ultrapassa o limite de segurança de 80 milhões de pixels. Exporte menos páginas por vez.",
        )
        return

    rendered: list[PILImage.Image] = []
    active_index = page._v150_active_index
    active_selection = [
        str(item.data(HISTORY_ID_KEY) or "")
        for item in page.scene.selectedItems()
        if item.data(HISTORY_ID_KEY)
    ]
    previous_history_suspended = getattr(page, "_v145_history_suspended", False)
    page._v145_history_suspended = True
    try:
        for index, entry in enumerate(page._v150_pages):
            page._v150_active_index = index
            _restore_page_data(page, entry["data"], fit=False, reset_history=False)
            image = page._render_art()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if not image.save(buffer, "PNG"):
                raise OSError(f"Falha ao renderizar a página {index + 1}.")
            rendered.append(PILImage.open(BytesIO(bytes(buffer.data()))).convert("RGB"))
        if not rendered:
            raise ValueError("O projeto não possui páginas para exportar.")
        rendered[0].save(
            path,
            "PDF",
            save_all=True,
            append_images=rendered[1:],
            resolution=300.0,
        )
    except Exception as exc:
        log.exception("Falha ao exportar documento multipágina")
        QMessageBox.critical(page, "Erro ao exportar PDF", str(exc))
    else:
        page.status_label.setText(f"PDF completo exportado com {len(rendered)} páginas: {path}")
        QMessageBox.information(page, "Exportação concluída", f"Documento PDF criado:\n{path}")
    finally:
        for image in rendered:
            try:
                image.close()
            except Exception:
                pass
        page._v150_active_index = active_index
        _restore_page_data(page, page._v150_pages[active_index]["data"], reset_history=False)
        page.scene.clearSelection()
        selected_item = None
        for item in page._content_items():
            if str(item.data(HISTORY_ID_KEY) or "") in set(active_selection) and item.isVisible():
                item.setSelected(True)
                selected_item = item
                break
        page._v145_active_item = selected_item
        page._refresh_layers(select_item=selected_item)
        page._update_selection_controls(selected_item)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        page._v145_last_snapshot = _v145_snapshot(page)
        page._v145_history_suspended = previous_history_suspended
        page._v150_update_page_chrome()


def _install_group_identity_persistence(page) -> None:
    original_serialize = page._serialize_item

    def serialize_with_group_identity(item):
        data = original_serialize(item)
        if isinstance(item, QGraphicsItemGroup):
            identity = item.data(HISTORY_ID_KEY)
            if not identity:
                identity = uuid.uuid4().hex
                item.setData(HISTORY_ID_KEY, identity)
            data["history_id"] = str(identity)
        return data

    page._serialize_item = serialize_with_group_identity


def enhance_art_studio_page_v150(page) -> None:
    """Instala V150 uma única vez, depois das camadas V145–V149."""
    if getattr(page, "_v150_installed", False):
        return
    page._v150_installed = True
    page._v150_restoring = False
    page._v150_tab_guard = False
    page._v150_active_index = 0
    page._v150_background = _page_background_default(page)
    page._v150_pages = [{"id": uuid.uuid4().hex, "name": "Página 1", "data": _capture_page(page)}]
    page._v150_page_histories = {page._v150_pages[0]["id"]: page._v145_history}
    page._v150_undo_state_slot = page.undo_button.setEnabled
    page._v150_redo_state_slot = page.redo_button.setEnabled
    _install_history_snapshot_compatibility(page)
    page._v150_grid_lines: list[QGraphicsLineItem] = []
    page._v150_guide_lines: list[QGraphicsLineItem] = []
    page._v150_overlay_items: list[QGraphicsItem] = []

    _install_group_identity_persistence(page)
    _install_pages_bar(page)
    _install_background_tools(page)
    _install_element_library(page)
    _install_left_panel_scroll(page)
    _install_advanced_typography(page)
    _install_guides(page)
    _install_document_methods(page)
    page._v150_update_page_chrome = lambda: _update_page_chrome(page)

    original_apply_canvas_size = page.apply_canvas_size
    def apply_canvas_size_v150():
        original_apply_canvas_size()
        _apply_background(page, page._v150_background)
        _capture_active_page(page)
        if page.v150_grid_check.isChecked():
            _set_grid(page, True)
    page.apply_canvas_size = apply_canvas_size_v150
    page.apply_size_button.clicked.disconnect()
    page.apply_size_button.clicked.connect(page.apply_canvas_size)

    # Duplo clique no rótulo da página permite renomear sem abrir outro painel.
    page.v150_tab_bar.tabBarDoubleClicked.connect(lambda _index: _rename_page(page))
    page.status_label.setText(
        "V150: documentos com várias páginas, fundos em degradê/imagem, biblioteca de elementos, "
        "tipografia avançada, grade, guias inteligentes e histórico independente por página."
    )


def install_art_studio_v150() -> None:
    """Conecta a camada V150 à página criada pelos instaladores anteriores."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v150_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v150(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v150(page)

    MainWindow.__init__ = init_with_v150
    MainWindow._v150_integration_installed = True
