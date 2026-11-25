from __future__ import annotations

"""V156 — lixeira temporária e recuperação de exclusões do Estúdio.

Acrescenta uma lixeira por página para recuperar camadas removidas pelo botão,
atalho ou menu de contexto. A implementação preserva grupos, identificadores,
posição, ordem, visibilidade e propriedades serializadas pelo Estúdio.

Também integra a instalação correta da V155: o módulo V155 precisa estar em
src/monitor_noticias/ui/, caminho utilizado pelo run.py.
"""

from copy import deepcopy
import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout

from monitor_noticias.ui import art_studio_v154 as _v154
from monitor_noticias.ui.art_studio_page import ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import HISTORY_ID_KEY, LOCKED_KEY
from monitor_noticias.ui.art_studio_v155 import _active_page_id

log = logging.getLogger(__name__)

_MAX_RECYCLE_BATCHES = 12
_MAX_RECYCLE_BYTES = 48 * 1024 * 1024


def _page_key(page) -> str:
    return _active_page_id(page) or "single-page-document"


def _item_identity(item) -> str:
    identity = item.data(HISTORY_ID_KEY)
    if not identity:
        import uuid
        identity = uuid.uuid4().hex
        item.setData(HISTORY_ID_KEY, identity)
    return str(identity)


def _top_level_roots(items: list) -> list:
    selected = set(items)
    roots = []
    for item in items:
        parent = item.parentItem()
        nested = False
        while parent is not None:
            if parent in selected:
                nested = True
                break
            parent = parent.parentItem()
        if not nested:
            roots.append(item)
    return roots


def _serialize_deletable(page, items: list) -> list[dict]:
    snapshots = []
    for item in _top_level_roots(items):
        try:
            if item.scene() is not page.scene or bool(item.data(LOCKED_KEY)):
                continue
            data = deepcopy(page._serialize_item(item))
            data["history_id"] = _item_identity(item)
            snapshots.append(data)
        except Exception as exc:
            log.exception("Não foi possível guardar uma camada na lixeira temporária")
            raise RuntimeError(
                f"A camada '{item.data(ITEM_NAME_KEY) or 'Objeto'}' não pôde ser protegida. "
                "A exclusão foi cancelada para evitar perda de conteúdo."
            ) from exc
    return snapshots


def _recycle_size(batches: list[dict]) -> int:
    try:
        return len(json.dumps(batches, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError):
        return _MAX_RECYCLE_BYTES + 1


def _update_recycle_ui(page) -> None:
    batches = getattr(page, "_v156_recycle_bin", [])
    matching = [batch for batch in batches if batch.get("page_id") == _page_key(page)]
    count = sum(len(batch.get("items", [])) for batch in matching)
    page.v156_recycle_label.setText(
        f"{count} camada(s) recuperável(is) nesta página · lixeira desta sessão"
    )
    page.v156_restore_button.setEnabled(bool(matching))


def _record_deleted(page, snapshots: list[dict], removed_items: list) -> None:
    actually_removed = []
    removed_ids = set()
    for data, item in zip(snapshots, removed_items):
        try:
            if item.scene() is not page.scene:
                actually_removed.append(data)
                removed_ids.add(str(data.get("history_id") or ""))
        except RuntimeError:
            actually_removed.append(data)
            removed_ids.add(str(data.get("history_id") or ""))
    if not actually_removed:
        return

    batches = list(getattr(page, "_v156_recycle_bin", []))
    batch = {
        "page_id": _page_key(page),
        "items": actually_removed,
        "label": ", ".join(str(item.get("name") or item.get("kind") or "Objeto") for item in actually_removed),
    }
    batches.append(batch)
    while len(batches) > _MAX_RECYCLE_BATCHES or _recycle_size(batches) > _MAX_RECYCLE_BYTES:
        if len(batches) <= 1:
            # Não guarda uma imagem gigantesca em memória, mas nunca impede a
            # exclusão solicitada pelo usuário.
            batches = []
            page.status_label.setText(
                "A camada foi excluída, mas era grande demais para a lixeira temporária. Use Ctrl+Z para desfazer."
            )
            break
        batches.pop(0)
    page._v156_recycle_bin = batches
    _update_recycle_ui(page)


def _capture_for_items(page, items: list) -> tuple[list[dict], list]:
    roots = _top_level_roots(items)
    deletable = [
        item for item in roots
        if item.scene() is page.scene and not bool(item.data(LOCKED_KEY))
    ]
    try:
        snapshots = _serialize_deletable(page, deletable)
    except Exception as exc:
        page.status_label.setText(str(exc))
        return [], []
    # Alinha snapshots e referências por identidade. Uma camada sem cópia
    # serializada nunca é excluída por esta rotina.
    by_id = {str(data.get("history_id")): data for data in snapshots}
    kept_items = [item for item in deletable if _item_identity(item) in by_id]
    kept_snapshots = [by_id[_item_identity(item)] for item in kept_items]
    if len(kept_items) != len(deletable):
        page.status_label.setText(
            "Exclusão cancelada: nem todas as camadas puderam ser protegidas."
        )
        return [], []
    return kept_snapshots, kept_items


def _delete_from_layer_panel(page) -> None:
    selected = _v154._selected_layer_items(page)
    snapshots, deletable = _capture_for_items(page, selected)
    if not deletable:
        return
    _v154._v156_original_delete_selected(page)
    _record_deleted(page, snapshots, deletable)


def _wrap_v154_delete() -> None:
    if getattr(_v154, "_v156_delete_wrapped", False):
        return
    _v154._v156_original_delete_selected = _v154._delete_selected
    _v154._delete_selected = _delete_from_layer_panel
    _v154._v156_delete_wrapped = True


def _delete_single_selected(page) -> None:
    selected = list(page.scene.selectedItems())
    if not selected:
        current = getattr(page, "_v145_active_item", None)
        if current is not None:
            try:
                if current.scene() is page.scene:
                    selected = [current]
            except RuntimeError:
                selected = []
    if len(selected) > 1:
        page.status_label.setText(
            "Há várias camadas selecionadas. Use o menu de camadas para excluir a seleção sem perder a possibilidade de recuperação."
        )
        return
    snapshots, deletable = _capture_for_items(page, selected)
    if not deletable:
        if selected and bool(selected[0].data(LOCKED_KEY)):
            page.status_label.setText("Desbloqueie a camada antes de excluí-la.")
        return
    # O caminho-base remove apenas o item ativo; a captura ocorre antes dele.
    page.scene.removeItem(deletable[0])
    page._v145_active_item = None
    page._refresh_layers()
    page._update_selection_controls(None)
    _record_deleted(page, snapshots, deletable)
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.start()


def _restore_last_deleted(page) -> None:
    batches = list(getattr(page, "_v156_recycle_bin", []))
    page_id = _page_key(page)
    index = next(
        (i for i in range(len(batches) - 1, -1, -1) if batches[i].get("page_id") == page_id),
        None,
    )
    if index is None:
        page.status_label.setText("Não há camadas removidas nesta página para recuperar.")
        _update_recycle_ui(page)
        return

    batch = batches[index]
    existing_ids = set()
    for item in page._content_items():
        try:
            identity = item.data(HISTORY_ID_KEY)
            if identity:
                existing_ids.add(str(identity))
        except RuntimeError:
            continue

    restored = []
    built = []
    try:
        for data in batch.get("items", []):
            identity = str(data.get("history_id") or "")
            if identity and identity in existing_ids:
                continue
            item = page._build_item_from_data(deepcopy(data))
            if identity:
                item.setData(HISTORY_ID_KEY, identity)
            built.append(item)
        # Constrói todos antes de adicioná-los: uma falha não deixa restauração parcial.
        for item in built:
            page.scene.addItem(item)
            restored.append(item)
    except Exception as exc:
        for item in restored:
            try:
                if item.scene() is page.scene:
                    page.scene.removeItem(item)
            except RuntimeError:
                pass
        for item in built:
            if item not in restored:
                try:
                    if item.scene() is not None:
                        item.scene().removeItem(item)
                except RuntimeError:
                    pass
        page.status_label.setText(f"Não foi possível recuperar as camadas: {exc}")
        log.exception("Falha ao restaurar camadas da lixeira temporária")
        return

    batches.pop(index)
    page._v156_recycle_bin = batches
    page.scene.clearSelection()
    for item in restored:
        item.setSelected(True)
    page._v145_active_item = restored[0] if len(restored) == 1 else None
    if hasattr(page, "_v154_layer_selection"):
        page._v154_layer_selection = list(restored)
    page._refresh_layers(select_item=restored[0] if len(restored) == 1 else None)
    if hasattr(_v154, "_restore_layer_rows"):
        _v154._restore_layer_rows(page, restored)
    if hasattr(page, "_update_selection_controls"):
        page._update_selection_controls(restored[0] if len(restored) == 1 else None)
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v148_update_dimensions"):
        page._v148_update_dimensions()
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None:
        timer.start()
    page.status_label.setText(
        f"{len(restored)} camada(s) recuperada(s) da lixeira temporária."
        if restored else "As camadas deste lote já estavam presentes; não foi necessário restaurar."
    )
    _update_recycle_ui(page)


def _install_recycle_panel(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    panel = QFrame(content)
    panel.setObjectName("artStudioRecyclePanelV156")
    box = QVBoxLayout(panel)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(5)
    title = QLabel("LIXEIRA TEMPORÁRIA")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)

    page.v156_recycle_label = QLabel("Nenhuma camada removida nesta página")
    page.v156_recycle_label.setObjectName("muted")
    page.v156_recycle_label.setWordWrap(True)
    box.addWidget(page.v156_recycle_label)

    page.v156_restore_button = QPushButton("Recuperar última exclusão")
    page.v156_restore_button.setProperty("secondary", True)
    page.v156_restore_button.setMinimumHeight(32)
    page.v156_restore_button.setToolTip(
        "Restaura a última camada ou conjunto de camadas removidas nesta página durante a sessão atual."
    )
    page.v156_restore_button.clicked.connect(lambda: _restore_last_deleted(page))
    box.addWidget(page.v156_restore_button)

    index = layout.indexOf(getattr(page, "v155_integrity_panel", None))
    layout.insertWidget(index + 1 if index >= 0 else layout.count(), panel)
    page.v156_recycle_panel = panel
    page._v156_recycle_bin = []
    _update_recycle_ui(page)


def _install_single_delete_guards(page) -> None:
    page._v156_original_page_delete = page.delete_selected
    page.delete_selected = lambda: _delete_single_selected(page)

    button = getattr(page, "delete_button", None)
    if button is not None:
        try:
            button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        button.clicked.connect(lambda: _delete_single_selected(page))

    for action in page.actions():
        if action.text() == "Excluir objeto":
            try:
                action.triggered.disconnect()
            except (RuntimeError, TypeError):
                pass
            action.triggered.connect(lambda _checked=False: _delete_single_selected(page))

    action = QAction("Recuperar última camada excluída", page)
    action.setShortcut(QKeySequence("Ctrl+Alt+Z"))
    action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    action.triggered.connect(lambda _checked=False: _restore_last_deleted(page))
    page.addAction(action)


def enhance_art_studio_page_v156(page) -> None:
    if getattr(page, "_v156_installed", False):
        return
    page._v156_installed = True
    _install_recycle_panel(page)
    _install_single_delete_guards(page)


def install_art_studio_v156() -> None:
    """Instala a lixeira depois da V155 e intercepta exclusões pelos dois painéis."""
    _wrap_v154_delete()
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v156_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v156(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v156(page)

    MainWindow.__init__ = init_with_v156
    MainWindow._v156_integration_installed = True
