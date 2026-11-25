from __future__ import annotations

"""V151 — composição multipla, distribuição e organização de camadas.

Esta camada amplia o Estúdio de Artes V150 sem reescrever as versões
anteriores nem alterar o formato dos projetos .centralart. Todos os recursos
operam sobre os objetos Qt já suportados pelo editor.
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY


def _selected_roots(page) -> list:
    """Retorna apenas os objetos selecionados de nível superior.

    Quando um grupo e um de seus filhos aparecem na seleção, o grupo é a
    unidade de composição. Isso evita mover ou alinhar o mesmo conteúdo duas
    vezes. O fundo do canvas já é excluído pela lista V146 de objetos.
    """
    selected = list(page.scene.selectedItems())
    selected_set = set(selected)
    roots = []
    for item in selected:
        parent = item.parentItem()
        nested_in_selection = False
        while parent is not None:
            if parent in selected_set:
                nested_in_selection = True
                break
            parent = parent.parentItem()
        if not nested_in_selection and item.data(ITEM_KIND_KEY) != "canvas-background":
            roots.append(item)
    return roots


def _movable_selection(page) -> tuple[list, int]:
    roots = _selected_roots(page)
    eligible = [
        item for item in roots
        if item.isVisible() and not bool(item.data(LOCKED_KEY))
    ]
    return eligible, len(roots) - len(eligible)


def _move_by_scene_delta(item, dx: float, dy: float) -> None:
    """Move um item pelo canvas, inclusive quando ele pertence a um grupo."""
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


def _finish_composition(page, items: list, message: str) -> None:
    if items:
        page._v145_active_item = items[0]
        page._refresh_layers(select_item=items[0])
        page._update_selection_controls(items[0])
    if hasattr(page, "_v148_sync_handles"):
        page._v148_sync_handles()
    if hasattr(page, "_v149_sync_controls"):
        page._v149_sync_controls()
    page.status_label.setText(message)
    page.scene.update()
    _schedule_history(page)
    _sync_controls(page)


def _selection_bounds(items: list):
    bounds = [item.sceneBoundingRect() for item in items]
    result = bounds[0]
    for rect in bounds[1:]:
        result = result.united(rect)
    return result, bounds


def _align_selection(page, mode: str) -> None:
    items, skipped = _movable_selection(page)
    if len(items) < 2:
        page.status_label.setText("Selecione pelo menos dois objetos desbloqueados para alinhar.")
        return

    target, bounds = _selection_bounds(items)
    for item, rect in zip(items, bounds):
        dx = 0.0
        dy = 0.0
        if mode == "left":
            dx = target.left() - rect.left()
        elif mode == "center_x":
            dx = target.center().x() - rect.center().x()
        elif mode == "right":
            dx = target.right() - rect.right()
        elif mode == "top":
            dy = target.top() - rect.top()
        elif mode == "center_y":
            dy = target.center().y() - rect.center().y()
        elif mode == "bottom":
            dy = target.bottom() - rect.bottom()
        else:
            page.status_label.setText("Tipo de alinhamento desconhecido.")
            return
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            _move_by_scene_delta(item, dx, dy)

    label = {
        "left": "esquerda",
        "center_x": "centro horizontal",
        "right": "direita",
        "top": "topo",
        "center_y": "centro vertical",
        "bottom": "base",
    }[mode]
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _finish_composition(page, items, f"{len(items)} objetos alinhados pelo {label} da seleção{suffix}.")


def _distribute_selection(page, axis: str) -> None:
    items, skipped = _movable_selection(page)
    if len(items) < 3:
        page.status_label.setText("Selecione pelo menos três objetos desbloqueados para distribuir.")
        return

    horizontal = axis == "horizontal"
    if not horizontal and axis != "vertical":
        page.status_label.setText("Eixo de distribuição desconhecido.")
        return

    rect_for = lambda item: item.sceneBoundingRect()
    items.sort(key=lambda item: (
        rect_for(item).left() if horizontal else rect_for(item).top(),
        rect_for(item).top() if horizontal else rect_for(item).left(),
        item.zValue(),
    ))
    rects = [rect_for(item) for item in items]
    leading = rects[0].left() if horizontal else rects[0].top()
    trailing = rects[-1].right() if horizontal else rects[-1].bottom()
    sizes = [rect.width() if horizontal else rect.height() for rect in rects]
    available_gap = (trailing - leading - sum(sizes)) / (len(items) - 1)

    cursor = leading
    for item, rect, size in zip(items, rects, sizes):
        current = rect.left() if horizontal else rect.top()
        delta = cursor - current
        if horizontal:
            _move_by_scene_delta(item, delta, 0.0)
        else:
            _move_by_scene_delta(item, 0.0, delta)
        cursor += size + available_gap

    direction = "horizontalmente" if horizontal else "verticalmente"
    suffix = f" · {skipped} bloqueado(s)/oculto(s) ignorado(s)" if skipped else ""
    _finish_composition(page, items, f"{len(items)} objetos distribuídos {direction} com espaçamento uniforme{suffix}.")


def _select_all(page) -> None:
    page.scene.clearSelection()
    for item in page._content_items():
        if item.isVisible():
            item.setSelected(True)
    page.status_label.setText("Todos os objetos visíveis da página foram selecionados.")
    _sync_controls(page)


def _invert_selection(page) -> None:
    for item in page._content_items():
        if item.isVisible():
            item.setSelected(not item.isSelected())
    page.status_label.setText("Seleção invertida na página atual.")
    _sync_controls(page)


def _clear_selection(page) -> None:
    page.scene.clearSelection()
    page.status_label.setText("Seleção limpa.")
    _sync_controls(page)


def _move_layer_one_step(page, direction: int) -> None:
    selected, _skipped = _movable_selection(page)
    selected_set = set(selected)
    if not selected_set:
        page.status_label.setText("Selecione ao menos uma camada desbloqueada.")
        return

    stack = [
        item for item in page._content_items()
        if item.parentItem() is None
    ]
    stack.sort(key=lambda item: item.zValue())
    before = list(stack)

    if direction > 0:
        # Percorrer de cima para baixo evita que uma seleção múltipla atravesse
        # mais de uma camada no mesmo comando.
        for index in range(len(stack) - 2, -1, -1):
            if stack[index] in selected_set and stack[index + 1] not in selected_set:
                stack[index], stack[index + 1] = stack[index + 1], stack[index]
    else:
        for index in range(1, len(stack)):
            if stack[index] in selected_set and stack[index - 1] not in selected_set:
                stack[index], stack[index - 1] = stack[index - 1], stack[index]

    if stack == before:
        page.status_label.setText("A seleção já está no limite dessa ordem de camadas.")
        return

    # Normaliza apenas a ordem dos objetos principais. A hierarquia e o z-order
    # interno dos filhos de grupos permanecem inalterados.
    for index, item in enumerate(stack, 1):
        item.setZValue(float(index))

    direction_label = "uma camada à frente" if direction > 0 else "uma camada atrás"
    _finish_composition(page, selected, f"Camada(s) movida(s) {direction_label}.")


def _sync_controls(page) -> None:
    if not getattr(page, "_v151_installed", False):
        return
    roots = _selected_roots(page)
    movable, _skipped = _movable_selection(page)
    count = len(roots)
    page.v151_selection_count.setText(
        f"{count} objeto(s) selecionado(s) · {len(movable)} editável(is)"
    )
    enough_for_align = len(movable) >= 2
    enough_for_distribute = len(movable) >= 3
    for button in page.v151_align_buttons.values():
        button.setEnabled(enough_for_align)
    page.v151_distribute_h_button.setEnabled(enough_for_distribute)
    page.v151_distribute_v_button.setEnabled(enough_for_distribute)
    page.v151_raise_button.setEnabled(bool(movable))
    page.v151_lower_button.setEnabled(bool(movable))
    has_objects = bool(page._content_items())
    page.v151_select_all_button.setEnabled(has_objects)
    page.v151_invert_button.setEnabled(has_objects)
    page.v151_clear_button.setEnabled(bool(roots))


def _install_composition_panel(page) -> None:
    scroll = page.findChild(QScrollArea, "artStudioLayersScroll")
    content = scroll.widget() if scroll is not None else None
    layout = content.layout() if content is not None else None
    if layout is None:
        return

    frame = QFrame(content)
    frame.setObjectName("artStudioCompositionPanelV151")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    box = QVBoxLayout(frame)
    box.setContentsMargins(8, 8, 8, 8)
    box.setSpacing(6)

    title = QLabel("COMPOSIÇÃO E ALINHAMENTO")
    title.setObjectName("artSmallLabel")
    box.addWidget(title)
    page.v151_selection_count = QLabel("0 objeto(s) selecionado(s)")
    page.v151_selection_count.setWordWrap(True)
    page.v151_selection_count.setObjectName("muted")
    box.addWidget(page.v151_selection_count)

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(5)
    grid.setVerticalSpacing(5)
    page.v151_align_buttons = {}
    align_specs = (
        ("left", "Esquerda", "Alinhar pelas bordas esquerdas"),
        ("center_x", "Centro H", "Alinhar pelo centro horizontal"),
        ("right", "Direita", "Alinhar pelas bordas direitas"),
        ("top", "Topo", "Alinhar pelas bordas superiores"),
        ("center_y", "Centro V", "Alinhar pelo centro vertical"),
        ("bottom", "Base", "Alinhar pelas bordas inferiores"),
    )
    for index, (mode, label, tooltip) in enumerate(align_specs):
        button = QPushButton(label)
        button.setProperty("secondary", True)
        button.setMinimumHeight(30)
        button.setToolTip(tooltip + " da área total selecionada.")
        button.clicked.connect(lambda _checked=False, value=mode: _align_selection(page, value))
        page.v151_align_buttons[mode] = button
        grid.addWidget(button, index // 3, index % 3)
    box.addLayout(grid)

    page.v151_distribute_h_button = QPushButton("Distribuir horizontal")
    page.v151_distribute_v_button = QPushButton("Distribuir vertical")
    page.v151_raise_button = QPushButton("Avançar uma camada")
    page.v151_lower_button = QPushButton("Recuar uma camada")
    for button in (
        page.v151_distribute_h_button,
        page.v151_distribute_v_button,
        page.v151_raise_button,
        page.v151_lower_button,
    ):
        button.setProperty("secondary", True)
        button.setMinimumHeight(31)
        box.addWidget(button)
    page.v151_distribute_h_button.clicked.connect(lambda: _distribute_selection(page, "horizontal"))
    page.v151_distribute_v_button.clicked.connect(lambda: _distribute_selection(page, "vertical"))
    page.v151_raise_button.clicked.connect(lambda: _move_layer_one_step(page, 1))
    page.v151_lower_button.clicked.connect(lambda: _move_layer_one_step(page, -1))

    selection_grid = QGridLayout()
    selection_grid.setContentsMargins(0, 0, 0, 0)
    selection_grid.setHorizontalSpacing(5)
    page.v151_select_all_button = QPushButton("Selecionar tudo")
    page.v151_invert_button = QPushButton("Inverter")
    page.v151_clear_button = QPushButton("Limpar seleção")
    for button in (page.v151_select_all_button, page.v151_invert_button, page.v151_clear_button):
        button.setProperty("secondary", True)
        button.setMinimumHeight(30)
    selection_grid.addWidget(page.v151_select_all_button, 0, 0, 1, 2)
    selection_grid.addWidget(page.v151_invert_button, 1, 0)
    selection_grid.addWidget(page.v151_clear_button, 1, 1)
    box.addLayout(selection_grid)
    hint = QLabel("Dica: use Ctrl+clique ou arraste uma área no canvas para selecionar vários objetos.")
    hint.setWordWrap(True)
    hint.setObjectName("muted")
    box.addWidget(hint)

    page.v151_select_all_button.clicked.connect(lambda: _select_all(page))
    page.v151_invert_button.clicked.connect(lambda: _invert_selection(page))
    page.v151_clear_button.clicked.connect(lambda: _clear_selection(page))

    # Inserir depois dos painéis de tamanho/posição/estilo já existentes.
    index = layout.indexOf(getattr(page, "v149_shape_style_frame", None))
    if index < 0:
        index = layout.indexOf(getattr(page, "v148_size_frame", None))
    layout.insertWidget(index + 1 if index >= 0 else layout.count(), frame)
    page.v151_composition_frame = frame


def _install_shortcuts(page) -> None:
    shortcuts = (
        ("Alinhar seleção à esquerda", "Ctrl+Alt+Left", lambda: _align_selection(page, "left")),
        ("Centralizar seleção horizontalmente", "Ctrl+Alt+H", lambda: _align_selection(page, "center_x")),
        ("Alinhar seleção à direita", "Ctrl+Alt+Right", lambda: _align_selection(page, "right")),
        ("Alinhar seleção ao topo", "Ctrl+Alt+Up", lambda: _align_selection(page, "top")),
        ("Centralizar seleção verticalmente", "Ctrl+Alt+V", lambda: _align_selection(page, "center_y")),
        ("Alinhar seleção à base", "Ctrl+Alt+Down", lambda: _align_selection(page, "bottom")),
        ("Distribuir seleção horizontalmente", "Ctrl+Alt+Shift+H", lambda: _distribute_selection(page, "horizontal")),
        ("Distribuir seleção verticalmente", "Ctrl+Alt+Shift+V", lambda: _distribute_selection(page, "vertical")),
        ("Avançar uma camada", "Ctrl+Alt+]", lambda: _move_layer_one_step(page, 1)),
        ("Recuar uma camada", "Ctrl+Alt+[", lambda: _move_layer_one_step(page, -1)),
    )
    for label, sequence, callback in shortcuts:
        action = QAction(label, page)
        action.setShortcut(QKeySequence(sequence))
        action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(lambda _checked=False, fn=callback: fn())
        page.addAction(action)


def enhance_art_studio_page_v151(page) -> None:
    """Instala V151 uma única vez após a V150."""
    if getattr(page, "_v151_installed", False):
        return
    page._v151_installed = True
    _install_composition_panel(page)
    if not hasattr(page, "v151_select_all_button"):
        # Não interrompe a inicialização principal caso a área de camadas não
        # esteja disponível em uma configuração alternativa da interface.
        page._v151_installed = False
        return
    _install_shortcuts(page)
    page.scene.selectionChanged.connect(lambda: _sync_controls(page))
    page.v151_select_all_button.setEnabled(bool(page._content_items()))
    _sync_controls(page)
    page.status_label.setText(
        "V151: composição de múltiplos objetos, alinhamento e distribuição uniformes, "
        "seleção rápida e organização de camadas por etapas."
    )


def install_art_studio_v151() -> None:
    """Conecta a camada V151 à página montada pelas versões anteriores."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v151_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v151(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v151(page)

    MainWindow.__init__ = init_with_v151
    MainWindow._v151_integration_installed = True
