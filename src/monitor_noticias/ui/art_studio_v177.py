from __future__ import annotations

"""V177 — biblioteca visual, camadas inteligentes e navegação refinada.

Atualiza a biblioteca V163 para cartões com prévias, melhora a leitura e a
reorganização do painel de camadas e acrescenta presets/atalhos de zoom. Todas
as ações de documento reutilizam comandos existentes e preservam o formato nativo do projeto.
"""

import weakref

from PySide6.QtCore import QEvent, QObject, QItemSelectionModel, QSize, Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QInputDialog,
    QMenu,
    QListWidget,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QToolButton,
    QSizePolicy,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v154 import _schedule_history
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.art_studio_v163 import PALETTES, TEMPLATES, _insert_template
from monitor_noticias.ui.art_studio_workspace_engine_v177 import (
    layer_context_actions,
    layer_order_z_values,
    library_grid_columns,
    nearest_zoom_preset,
    zoom_factor_to_target,
)


_INSTALLED = False


def _theme_name(page) -> str:
    try:
        from monitor_noticias.ui.art_studio_v176 import _theme_name as theme_name
        return theme_name(page)
    except Exception:
        return "claro"


def _palette(page) -> dict[str, str]:
    try:
        from monitor_noticias.ui.art_studio_v176 import _palette as palette
        return palette(_theme_name(page))
    except Exception:
        dark = _theme_name(page) == "escuro"
        return {
            "panel": "#172532" if dark else "#FFFFFF",
            "panel_alt": "#1D2D3B" if dark else "#F5F7F9",
            "border": "#314556" if dark else "#D8E1E8",
            "text": "#EAF1F5" if dark else "#203748",
            "muted": "#9AABB8" if dark else "#718493",
            "accent": "#41B8B3" if dark else "#167E83",
            "selected": "#244B52" if dark else "#E3F0F0",
            "hover": "#273D4D" if dark else "#EAF2F4",
        }


def _visual_stylesheet(theme: str) -> str:
    dark = theme == "escuro"
    panel = "#172532" if dark else "#FFFFFF"
    panel_alt = "#1D2D3B" if dark else "#F5F7F9"
    border = "#314556" if dark else "#D8E1E8"
    text = "#EAF1F5" if dark else "#203748"
    muted = "#9AABB8" if dark else "#718493"
    accent = "#41B8B3" if dark else "#167E83"
    selected = "#244B52" if dark else "#E3F0F0"
    hover = "#273D4D" if dark else "#EAF2F4"
    return f"""
    QToolButton#artStudioTemplateTileV177 {{
        background:{panel}; color:{text}; border:1px solid {border}; border-radius:9px;
        padding:5px 4px; font-family:'Segoe UI'; font-size:8px; font-weight:750;
    }}
    QToolButton#artStudioTemplateTileV177:hover {{
        background:{hover}; border:1px solid {accent};
    }}
    QListWidget#artLayersList {{
        background:transparent; border:0; padding:3px; outline:0;
        color:{text}; selection-background-color:transparent;
    }}
    QListWidget#artLayersList::item {{ border:0; padding:0; margin:1px 0; }}
    QListWidget#artLayersList::item:selected {{ background:transparent; }}
    QComboBox#artStudioZoomPresetsV177 {{
        background:{panel}; color:{text}; border:1px solid {border};
        border-radius:7px; padding:4px 7px; min-height:24px; min-width:76px;
        font-size:9px; font-weight:800;
    }}
    QComboBox#artStudioZoomPresetsV177:hover {{ border-color:{accent}; }}
    QComboBox#artStudioZoomPresetsV177 QAbstractItemView {{
        background:{panel}; color:{text}; border:1px solid {border};
        selection-background-color:{selected};
    }}
    QLabel#artStudioCanvasMetaV177 {{
        background:{panel_alt}; color:{muted}; border:1px solid {border};
        border-radius:6px; padding:4px 7px; font-size:8px; font-weight:800;
    }}
    """


def _wrap_skin() -> None:
    from monitor_noticias.ui import art_studio_v161
    if getattr(art_studio_v161, "_v177_skin_wrapped", False):
        return
    original = art_studio_v161._skin_stylesheet

    def stylesheet_with_v177(theme: str) -> str:
        return original(theme) + _visual_stylesheet(theme)

    art_studio_v161._skin_stylesheet = stylesheet_with_v177
    art_studio_v161._v177_skin_wrapped = True


def _color(value: str, palette: dict[str, str]) -> QColor:
    return QColor(palette.get(value, value if value.startswith("#") else "#808080"))


def _template_preview_icon(template, palette_name: str) -> QIcon:
    """Miniatura vetorial leve do componente, sem criar itens na cena do projeto."""
    palette = PALETTES.get(palette_name, PALETTES["institucional"])
    width, height = 112, 66
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QColor(palette["surface"]))
    painter.drawRoundedRect(QRectF(1, 1, width - 2, height - 2), 6, 6)
    available_w, available_h = width - 12, height - 12
    sx = available_w / max(1.0, float(template.width))
    sy = available_h / max(1.0, float(template.height))
    scale = min(sx, sy)
    offset_x = (width - template.width * scale) / 2.0
    offset_y = (height - template.height * scale) / 2.0
    painter.save()
    painter.translate(offset_x, offset_y)
    painter.scale(scale, scale)
    for element in template.elements:
        rect = QRectF(element.x, element.y, element.width, element.height)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(_color(element.color, palette))
        if element.kind == "rect":
            painter.drawRoundedRect(rect, 5 / max(scale, 0.05), 5 / max(scale, 0.05))
        elif element.kind == "ellipse":
            painter.drawEllipse(rect)
        elif element.kind == "text":
            # Linhas abstratas simulam hierarquia tipográfica, sem texto ilegível
            # ou excesso de detalhes em uma miniatura de baixa resolução.
            line_height = max(3.0, min(20.0, element.height * 0.18))
            line_width = min(element.width, max(12.0, len(element.value) * max(1.0, element.font_size * 0.34)))
            painter.drawRoundedRect(QRectF(element.x, element.y + element.height * 0.28, line_width, line_height), line_height / 2, line_height / 2)
            if element.height > 70 and len(element.value) > 30:
                second_width = min(element.width * 0.72, line_width * 0.78)
                painter.setOpacity(0.72)
                painter.drawRoundedRect(QRectF(element.x, element.y + element.height * 0.58, second_width, max(2.0, line_height * 0.65)), 4, 4)
                painter.setOpacity(1.0)
    painter.restore()
    painter.end()
    return QIcon(pixmap)


def _find_grid(panel) -> QGridLayout | None:
    root = panel.layout() if panel is not None else None
    if root is None:
        return None
    for index in range(root.count()):
        entry = root.itemAt(index)
        layout = entry.layout() if entry is not None else None
        if isinstance(layout, QGridLayout):
            return layout
    return None


def _restyle_component_tiles(page) -> None:
    panel = getattr(page, "v163_component_panel", None)
    if panel is None:
        return
    palette_name = str(page.v163_palette_combo.currentData() or "institucional")
    palette = PALETTES.get(palette_name, PALETTES["institucional"])
    for button in getattr(page, "v163_template_buttons", []):
        button.setStyleSheet(
            "QToolButton#artStudioTemplateTileV177 {"
            f"background:{palette['surface']};color:{palette['ink']};"
            f"border:1px solid {palette['secondary']};border-bottom:2px solid {palette['accent']};"
            "border-radius:9px;padding:5px 3px;font-size:8px;font-weight:800;}"
            "QToolButton#artStudioTemplateTileV177:hover {"
            f"background:{palette['white']};border:1px solid {palette['accent']};"
            f"border-bottom:2px solid {palette['accent']};}}"
        )


def _layout_component_tiles(page) -> None:
    panel = getattr(page, "v163_component_panel", None)
    grid = _find_grid(panel)
    buttons = list(getattr(page, "v163_template_buttons", []))
    if grid is None or not buttons:
        return
    columns = library_grid_columns(panel.width() - 18, min_card_width=94, gap=7, max_columns=2)
    for button in buttons:
        grid.removeWidget(button)
    for index, button in enumerate(buttons):
        row, column = divmod(index, columns)
        grid.addWidget(button, row, column)
    for column in range(2):
        grid.setColumnStretch(column, 1 if column < columns else 0)
    grid.setHorizontalSpacing(7)
    grid.setVerticalSpacing(7)


def _upgrade_component_library(page) -> None:
    if getattr(page, "_v177_component_library_installed", False):
        return
    panel = getattr(page, "v163_component_panel", None)
    if panel is None:
        return
    grid = _find_grid(panel)
    old_buttons = list(getattr(page, "v163_template_buttons", []))
    if grid is None or not old_buttons:
        return

    for button in old_buttons:
        grid.removeWidget(button)
        button.setParent(None)
        button.deleteLater()

    from PySide6.QtWidgets import QToolButton as ToolButton
    tiles = []
    for template in TEMPLATES:
        button = ToolButton(panel)
        button.setObjectName("artStudioTemplateTileV177")
        button.setProperty("templateKey", template.key)
        button.setText(template.title)
        button.setIcon(_template_preview_icon(template, str(page.v163_palette_combo.currentData() or "institucional")))
        button.setIconSize(QSize(86, 50))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setToolTip(
            f"{template.description}\n\n{template.width} × {template.height} px · {template.category}\nClique para inserir no canvas."
        )
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(False)
        button.setMinimumSize(92, 86)
        button.setMaximumHeight(100)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda _checked=False, key=template.key: _insert_template(page, key))
        tiles.append(button)
    page.v163_template_buttons = tiles
    page._v177_template_resize_timer = QTimer(page)
    page._v177_template_resize_timer.setSingleShot(True)
    page._v177_template_resize_timer.setInterval(20)
    page._v177_template_resize_timer.timeout.connect(lambda: _layout_component_tiles(page))
    page.v163_palette_combo.currentIndexChanged.connect(lambda *_args: _restyle_component_tiles(page))
    _layout_component_tiles(page)
    _restyle_component_tiles(page)
    page._v177_component_library_installed = True


class _LibraryPanelFilter(QObject):
    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)

    def eventFilter(self, watched, event):
        page = self._page_ref()
        if page is not None and event.type() == QEvent.Type.Resize:
            timer = getattr(page, "_v177_template_resize_timer", None)
            if timer is not None:
                timer.start()
        return False


def _install_library_resize_filter(page) -> None:
    panel = getattr(page, "v163_component_panel", None)
    if panel is None or getattr(page, "_v177_library_filter_installed", False):
        return
    filter_object = _LibraryPanelFilter(page)
    page._v177_library_panel_filter = filter_object
    panel.installEventFilter(filter_object)
    page._v177_library_filter_installed = True


class _LayerDelegate(QStyledItemDelegate):
    def __init__(self, page, parent=None):
        super().__init__(parent)
        self._page_ref = weakref.ref(page)

    def sizeHint(self, option, index):  # noqa: N802 - API Qt
        return QSize(max(100, option.rect.width()), 50)

    def paint(self, painter, option, index):  # noqa: N802 - API Qt
        page = self._page_ref()
        if page is None:
            return super().paint(painter, option, index)
        colors = _palette(page)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = option.rect.adjusted(3, 2, -3, -2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        fill = colors["selected"] if selected else colors["hover"] if hovered else colors["panel"]
        border = colors["accent"] if selected else colors["border"] if hovered else "#00000000"
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(fill))
        painter.drawRoundedRect(rect, 7, 7)

        row = index.data(Qt.ItemDataRole.UserRole)
        try:
            item = getattr(page, "_layer_objects", {}).get(int(row))
        except (TypeError, ValueError):
            item = None
        kind = str(item.data(ITEM_KIND_KEY) or "object").lower() if item is not None else "object"
        glyphs = {"image": "▧", "text": "T", "shape": "◇", "group": "▦"}
        labels = {"image": "IMAGEM", "text": "TEXTO", "shape": "FORMA", "group": "GRUPO"}
        glyph = glyphs.get(kind, "•")
        badge_fill = "#DDEFF0" if not selected else colors["panel"]
        if page is not None and _theme_name(page) == "escuro" and not selected:
            badge_fill = "#264A50"
        badge = QRectF(rect.left() + 8, rect.top() + 8, 30, 30)
        painter.setPen(QPen(QColor(colors["border"]), 1))
        painter.setBrush(QColor(badge_fill))
        painter.drawRoundedRect(badge, 7, 7)
        painter.setPen(QColor(colors["accent"]))
        icon_font = QFont("Segoe UI")
        icon_font.setPixelSize(13)
        icon_font.setBold(True)
        painter.setFont(icon_font)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, glyph)

        name = str(item.data(ITEM_NAME_KEY) or "Camada") if item is not None else str(index.data() or "Camada")
        if item is None and len(name) > 3 and name[1:3] == "  ":
            name = name[3:]
        name_rect = rect.adjusted(47, 7, -42, -20)
        painter.setPen(QColor(colors["text"] if item is None or item.isVisible() else colors["muted"]))
        name_font = QFont("Segoe UI")
        name_font.setPixelSize(9)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, max(20, int(name_rect.width()))))

        caption = labels.get(kind, "OBJETO")
        caption_font = QFont("Segoe UI")
        caption_font.setPixelSize(7)
        caption_font.setBold(True)
        painter.setFont(caption_font)
        painter.setPen(QColor(colors["muted"]))
        painter.drawText(rect.adjusted(47, 26, -40, -3), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, caption)

        state = ""
        if item is not None:
            try:
                locked = bool(item.data(LOCKED_KEY))
                visible = bool(item.isVisible())
                if locked:
                    state = "⌑"
                elif not visible:
                    state = "◌"
            except RuntimeError:
                state = ""
        if state:
            state_font = QFont("Segoe UI")
            state_font.setPixelSize(12)
            state_font.setBold(True)
            painter.setFont(state_font)
            painter.setPen(QColor(colors["accent"] if state == "⌑" else colors["muted"]))
            painter.drawText(rect.adjusted(0, 0, -8, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, state)
        painter.restore()


def _item_from_layer_row(page, row):
    if row is None:
        return None
    try:
        key = int(row.data(Qt.ItemDataRole.UserRole))
    except (TypeError, ValueError):
        return None
    return getattr(page, "_layer_objects", {}).get(key)


def _selected_layer_items(page) -> list:
    result = []
    for row in page.layers.selectedItems():
        item = _item_from_layer_row(page, row)
        if item is not None:
            try:
                if item.scene() is page.scene:
                    result.append(item)
            except RuntimeError:
                continue
    return result


def _rename_layer(page, item) -> None:
    current = str(item.data(ITEM_NAME_KEY) or "Camada")
    value, accepted = QInputDialog.getText(page, "Renomear camada", "Nome:", text=current)
    if not accepted or not value.strip():
        return
    item.setData(ITEM_NAME_KEY, value.strip()[:100])
    page._refresh_layers(select_item=item)
    _schedule_history(page)
    _schedule_autosave(page)
    if hasattr(page, "v176_object_name"):
        page.v176_object_name.setText(value.strip()[:100])


def _show_layer_context_menu(page, position) -> None:
    layers = page.layers
    row = layers.itemAt(position)
    if row is not None and not row.isSelected():
        layers.setCurrentItem(row, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    items = _selected_layer_items(page)
    if not items:
        return
    unlocked = all(not bool(item.data(LOCKED_KEY)) for item in items)
    single_kind = str(items[0].data(ITEM_KIND_KEY) or "") if len(items) == 1 else None
    actions = layer_context_actions(selection_count=len(items), all_unlocked=unlocked, single_kind=single_kind)
    menu = QMenu(layers)
    labels = {
        "rename": "Renomear camada…", "visibility": "Mostrar / ocultar",
        "lock": "Bloquear / desbloquear", "duplicate": "Duplicar",
        "front": "Trazer para frente", "back": "Enviar para trás",
        "group": "Agrupar seleção", "ungroup": "Desagrupar grupo",
        "delete": "Excluir seleção",
    }
    action_map = {key: menu.addAction(label) for key, label in labels.items() if key in actions}
    chosen = menu.exec(layers.viewport().mapToGlobal(position))
    if chosen is None:
        return
    key = next((name for name, action in action_map.items() if action is chosen), None)
    if key == "rename" and len(items) == 1:
        _rename_layer(page, items[0])
    elif key == "visibility" and len(items) == 1:
        button = getattr(page, "v145_visibility_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "lock":
        multi_lock = getattr(page, "v176_lock_button", None)
        single_lock = getattr(page, "v145_lock_button", None)
        button = multi_lock if len(items) > 1 else single_lock
        if button is not None and button.isEnabled():
            button.click()
    elif key == "duplicate":
        button = getattr(page, "duplicate_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "front":
        button = getattr(page, "forward_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "back":
        button = getattr(page, "backward_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "group":
        button = getattr(page, "v146_group_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "ungroup":
        button = getattr(page, "v146_ungroup_button", None)
        if button is not None and button.isEnabled():
            button.click()
    elif key == "delete":
        button = getattr(page, "v170_layers_delete_button", None) or getattr(page, "delete_button", None)
        if button is not None and button.isEnabled():
            button.click()


def _commit_layer_order(page) -> None:
    layers = getattr(page, "layers", None)
    if not isinstance(layers, QListWidget):
        return
    ordered = []
    for index in range(layers.count()):
        item = _item_from_layer_row(page, layers.item(index))
        if item is None:
            continue
        try:
            if item.scene() is page.scene:
                ordered.append(item)
        except RuntimeError:
            continue
    if len(ordered) < 2:
        return
    for item, z_value in zip(ordered, layer_order_z_values(len(ordered))):
        item.setZValue(z_value)
    page.scene.update()
    stored = list(getattr(page, "_v154_layer_selection", []))
    selected = [item for item in stored if item in ordered]
    page._refresh_layers(select_item=selected[0] if len(selected) == 1 else None)
    _schedule_history(page)
    _schedule_autosave(page)
    page.status_label.setText("Ordem das camadas atualizada.")


def _install_layer_refinements(page) -> None:
    if getattr(page, "_v177_layers_installed", False):
        return
    layers = getattr(page, "layers", None)
    if not isinstance(layers, QListWidget):
        return
    layers.setItemDelegate(_LayerDelegate(page, layers))
    layers.setSpacing(2)
    layers.setUniformItemSizes(True)
    layers.setMouseTracking(True)
    layers.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    layers.setDragEnabled(True)
    layers.setAcceptDrops(True)
    layers.setDropIndicatorShown(True)
    layers.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    layers.setDefaultDropAction(Qt.DropAction.MoveAction)
    layers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    layers.customContextMenuRequested.connect(lambda pos: _show_layer_context_menu(page, pos))
    try:
        layers.model().rowsMoved.connect(lambda *_args: QTimer.singleShot(0, lambda: _commit_layer_order(page)))
    except (AttributeError, RuntimeError):
        pass
    page._v177_layers_installed = True


def _find_layout_with_widget(layout, widget):
    if layout is None:
        return None
    for index in range(layout.count()):
        entry = layout.itemAt(index)
        if entry is None:
            continue
        if entry.widget() is widget:
            return layout
        child = entry.layout()
        found = _find_layout_with_widget(child, widget) if child is not None else None
        if found is not None:
            return found
    return None


def _zoom_preset_changed(page, index: int) -> None:
    combo = getattr(page, "v177_zoom_combo", None)
    if combo is None or index < 0:
        return
    target = combo.itemData(index)
    if target == "fit":
        page.view_fit()
        return
    try:
        current = float(str(page.zoom_label.text()).replace("%", "").strip())
        factor = zoom_factor_to_target(current, float(target))
    except (TypeError, ValueError, ZeroDivisionError):
        return
    page.view.zoom_by(factor)


def _sync_zoom_preset(page, value=None) -> None:
    combo = getattr(page, "v177_zoom_combo", None)
    if combo is None:
        return
    try:
        current = float(value if isinstance(value, (int, float)) else str(page.zoom_label.text()).replace("%", "").strip())
        preset = nearest_zoom_preset(current)
    except (TypeError, ValueError):
        return
    index = combo.findData(preset)
    if index >= 0:
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)


def _install_zoom_tools(page) -> None:
    if getattr(page, "_v177_zoom_installed", False):
        return
    label = getattr(page, "zoom_label", None)
    if label is None:
        return
    target_layout = _find_layout_with_widget(page.layout(), label)
    if target_layout is None:
        return
    combo = QComboBox(page)
    combo.setObjectName("artStudioZoomPresetsV177")
    for text, value in (("Ajustar", "fit"), ("25%", 25), ("50%", 50), ("75%", 75), ("100%", 100), ("125%", 125), ("150%", 150), ("200%", 200), ("300%", 300)):
        combo.addItem(text, value)
    combo.setToolTip("Zoom do canvas. Atalhos: Ctrl+0 ajustar · Ctrl+1 tamanho real · Ctrl+2 200%.")
    combo.setMinimumWidth(76)
    combo.setMaximumWidth(86)
    combo.setMinimumHeight(28)
    target_layout.insertWidget(target_layout.indexOf(label) + 1, combo)
    combo.currentIndexChanged.connect(lambda index: _zoom_preset_changed(page, index))
    page.v177_zoom_combo = combo
    try:
        page.view.zoomChanged.connect(lambda value: _sync_zoom_preset(page, value))
    except (AttributeError, RuntimeError):
        pass
    for name, sequence, callback in (
        ("fit", "Ctrl+0", page.view_fit),
        ("actual", "Ctrl+1", page.view.actual_size),
        ("double", "Ctrl+2", lambda: page.view.zoom_by(2.0)),
    ):
        shortcut = QShortcut(QKeySequence(sequence), page)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(callback)
        setattr(page, f"_v177_zoom_shortcut_{name}", shortcut)
    page._v177_zoom_installed = True
    QTimer.singleShot(0, lambda: _sync_zoom_preset(page))


def _add_canvas_meta(page) -> None:
    if getattr(page, "_v177_canvas_meta_installed", False):
        return
    size_label = getattr(page, "canvas_size_label", None)
    if size_label is None:
        return
    layout = _find_layout_with_widget(page.layout(), size_label)
    if layout is None:
        return
    from PySide6.QtWidgets import QLabel as Label
    badge = Label(page)
    badge.setObjectName("artStudioCanvasMetaV177")
    layout.insertWidget(layout.indexOf(size_label) + 1, badge)
    page.v177_canvas_meta = badge

    def refresh(*_args):
        index = int(getattr(page, "_v150_active_index", 0)) + 1
        count = len(getattr(page, "_v150_pages", [])) or 1
        badge.setText(f"PÁGINA {index} / {count}")
        badge.setToolTip(f"Página {index} de {count} · {getattr(page, '_width', 1080)} × {getattr(page, '_height', 1080)} px")
    page._v177_refresh_canvas_meta = refresh
    refresh()
    tab_bar = getattr(page, "v150_tab_bar", None)
    if tab_bar is not None:
        tab_bar.currentChanged.connect(refresh)


def _apply_theme(page) -> None:
    try:
        from monitor_noticias.ui import art_studio_v161
        page.setStyleSheet(art_studio_v161._skin_stylesheet(_theme_name(page)))
    except Exception:
        page.setStyleSheet(_visual_stylesheet(_theme_name(page)))
    _restyle_component_tiles(page)


def enhance_art_studio_page_v177(page) -> None:
    if getattr(page, "_v177_installed", False):
        return
    _upgrade_component_library(page)
    _install_library_resize_filter(page)
    _install_layer_refinements(page)
    _install_zoom_tools(page)
    _add_canvas_meta(page)
    page._v177_installed = True
    QTimer.singleShot(520, lambda ref=weakref.ref(page): _apply_theme_from_ref(ref))
    page.status_label.setText("Central Studio V177: biblioteca visual, camadas com contexto e navegação de zoom refinada.")


def _apply_theme_from_ref(page_ref) -> None:
    page = page_ref()
    if page is not None:
        _apply_theme(page)


def install_art_studio_v177() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _wrap_skin()
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v177_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v177(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v177(page)

    MainWindow.__init__ = init_with_v177
    MainWindow._v177_integration_installed = True
    _INSTALLED = True
