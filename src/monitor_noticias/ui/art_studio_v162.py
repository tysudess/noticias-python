from __future__ import annotations

"""V162 — bancada de trabalho adaptável e inspetor contextual.

- Converte as três colunas do Estúdio em painéis redimensionáveis.
- Acrescenta modo foco para ampliar temporariamente o canvas.
- Exibe um resumo contextual do objeto/seleção no inspetor Design.
- Não substitui canvas, seleção, comandos, histórico, autosave ou .centralart.
"""

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QAction, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import CANVAS_BG_KEY, ITEM_KIND_KEY, ITEM_NAME_KEY


_INSTALLED = False


def _panel_for_title(page, title: str) -> QFrame | None:
    label = next(
        (item for item in page.findChildren(QLabel, "artPanelTitle") if item.text() == title),
        None,
    )
    parent = label.parentWidget() if label is not None else None
    return parent if isinstance(parent, QFrame) else None


def _layout_has_targets(layout: QLayout, targets: set[int]) -> bool:
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None and id(widget) in targets:
            return True
        child_layout = item.layout()
        if child_layout is not None and _layout_has_targets(child_layout, targets):
            return True
    return False


def _find_workspace_layout(page, widgets: tuple[QWidget, ...]) -> QLayout | None:
    root = page.layout()
    if root is None:
        return None
    target_ids = {id(widget) for widget in widgets if widget is not None}
    for index in range(root.count()):
        item = root.itemAt(index)
        candidate = item.layout() if item is not None else None
        if candidate is not None and _layout_has_targets(candidate, target_ids):
            return candidate
    return None



class _SplitterInitialSizeFilter(QObject):
    """Aplica as larguras iniciais quando a página aparece pela primeira vez."""

    def __init__(self, page: QWidget, splitter: QSplitter) -> None:
        super().__init__(page)
        self._page = page
        self._splitter = splitter
        self._applied = False

    def eventFilter(self, watched, event):
        if not self._applied and event.type() == QEvent.Type.Show:
            QTimer.singleShot(0, self._apply_initial_sizes)
        return False

    def _apply_initial_sizes(self) -> None:
        if self._applied or not self._splitter.isVisible() or self._splitter.width() <= 0:
            return
        available = max(1, self._splitter.width() - self._splitter.handleWidth() * 2)
        left_size = min(260, max(190, round(available * 0.19)))
        right_size = min(360, max(285, round(available * 0.27)))
        center_size = max(430, available - left_size - right_size)
        self._splitter.setSizes([left_size, center_size, right_size])
        self._page._v162_default_split_sizes = self._splitter.sizes()
        self._applied = True


def _install_resizable_workspace(page) -> None:
    if getattr(page, "_v162_splitter_installed", False):
        return

    left = _panel_for_title(page, "ELEMENTOS")
    right = _panel_for_title(page, "CAMADAS E OBJETOS")
    center = page.findChild(QFrame, "artStudioWorkspace")
    if left is None or right is None or center is None:
        return

    workspace_layout = _find_workspace_layout(page, (left, center, right))
    if workspace_layout is None:
        return

    splitter = QSplitter(Qt.Orientation.Horizontal, page)
    splitter.setObjectName("artStudioWorkspaceSplitterV162")
    splitter.setHandleWidth(8)
    splitter.setChildrenCollapsible(False)
    splitter.setOpaqueResize(True)
    splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # V161 fixava as larguras. V162 libera os painéis mantendo limites seguros
    # para que o canvas continue utilizável mesmo em janelas menores.
    left.setMinimumWidth(180)
    left.setMaximumWidth(350)
    left.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    right.setMinimumWidth(265)
    right.setMaximumWidth(445)
    right.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    center.setMinimumWidth(430)
    center.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    for widget in (left, center, right):
        splitter.addWidget(widget)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)
    splitter.setStretchFactor(2, 0)
    splitter.setStyleSheet(
        "QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal {"
        "background:palette(mid);border-radius:3px;margin:6px 1px;}"
        "QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal:hover {"
        "background:palette(highlight);margin:3px 0px;}"
    )

    while workspace_layout.count():
        item = workspace_layout.takeAt(0)
        del item
    workspace_layout.setContentsMargins(0, 0, 0, 0)
    workspace_layout.setSpacing(0)
    workspace_layout.addWidget(splitter)

    page._v162_workspace_splitter = splitter
    page._v162_workspace_panels = (left, center, right)
    page._v162_default_split_sizes = [224, 620, 336]
    page._v162_splitter_installed = True

    size_filter = _SplitterInitialSizeFilter(page, splitter)
    page._v162_size_filter = size_filter
    page.installEventFilter(size_filter)


def _set_focus_mode(page, enabled: bool) -> None:
    splitter = getattr(page, "_v162_workspace_splitter", None)
    panels = getattr(page, "_v162_workspace_panels", None)
    button = getattr(page, "v162_focus_button", None)
    if splitter is None or not panels:
        return

    left, _center, right = panels
    if enabled:
        current_sizes = splitter.sizes()
        if len(current_sizes) == 3 and sum(current_sizes) > 0:
            page._v162_saved_split_sizes = current_sizes
        left.hide()
        right.hide()
        if button is not None:
            button.setText("⛶  Restaurar painéis")
            button.setToolTip("Sair do modo foco e restaurar os painéis laterais")
    else:
        left.show()
        right.show()
        sizes = getattr(page, "_v162_saved_split_sizes", None)
        if not sizes or len(sizes) != 3 or sum(sizes) <= 0:
            sizes = getattr(page, "_v162_default_split_sizes", [224, 620, 336])
        QTimer.singleShot(0, lambda value=list(sizes): splitter.setSizes(value))
        if button is not None:
            button.setText("⛶  Foco no canvas")
            button.setToolTip("Ocultar temporariamente os painéis laterais e ampliar o canvas")


def _install_focus_control(page) -> None:
    if getattr(page, "_v162_focus_control_installed", False):
        return
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    export_button = getattr(page, "export_button", None)
    if layout is None or export_button is None:
        return

    button = QPushButton("⛶  Foco no canvas", toolbar)
    button.setObjectName("artStudioFocusButtonV162")
    button.setProperty("secondary", True)
    button.setCheckable(True)
    button.setMinimumHeight(38)
    button.setToolTip("Ocultar temporariamente os painéis laterais e ampliar o canvas")
    insert_at = layout.indexOf(export_button)
    layout.insertWidget(insert_at + 1 if insert_at >= 0 else layout.count(), button)
    button.toggled.connect(lambda checked: _set_focus_mode(page, bool(checked)))

    action = QAction("Alternar modo foco do canvas", page)
    action.setShortcut("Ctrl+Shift+F")
    action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    action.triggered.connect(lambda: button.setChecked(not button.isChecked()))
    page.addAction(action)

    page.v162_focus_button = button
    page._v162_focus_action = action
    page._v162_focus_control_installed = True


def _selection_values(page) -> tuple[str, str, str]:
    selected = []
    for item in page.scene.selectedItems():
        try:
            if item.scene() is page.scene and item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY:
                selected.append(item)
        except RuntimeError:
            continue

    if not selected:
        return (
            "SEM SELEÇÃO",
            "Selecione um objeto no canvas ou na lista de camadas",
            "As dimensões e a posição aparecerão aqui",
        )

    kind_labels = {
        "text": "TEXTO",
        "image": "IMAGEM",
        "shape": "FORMA",
        "group": "GRUPO",
    }
    bounds = selected[0].sceneBoundingRect()
    for item in selected[1:]:
        bounds = bounds.united(item.sceneBoundingRect())

    if len(selected) == 1:
        item = selected[0]
        kind = str(item.data(ITEM_KIND_KEY) or "object")
        kind_label = kind_labels.get(kind, "OBJETO")
        name = str(item.data(ITEM_NAME_KEY) or "").strip()
        if not name and kind == "text":
            name = str(item.toPlainText() or "Texto").splitlines()[0]
        if not name:
            name = "Objeto sem nome"
    else:
        kind_label = "SELEÇÃO MÚLTIPLA"
        name = f"{len(selected)} objetos selecionados"

    name = name.replace("\n", " ").strip()
    if len(name) > 54:
        name = name[:51].rstrip() + "…"
    metrics = (
        f"{bounds.width():.0f} × {bounds.height():.0f} px"
        f"   ·   X {bounds.x():.0f}"
        f"   ·   Y {bounds.y():.0f}"
    )
    return kind_label, name or "Objeto sem nome", metrics


def _refresh_selection_summary(page) -> None:
    if not getattr(page, "_v162_selection_card_installed", False):
        return
    kind, name, metrics = _selection_values(page)
    page.v162_selection_kind.setText(kind)
    page.v162_selection_name.setText(name)
    page.v162_selection_metrics.setText(metrics)


def _install_selection_summary(page) -> None:
    if getattr(page, "_v162_selection_card_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if tabs is None or tabs.count() < 2:
        return
    design_page = tabs.widget(1)
    layout = design_page.layout() if design_page is not None else None
    if layout is None:
        return

    card = QFrame(design_page)
    card.setObjectName("artStudioSelectionCardV162")
    box = QVBoxLayout(card)
    box.setContentsMargins(10, 9, 10, 9)
    box.setSpacing(5)

    eyebrow = QLabel("SELEÇÃO ATUAL", card)
    eyebrow.setObjectName("artStudioSelectionEyebrowV162")
    box.addWidget(eyebrow)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    page.v162_selection_kind = QLabel("SEM SELEÇÃO", card)
    page.v162_selection_kind.setObjectName("artStudioSelectionKindV162")
    page.v162_selection_kind.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.v162_selection_kind.setMinimumWidth(92)
    page.v162_selection_kind.setWordWrap(True)
    page.v162_selection_name = QLabel("Selecione um objeto", card)
    page.v162_selection_name.setObjectName("artStudioSelectionNameV162")
    page.v162_selection_name.setWordWrap(True)
    row.addWidget(page.v162_selection_kind, 0)
    row.addWidget(page.v162_selection_name, 1)
    box.addLayout(row)

    page.v162_selection_metrics = QLabel("Dimensões e posição do objeto", card)
    page.v162_selection_metrics.setObjectName("artStudioSelectionMetricsV162")
    page.v162_selection_metrics.setWordWrap(True)
    box.addWidget(page.v162_selection_metrics)

    layout.insertWidget(2, card)
    page.v162_selection_card = card
    page._v162_selection_card_installed = True

    timer = QTimer(page)
    timer.setSingleShot(True)
    timer.setInterval(90)
    timer.timeout.connect(lambda: _refresh_selection_summary(page))
    page._v162_selection_timer = timer
    page.scene.selectionChanged.connect(timer.start)
    page.scene.changed.connect(lambda *_args: timer.start())
    _refresh_selection_summary(page)


def _selection_card_stylesheet(page) -> str:
    # Usa papéis da paleta Qt para acompanhar automaticamente os temas da Central.
    return (
        "QFrame#artStudioSelectionCardV162 {background:palette(alternate-base);border:1px solid palette(mid);border-radius:10px;}"
        "QLabel#artStudioSelectionEyebrowV162 {color:palette(mid);background:transparent;font-size:8px;font-weight:900;letter-spacing:1px;}"
        "QLabel#artStudioSelectionKindV162 {color:palette(highlighted-text);background:palette(highlight);border:0;border-radius:6px;padding:5px 7px;font-size:8px;font-weight:900;}"
        "QLabel#artStudioSelectionNameV162 {color:palette(text);background:transparent;font-size:10px;font-weight:800;}"
        "QLabel#artStudioSelectionMetricsV162 {color:palette(mid);background:transparent;font-size:8px;font-weight:650;}"
    )


def _apply_selection_card_skin(page) -> None:
    card = getattr(page, "v162_selection_card", None)
    if card is not None:
        card.setStyleSheet(_selection_card_stylesheet(page))


def enhance_art_studio_page_v162(page) -> None:
    if getattr(page, "_v162_installed", False):
        return
    _install_resizable_workspace(page)
    if not getattr(page, "_v162_splitter_installed", False):
        return
    _install_focus_control(page)
    _install_selection_summary(page)
    _apply_selection_card_skin(page)
    page._v162_installed = True


def install_art_studio_v162() -> None:
    """Instala a bancada adaptável depois da reformulação V161."""
    global _INSTALLED
    if _INSTALLED:
        return
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v162_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v162(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v162(page)

    MainWindow.__init__ = init_with_v162
    MainWindow._v162_integration_installed = True
    _INSTALLED = True
