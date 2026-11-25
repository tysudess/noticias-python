from __future__ import annotations

"""V154 — gerenciamento avançado de camadas e seleção múltipla.

Amplia o Estúdio V153 com seleção múltipla pelo painel de camadas, filtro,
renomeação direta e ações em lote. Não altera o formato .centralart nem os
módulos anteriores.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QApplication,
    QGraphicsItem,
    QGraphicsTextItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_page import ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import _group_selected, _ungroup_selected
from monitor_noticias.ui.art_studio_v151 import _sync_controls as _v151_sync_controls
from monitor_noticias.ui.art_studio_v152 import (
    _duplicate_selection,
    _move_selection_to_extreme,
    _sync_controls as _v152_sync_controls,
)


def _item_from_row(page, row):
    if row is None:
        return None
    try:
        key = int(row.data(Qt.ItemDataRole.UserRole))
    except (TypeError, ValueError):
        return None
    item = getattr(page, "_layer_objects", {}).get(key)
    if item is None:
        return None
    try:
        return item if item.scene() is page.scene else None
    except RuntimeError:
        return None


def _selected_layer_items(page, *, fallback: bool = True) -> list:
    result = []
    seen = set()
    for row in page.layers.selectedItems():
        item = _item_from_row(page, row)
        if item is not None and id(item) not in seen:
            result.append(item)
            seen.add(id(item))
    if not result and fallback:
        for item in getattr(page, "_v154_layer_selection", []):
            try:
                if item.scene() is page.scene and id(item) not in seen:
                    result.append(item)
                    seen.add(id(item))
            except RuntimeError:
                continue
    return result


def _selected_roots(items: list) -> list:
    selected = set(items)
    result = []
    for item in items:
        parent = item.parentItem()
        nested = False
        while parent is not None:
            if parent in selected:
                nested = True
                break
            parent = parent.parentItem()
        if not nested:
            result.append(item)
    return result


def _refresh_status(page) -> None:
    items = _selected_layer_items(page)
    count = len(items)
    editable = sum(1 for item in items if item.isVisible() and not bool(item.data(LOCKED_KEY)))
    page.v154_layer_count.setText(f"{count} camada(s) selecionada(s) · {editable} editável(is)")
    page.v154_rename_button.setEnabled(count == 1)
    page.v154_visibility_button.setEnabled(bool(count))
    page.v154_lock_button.setEnabled(bool(count))
    page.v154_visibility_button.setText(
        "Ocultar" if count and all(item.isVisible() for item in items) else "Mostrar"
    )
    page.v154_lock_button.setText(
        "Desbloquear" if count and all(bool(item.data(LOCKED_KEY)) for item in items) else "Bloquear"
    )


def _restore_layer_rows(page, items: list) -> None:
    wanted = {id(item) for item in items}
    previous_blocked = page.layers.blockSignals(True)
    try:
        for index in range(page.layers.count()):
            row = page.layers.item(index)
            item = _item_from_row(page, row)
            row.setSelected(item is not None and id(item) in wanted)
        page._v154_layer_selection = [item for item in items if _item_is_in_scene(item, page)]
    finally:
        page.layers.blockSignals(previous_blocked)


def _sync_scene_from_layer_list(page) -> None:
    if getattr(page, "_v154_syncing", False):
        return
    page._v154_syncing = True
    try:
        items = _selected_layer_items(page, fallback=False)
        page._v154_layer_selection = items
        page.scene.clearSelection()
        visible = [item for item in items if item.isVisible()]
        for item in visible:
            item.setSelected(True)
        page._v145_active_item = items[0] if len(items) == 1 else None
        if len(items) == 1:
            page._update_selection_controls(items[0])
        else:
            page._update_selection_controls(None)
        if hasattr(page, "_v148_sync_handles"):
            page._v148_sync_handles()
        if hasattr(page, "_v148_update_dimensions"):
            page._v148_update_dimensions()
        if hasattr(page, "_v149_sync_controls"):
            page._v149_sync_controls()
        if hasattr(page, "_v145_update_v145_controls"):
            page._v145_update_v145_controls()
        _restore_layer_rows(page, items)
    finally:
        page._v154_syncing = False
    _refresh_status(page)
    _v151_sync_controls(page)
    _v152_sync_controls(page)


def _sync_layer_list_from_scene(page) -> None:
    if getattr(page, "_v154_syncing", False):
        return
    scene_items = _selected_roots(list(page.scene.selectedItems()))
    page._v154_syncing = True
    try:
        previous_blocked = page.layers.blockSignals(True)
        page.layers.clearSelection()
        wanted = {id(item) for item in scene_items}
        for index in range(page.layers.count()):
            row = page.layers.item(index)
            item = _item_from_row(page, row)
            if item is not None and id(item) in wanted:
                row.setSelected(True)
        page._v154_layer_selection = scene_items
        page._v145_active_item = scene_items[0] if len(scene_items) == 1 else None
    finally:
        page.layers.blockSignals(previous_blocked)
        page._v154_syncing = False
    _refresh_status(page)
    _v151_sync_controls(page)
    _v152_sync_controls(page)


def _refresh_layers_with_multiselection(page, *args, **kwargs):
    original = page._v154_original_refresh_layers
    scene_items = _selected_roots(list(page.scene.selectedItems()))
    stored = [
        item for item in getattr(page, "_v154_layer_selection", [])
        if _item_is_in_scene(item, page)
    ]
    if scene_items:
        wanted = list(scene_items)
        # Camadas ocultas podem continuar selecionadas no painel para que o
        # usuário consiga mostrá-las novamente sem procurá-las outra vez.
        wanted.extend(item for item in stored if not item.isVisible() and item not in wanted)
    else:
        wanted = stored
    target = kwargs.get("select_item")
    if target is None and args:
        target = args[0]
    if target is not None and not scene_items:
        wanted = [target] if _item_is_in_scene(target, page) else []

    previous_blocked = page.layers.blockSignals(True)
    try:
        result = original(*args, **kwargs)
        _restore_layer_rows(page, wanted)
    finally:
        page.layers.blockSignals(previous_blocked)
    _refresh_status(page)
    if hasattr(page, "v154_layer_filter"):
        _filter_layers(page, page.v154_layer_filter.text())
    return result


def _item_is_in_scene(item, page) -> bool:
    try:
        return item.scene() is page.scene
    except RuntimeError:
        return False


def _filter_layers(page, text: str) -> None:
    needle = str(text or "").strip().casefold()
    for index in range(page.layers.count()):
        row = page.layers.item(index)
        item = _item_from_row(page, row)
        name = str(item.data(ITEM_NAME_KEY) or row.text()) if item is not None else row.text()
        row.setHidden(bool(needle) and needle not in name.casefold())


def _rename_selected(page) -> None:
    items = _selected_layer_items(page)
    if len(items) != 1:
        page.status_label.setText("Selecione uma única camada para renomear.")
        return
    item = items[0]
    current = str(item.data(ITEM_NAME_KEY) or "Objeto")
    name, accepted = QInputDialog.getText(page, "Renomear camada", "Nome da camada:", text=current)
    if not accepted or not name.strip():
        return
    item.setData(ITEM_NAME_KEY, name.strip()[:100])
    page._v154_layer_selection = [item]
    page._refresh_layers(select_item=item)
    page.status_label.setText(f"Camada renomeada para '{name.strip()[:100]}'.")


def _toggle_visibility_selected(page) -> None:
    items = _selected_roots(_selected_layer_items(page))
    if not items:
        return
    make_visible = not all(item.isVisible() for item in items)
    page._v154_syncing = True
    try:
        for item in items:
            item.setVisible(make_visible)
        page._v154_layer_selection = items
        page.scene.clearSelection()
        if make_visible:
            for item in items:
                item.setSelected(True)
    finally:
        page._v154_syncing = False
    page._refresh_layers()
    _restore_layer_rows(page, items)
    page.status_label.setText(
        f"{len(items)} camada(s) {'exibida(s)' if make_visible else 'ocultada(s)'}."
    )
    _schedule_history(page)
    _refresh_status(page)


def _toggle_lock_selected(page) -> None:
    items = _selected_roots(_selected_layer_items(page))
    if not items:
        return
    lock = not all(bool(item.data(LOCKED_KEY)) for item in items)
    for item in items:
        item.setData(LOCKED_KEY, lock)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not lock)
    page._v154_layer_selection = items
    page._refresh_layers()
    _restore_layer_rows(page, items)
    page.status_label.setText(
        f"{len(items)} camada(s) {'bloqueada(s)' if lock else 'desbloqueada(s)'}."
    )
    _schedule_history(page)
    _refresh_status(page)


def _delete_selected(page) -> None:
    items = _selected_roots(_selected_layer_items(page))
    deletable = [item for item in items if not bool(item.data(LOCKED_KEY))]
    skipped = len(items) - len(deletable)
    if not deletable:
        page.status_label.setText("Não há camadas desbloqueadas para excluir.")
        return
    for item in deletable:
        if item.scene() is page.scene:
            page.scene.removeItem(item)
    page._v154_layer_selection = []
    page._v145_active_item = None
    page.scene.clearSelection()
    page._refresh_layers()
    suffix = f" {skipped} bloqueada(s) preservada(s)." if skipped else ""
    page.status_label.setText(f"{len(deletable)} camada(s) excluída(s).{suffix}")
    _schedule_history(page)
    _refresh_status(page)


def _schedule_history(page) -> None:
    timer = getattr(page, "_v145_history_timer", None)
    if timer is not None and not getattr(page, "_v145_history_suspended", False):
        timer.start()


def _context_menu(page, position) -> None:
    row = page.layers.itemAt(position)
    if row is not None and not row.isSelected():
        page.layers.clearSelection()
        row.setSelected(True)
        _sync_scene_from_layer_list(page)
    items = _selected_roots(_selected_layer_items(page))
    if not items:
        return

    menu = QMenu(page.layers)
    rename = menu.addAction("Renomear camada…")
    rename.setEnabled(len(items) == 1)
    menu.addSeparator()
    menu.addAction("Mostrar / ocultar", lambda: _toggle_visibility_selected(page))
    menu.addAction("Bloquear / desbloquear", lambda: _toggle_lock_selected(page))
    menu.addSeparator()
    menu.addAction("Duplicar seleção", lambda: _duplicate_selection(page))
    menu.addAction("Agrupar seleção", lambda: _group_selected(page))
    menu.addAction("Desagrupar grupo", lambda: _ungroup_selected(page))
    menu.addSeparator()
    menu.addAction("Trazer para frente", lambda: _move_selection_to_extreme(page, "front"))
    menu.addAction("Enviar para trás", lambda: _move_selection_to_extreme(page, "back"))
    menu.addAction("Excluir seleção", lambda: _delete_selected(page))
    chosen = menu.exec(page.layers.mapToGlobal(position))
    if chosen is rename:
        _rename_selected(page)


def _delete_shortcut(page) -> None:
    focus = QApplication.focusWidget()
    if isinstance(focus, QLineEdit):
        return
    focus_item = page.scene.focusItem()
    if isinstance(focus_item, QGraphicsTextItem) and focus_item.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction:
        return
    _delete_selected(page)


def _install_shortcuts(page) -> None:
    actions = (
        ("Renomear camada", "F2", lambda: _rename_selected(page)),
        ("Excluir camadas selecionadas", "Delete", lambda: _delete_shortcut(page)),
        ("Mostrar ou ocultar camadas", "Ctrl+Shift+H", lambda: _toggle_visibility_selected(page)),
        ("Bloquear ou desbloquear camadas", "Ctrl+Shift+L", lambda: _toggle_lock_selected(page)),
    )
    for label, sequence, callback in actions:
        action = QAction(label, page)
        action.setShortcut(QKeySequence(sequence))
        action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(lambda _checked=False, fn=callback: fn())
        page.addAction(action)


def _install_layer_manager(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None or getattr(page, "_v154_layer_manager_installed", False):
        return

    page.v154_layer_filter = QLineEdit(content)
    page.v154_layer_filter.setObjectName("artStudioLayerFilterV154")
    page.v154_layer_filter.setPlaceholderText("⌕  Filtrar camadas pelo nome…")
    page.v154_layer_filter.setClearButtonEnabled(True)
    page.v154_layer_filter.setToolTip("Digite parte do nome para localizar uma camada.")

    actions = QFrame(content)
    actions.setObjectName("artStudioLayerActionsV154")
    row = QHBoxLayout(actions)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    page.v154_rename_button = QPushButton("Renomear")
    page.v154_visibility_button = QPushButton("Ocultar")
    page.v154_lock_button = QPushButton("Bloquear")
    for button in (page.v154_rename_button, page.v154_visibility_button, page.v154_lock_button):
        button.setProperty("secondary", True)
        button.setMinimumHeight(28)
        button.setToolTip(button.text())
        row.addWidget(button)
    page.v154_layer_count = QLabel("0 camada(s) selecionada(s)")
    page.v154_layer_count.setObjectName("muted")
    page.v154_layer_count.setWordWrap(True)

    index = layout.indexOf(page.layers)
    if index < 0:
        return
    layout.insertWidget(index, page.v154_layer_filter)
    layout.insertWidget(index + 1, actions)
    layout.insertWidget(index + 2, page.v154_layer_count)

    page.v154_layer_filter.textChanged.connect(lambda value: _filter_layers(page, value))
    page.v154_rename_button.clicked.connect(lambda: _rename_selected(page))
    page.v154_visibility_button.clicked.connect(lambda: _toggle_visibility_selected(page))
    page.v154_lock_button.clicked.connect(lambda: _toggle_lock_selected(page))
    page.layers.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    page.layers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    page.layers.customContextMenuRequested.connect(lambda point: _context_menu(page, point))
    page.layers.itemDoubleClicked.connect(lambda _row: _rename_selected(page))

    # A seleção antiga tratava cada clique como seleção única. Retira apenas
    # os slots desse sinal e passa a sincronizar a seleção múltipla por lista.
    try:
        page.layers.currentItemChanged.disconnect()
    except (RuntimeError, TypeError):
        pass
    page.layers.itemSelectionChanged.connect(lambda: _sync_scene_from_layer_list(page))

    page._v154_original_refresh_layers = page._refresh_layers
    page._refresh_layers = lambda *args, **kwargs: _refresh_layers_with_multiselection(page, *args, **kwargs)
    page.scene.selectionChanged.connect(lambda: _sync_layer_list_from_scene(page))
    page._v154_layer_selection = []
    page._v154_syncing = False
    page._v154_layer_manager_installed = True
    _install_shortcuts(page)
    _refresh_status(page)


def enhance_art_studio_page_v154(page) -> None:
    if getattr(page, "_v154_installed", False):
        return
    _install_layer_manager(page)
    if not getattr(page, "_v154_layer_manager_installed", False):
        return
    page._v154_installed = True
    page.status_label.setText(
        "V154: seleção múltipla pelo painel de camadas, filtro por nome, renomeação rápida, "
        "menu de contexto e ações em lote para visibilidade, bloqueio, duplicação e organização."
    )


def install_art_studio_v154() -> None:
    """Instala V154 depois de V153, sem substituir as camadas anteriores."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v154_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v154(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v154(page)

    MainWindow.__init__ = init_with_v154
    MainWindow._v154_integration_installed = True
