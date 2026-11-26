from __future__ import annotations

"""V170 — exclusão confiável, interface refinada e compactação do cabeçalho global.

O tratamento de Delete fica centralizado, respeita campos de edição e camadas
bloqueadas, e opera tanto na seleção do canvas quanto na lista de camadas.
A identidade visual é própria da Central: azul profundo, grafite, dourado e
um acento turquesa, mantendo a estrutura de documentos e os recursos V161–V169.
"""

import weakref

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from monitor_noticias.ui.art_studio_delete_engine_v170 import deletion_plan
from monitor_noticias.ui.art_studio_page import CANVAS_BG_KEY, ITEM_KIND_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v154 import (
    _refresh_status as _refresh_layer_status,
    _selected_layer_items,
)
from monitor_noticias.ui.art_studio_v154 import _schedule_history as _schedule_layer_history
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave


_DARK = {
    "pasteboard": "#101B27",
    "panel": "#172838",
    "panel_alt": "#1D3346",
    "border": "#314A5E",
    "text": "#E9F0F5",
    "muted": "#9CB0BF",
    "accent": "#D6B66D",
    "accent_text": "#14283A",
    "signal": "#50C4C6",
    "field": "#203A4F",
    "hover": "#29485D",
}
_LIGHT = {
    "pasteboard": "#E7EDF2",
    "panel": "#FFFFFF",
    "panel_alt": "#F4F7F9",
    "border": "#D4DEE6",
    "text": "#1A2D3C",
    "muted": "#6F8291",
    "accent": "#B18B3E",
    "accent_text": "#FFFFFF",
    "signal": "#168E98",
    "field": "#FFFFFF",
    "hover": "#EAF1F5",
}


def _style_for_theme(theme: str) -> str:
    p = _DARK if theme == "escuro" else _LIGHT
    return f"""
    QWidget#artStudioPage {{ background:{p['pasteboard']}; color:{p['text']}; }}
    QFrame#artStudioToolbar {{ background:{p['panel']}; border:1px solid {p['border']}; border-radius:13px; }}
    QFrame#artStudioPanel {{ background:{p['panel']}; border:1px solid {p['border']}; border-radius:14px; }}
    QFrame#artStudioWorkspace {{ background:{p['pasteboard']}; border:1px solid {p['border']}; border-radius:17px; }}
    QGraphicsView#artCanvasView {{ background:{p['pasteboard']}; border:0; border-radius:11px; outline:0; }}
    QTabWidget#artStudioElementsTabs::pane, QTabWidget#artStudioInspectorTabs::pane {{ background:{p['panel_alt']}; border:1px solid {p['border']}; border-radius:10px; top:-1px; }}
    QTabBar::tab {{ background:{p['panel_alt']}; color:{p['muted']}; border:1px solid transparent; border-radius:7px; padding:9px 11px; margin:2px; min-height:22px; font-size:9px; font-weight:750; }}
    QTabBar::tab:selected {{ background:{p['panel']}; color:{p['text']}; border:1px solid {p['accent']}; }}
    QTabBar::tab:hover {{ background:{p['hover']}; color:{p['text']}; }}
    QLabel#artStudioBrandTitle {{ color:{p['text']}; font-size:14px; font-weight:950; letter-spacing:0.5px; }}
    QLabel#artStudioBrandSub {{ color:{p['muted']}; font-size:8px; font-weight:800; letter-spacing:1.3px; }}
    QLabel#artStudioSectionHeading {{ color:{p['text']}; font-size:11px; font-weight:900; letter-spacing:0.4px; }}
    QLabel#artStudioSectionHint {{ color:{p['muted']}; font-size:9px; }}
    QPushButton {{ min-height:34px; border-radius:8px; padding:5px 10px; font-size:9px; font-weight:750; }}
    QPushButton[secondary="true"] {{ background:{p['panel_alt']}; color:{p['text']}; border:1px solid {p['border']}; }}
    QPushButton[secondary="true"]:hover {{ background:{p['hover']}; border-color:{p['signal']}; }}
    QPushButton[danger="true"] {{ background:#8C3544; color:#FFFFFF; border:1px solid #A64C5B; }}
    QPushButton[danger="true"]:hover {{ background:#A54150; border-color:#C35A69; }}
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{ background:{p['field']}; color:{p['text']}; border:1px solid {p['border']}; border-radius:7px; padding:6px 8px; min-height:25px; selection-background-color:{p['signal']}; }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{ border-color:{p['signal']}; }}
    QListWidget#artLayersList {{ background:{p['panel_alt']}; color:{p['text']}; border:1px solid {p['border']}; border-radius:9px; padding:5px; outline:0; }}
    QListWidget#artLayersList::item {{ min-height:31px; border-radius:6px; padding:4px 7px; margin:1px; }}
    QListWidget#artLayersList::item:selected {{ background:{p['signal']}; color:#FFFFFF; }}
    QScrollBar:vertical {{ background:transparent; width:7px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{p['border']}; border-radius:3px; min-height:26px; }}
    QScrollBar::handle:vertical:hover {{ background:{p['signal']}; }}
    QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal {{ background:{p['border']}; border-radius:3px; margin:7px 2px; }}
    QSplitter#artStudioWorkspaceSplitterV162::handle:horizontal:hover {{ background:{p['signal']}; }}
    QFrame#artStudioLayersDeleteRowV170 {{ background:transparent; border:0; }}
    QPushButton#artStudioDeleteLayersV170 {{ min-height:32px; font-size:9px; font-weight:850; }}
    """


def _wrap_v161_skin() -> None:
    try:
        from monitor_noticias.ui import art_studio_v161
    except Exception:
        return
    if getattr(art_studio_v161, "_v170_skin_wrapped", False):
        return
    original = art_studio_v161._skin_stylesheet

    def skin_with_v170(theme: str) -> str:
        return original(theme) + _style_for_theme(theme)

    art_studio_v161._skin_stylesheet = skin_with_v170
    art_studio_v161._v170_skin_wrapped = True


def _inside(widget: QWidget | None, ancestor: QWidget) -> bool:
    if widget is None:
        return False
    return widget is ancestor or ancestor.isAncestorOf(widget)


def _is_text_entry_focus(page, focus: QWidget | None) -> bool:
    if focus is not None and isinstance(
        focus,
        (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox),
    ):
        return True
    if isinstance(focus, QComboBox) and focus.isEditable():
        return True
    try:
        scene_focus = page.scene.focusItem()
        from PySide6.QtWidgets import QGraphicsTextItem

        if (
            isinstance(scene_focus, QGraphicsTextItem)
            and scene_focus.textInteractionFlags() != Qt.TextInteractionFlag.NoTextInteraction
        ):
            return True
    except RuntimeError:
        return False
    return False


def _selection_for_delete(page, focus: QWidget | None) -> list:
    layers = getattr(page, "layers", None)
    layer_has_focus = layers is not None and _inside(focus, layers)

    selected = []
    if layer_has_focus:
        selected = _selected_layer_items(page, fallback=False)
        if not selected:
            selected = _selected_layer_items(page, fallback=True)
    else:
        try:
            selected = list(page.scene.selectedItems())
        except RuntimeError:
            selected = []
        if not selected:
            selected = _selected_layer_items(page, fallback=True)

    return [
        item for item in selected
        if item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
    ]


def _refresh_after_delete(page, preserved: list) -> None:
    page.scene.clearSelection()
    for item in preserved:
        try:
            if item.scene() is page.scene and item.isVisible():
                item.setSelected(True)
        except RuntimeError:
            continue

    # A seleção da cena sincroniza imediatamente a lista; reaplicamos a seleção
    # completa ao final para manter também as camadas ocultas selecionadas.
    page._v154_layer_selection = list(preserved)
    page._v145_active_item = preserved[0] if len(preserved) == 1 else None
    page._refresh_layers(select_item=preserved[0] if len(preserved) == 1 else None)
    if len(preserved) == 1:
        page._update_selection_controls(preserved[0])
    else:
        page._update_selection_controls(None)
    for callback_name in ("_v148_sync_handles", "_v148_update_dimensions", "_v149_sync_controls"):
        callback = getattr(page, callback_name, None)
        if callable(callback):
            callback()
    try:
        _refresh_layer_status(page)
    except (AttributeError, RuntimeError):
        pass


def _delete_active_selection(page) -> int:
    focus = QApplication.focusWidget()
    selected = _selection_for_delete(page, focus)
    deletable, preserved = deletion_plan(
        selected,
        parent_of=lambda item: item.parentItem(),
        belongs_to_scene=lambda item: item.scene() is page.scene,
        is_locked=lambda item: bool(item.data(LOCKED_KEY)),
    )

    if not deletable:
        if preserved:
            page.status_label.setText(
                "Nenhuma camada foi excluída: desbloqueie as camadas selecionadas."
            )
        else:
            page.status_label.setText("Selecione uma ou mais camadas para excluir.")
        return 0

    removed_count = 0
    for item in deletable:
        try:
            if item.scene() is page.scene:
                page.scene.removeItem(item)
                removed_count += 1
        except RuntimeError:
            continue

    _refresh_after_delete(page, preserved)
    _schedule_layer_history(page)
    _schedule_autosave(page)

    suffix = f" · {len(preserved)} bloqueada(s) preservada(s)" if preserved else ""
    page.status_label.setText(
        f"{removed_count} camada(s) excluída(s) com sucesso{suffix}."
    )
    return removed_count


class _DeleteKeyFilter(QObject):
    """Filtro fino para capturar Delete somente dentro do Estúdio."""

    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        page = self._page_ref()
        if page is None or event.type() != QEvent.Type.KeyPress:
            return False
        if event.key() != Qt.Key.Key_Delete:
            return False

        focus = QApplication.focusWidget()
        if not _inside(focus, page):
            return False
        if _is_text_entry_focus(page, focus):
            return False

        _delete_active_selection(page)
        event.accept()
        return True


def _disable_conflicting_delete_shortcuts(page) -> None:
    for action in list(page.actions()):
        try:
            sequences = action.shortcuts()
        except RuntimeError:
            continue
        labels = {
            sequence.toString(QKeySequence.SequenceFormat.PortableText).strip().casefold()
            for sequence in sequences
        }
        if labels.intersection({"delete", "del"}):
            action.setShortcuts([])


def _install_delete_actions(page) -> None:
    if getattr(page, "_v170_delete_installed", False):
        return
    _disable_conflicting_delete_shortcuts(page)

    delete_button = getattr(page, "delete_button", None)
    if isinstance(delete_button, QPushButton):
        try:
            delete_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        delete_button.clicked.connect(lambda _checked=False: _delete_active_selection(page))
        delete_button.setText("Excluir seleção")
        delete_button.setToolTip("Remove todas as camadas selecionadas e desbloqueadas. Atalho: Delete")

    tabs = getattr(page, "_v161_inspector_tabs", None)
    if isinstance(tabs, QTabWidget) and tabs.count() > 0:
        layers_page = tabs.widget(0)
        layout = layers_page.layout() if layers_page is not None else None
        if layout is not None:
            button = QPushButton("Excluir camadas selecionadas  ·  Delete", layers_page)
            button.setObjectName("artStudioDeleteLayersV170")
            button.setProperty("danger", True)
            button.setToolTip("Exclui a seleção atual sem remover camadas bloqueadas.")
            button.clicked.connect(lambda _checked=False: _delete_active_selection(page))
            layout.insertWidget(min(2, layout.count()), button)
            page.v170_layers_delete_button = button

    app = QApplication.instance()
    if app is not None:
        key_filter = _DeleteKeyFilter(page)
        app.installEventFilter(key_filter)
        page._v170_delete_key_filter = key_filter

    page._v170_delete_installed = True


def _hide_global_header_widget(window, name: str) -> None:
    widget = getattr(window, name, None)
    if not isinstance(widget, QWidget):
        return
    widget.hide()
    widget.setMinimumSize(0, 0)
    widget.setMaximumSize(0, 0)
    policy = widget.sizePolicy()
    policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
    policy.setVerticalPolicy(QSizePolicy.Policy.Ignored)
    widget.setSizePolicy(policy)


def _compact_main_header(window) -> None:
    if getattr(window, "_v170_header_compacted", False):
        return
    # A faixa é comum a todas as páginas. Os recursos continuam ativos nos
    # controladores e nas configurações; apenas os cartões visuais são ocultos.
    for name in (
        "proxy_chip",
        "auto_chip",
        "clock",
        "_auth_user_label",
        "_auth_account_button",
        "_auth_logout_button",
        "global_search",
    ):
        _hide_global_header_widget(window, name)

    window._v170_header_compacted = True
    central = window.centralWidget()
    if central is not None:
        central.updateGeometry()
        central.update()


def _polish_workspace(page) -> None:
    if getattr(page, "_v170_visual_refinement_done", False):
        return
    page.setProperty("artStudioVisualSystem", "central-studio-v170")

    # Painéis equilibrados: o canvas recebe a maior parte da largura útil.
    splitter = getattr(page, "_v162_workspace_splitter", None)
    if splitter is not None:
        panels = getattr(page, "_v162_workspace_panels", None)
        if panels and len(panels) == 3:
            left, center, right = panels
            left.setMinimumWidth(190)
            left.setMaximumWidth(320)
            center.setMinimumWidth(430)
            right.setMinimumWidth(270)
            right.setMaximumWidth(385)
        if splitter.width() > 0:
            available = max(1, splitter.width() - 2 * splitter.handleWidth())
            left_size = min(250, max(190, round(available * 0.20)))
            right_size = min(365, max(270, round(available * 0.29)))
            center_size = max(430, available - left_size - right_size)
            sizes = [left_size, center_size, right_size]
            page._v162_default_split_sizes = sizes
            splitter.setSizes(sizes)
        else:
            page._v162_default_split_sizes = [230, 650, 320]

    # As abas laterais ficam navegáveis quando o número de ferramentas cresce.
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if isinstance(tabs, QTabWidget):
        bar = tabs.tabBar()
        bar.setUsesScrollButtons(True)
        bar.setExpanding(False)
        bar.setElideMode(Qt.TextElideMode.ElideRight)
        bar.setMovable(False)

    left_tabs = getattr(page, "_v161_left_tabs", None)
    if isinstance(left_tabs, QTabWidget):
        left_tabs.tabBar().setUsesScrollButtons(True)
        left_tabs.tabBar().setExpanding(False)
        left_tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)

    # Identidade original do editor, sem reproduzir marca ou ícones de terceiros.
    for label in page.findChildren(QWidget):
        name = label.objectName()
        if name == "artStudioBrandTitle":
            try:
                label.setText("CENTRAL STUDIO")
            except AttributeError:
                pass
        elif name == "artStudioBrandSub":
            try:
                label.setText("DESIGN  •  COMPOSIÇÃO  •  PUBLICAÇÃO")
            except AttributeError:
                pass

    page._v170_visual_refinement_done = True


def enhance_art_studio_page_v170(page) -> None:
    if getattr(page, "_v170_installed", False):
        return
    _install_delete_actions(page)
    _polish_workspace(page)
    page._v170_installed = True
    page.status_label.setText(
        "Central Studio V170: exclusão confiável de camadas, seleção múltipla e interface refinada."
    )


def install_art_studio_v170() -> None:
    """Instala a camada V170 depois do encaixe magnético V169."""
    _wrap_v161_skin()
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v170_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v170(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v170(page)
        # Os controles de autenticação são inseridos pela aplicação logo após
        # construir a MainWindow; o timer os oculta depois dessa integração.
        QTimer.singleShot(0, lambda window=self: _compact_main_header(window))

    MainWindow.__init__ = init_with_v170
    MainWindow._v170_integration_installed = True
