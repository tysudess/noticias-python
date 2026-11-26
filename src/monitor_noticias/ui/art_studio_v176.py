from __future__ import annotations

"""V176 — visão geral multipágina e inspetor contextual do Central Studio.

A grade de páginas cria prévias em cenas temporárias, sem trocar a cena ativa.
O inspetor resume e edita propriedades por tipo, reutilizando os mecanismos
atuais de histórico, salvamento, seleção e formato .centralart.
"""

import base64
import logging
import weakref

from PySide6.QtCore import QMimeData, QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QDrag, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QApplication,
    QDialog,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.art_studio_page import CANVAS_BG_KEY, ITEM_KIND_KEY, ITEM_NAME_KEY
from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v146 import FRAME_CHILD_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.art_studio_v154 import _schedule_history
from monitor_noticias.ui.art_studio_transform_engine_v172 import selected_roots
from monitor_noticias.ui.art_studio_workspace_engine_v176 import (
    page_grid_columns,
    page_preview_size,
    selection_summary,
)

log = logging.getLogger(__name__)
_INSTALLED = False


def _palette(theme: str) -> dict[str, str]:
    if theme == "escuro":
        return {
            "stage": "#0D151E", "panel": "#172532", "panel_alt": "#1D2D3B",
            "border": "#314556", "text": "#EAF1F5", "muted": "#9AABB8",
            "accent": "#41B8B3", "accent_text": "#10252B", "gold": "#D1AD67",
            "hover": "#273D4D", "danger": "#C65B66", "selected": "#244B52",
        }
    return {
        "stage": "#E9EEF2", "panel": "#FFFFFF", "panel_alt": "#F5F7F9",
        "border": "#D8E1E8", "text": "#203748", "muted": "#718493",
        "accent": "#167E83", "accent_text": "#FFFFFF", "gold": "#B28A45",
        "hover": "#EAF2F4", "danger": "#B64C58", "selected": "#E3F0F0",
    }


def _visual_stylesheet(theme: str) -> str:
    c = _palette(theme)
    return f"""
    QWidget#artStudioPage {{ background:{c['stage']}; color:{c['text']}; font-family:'Segoe UI'; }}
    QFrame#artStudioToolbar {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:11px; }}
    QFrame#artStudioPanel {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:11px; }}
    QFrame#artStudioWorkspace {{ background:{c['stage']}; border:1px solid {c['border']}; border-radius:13px; }}
    QGraphicsView#artCanvasView {{ background:{c['stage']}; border:0; outline:0; }}
    QLabel#artPanelTitle {{ color:{c['muted']}; border:0; border-bottom:1px solid {c['border']}; padding:4px 2px 8px; font-size:9px; font-weight:900; letter-spacing:1.1px; }}
    QLabel#artStudioSectionHeading {{ color:{c['text']}; font-size:10px; font-weight:900; letter-spacing:.45px; }}
    QLabel#artStudioSectionHint {{ color:{c['muted']}; font-size:9px; }}
    QTabWidget#artStudioElementsTabs::pane, QTabWidget#artStudioInspectorTabs::pane {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:8px; top:-1px; }}
    QTabBar::tab {{ background:{c['panel_alt']}; color:{c['muted']}; border:1px solid transparent; border-radius:6px; padding:6px 8px; margin:1px; min-height:22px; font-size:9px; font-weight:800; }}
    QTabBar::tab:selected {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; border-bottom:2px solid {c['accent']}; }}
    QTabBar::tab:hover {{ background:{c['hover']}; color:{c['text']}; }}
    QPushButton {{ background:{c['panel_alt']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:7px; min-height:29px; padding:4px 9px; font-size:9px; font-weight:750; }}
    QPushButton:hover {{ background:{c['hover']}; border-color:{c['accent']}; }}
    QPushButton[secondary="true"] {{ background:{c['panel_alt']}; color:{c['text']}; border:1px solid {c['border']}; }}
    QPushButton[gold="true"] {{ background:{c['accent']}; color:{c['accent_text']}; border:1px solid {c['accent']}; font-weight:900; }}
    QPushButton[danger="true"] {{ color:{c['danger']}; border-color:{c['border']}; background:{c['panel']}; }}
    QToolButton#artStudioPanelToggleV175 {{ background:{c['panel_alt']}; color:{c['muted']}; border:1px solid {c['border']}; border-radius:7px; padding:5px 8px; font-size:9px; font-weight:850; }}
    QToolButton#artStudioPanelToggleV175:checked {{ background:{c['selected']}; color:{c['accent']}; border-color:{c['accent']}; }}
    QToolButton#artStudioContextActionV175 {{ color:{c['text']}; }}
    QFrame#artStudioPageCardV176 {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:11px; }}
    QFrame#artStudioPageCardV176[active="true"] {{ border:2px solid {c['accent']}; background:{c['selected']}; }}
    QFrame#artStudioPageCardV176[dropTarget="true"] {{ border:2px dashed {c['accent']}; background:{c['selected']}; }}
    QLabel#artStudioPageTitleV176 {{ color:{c['text']}; font-size:10px; font-weight:850; }}
    QLabel#artStudioPageMetaV176 {{ color:{c['muted']}; font-size:8px; }}
    QLabel#artStudioPagePreviewV176 {{ background:{c['stage']}; border:1px solid {c['border']}; border-radius:7px; }}
    QFrame#artStudioSummaryCardV176 {{ background:{c['panel_alt']}; border:1px solid {c['border']}; border-radius:9px; }}
    QLabel#artStudioSummaryValueV176 {{ color:{c['text']}; font-size:10px; font-weight:800; }}
    QLabel#artStudioSummaryCaptionV176 {{ color:{c['muted']}; font-size:8px; font-weight:750; }}
    QLineEdit#artStudioObjectNameV176 {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:7px; padding:7px 8px; min-height:25px; }}
    QLineEdit#artStudioObjectNameV176:focus {{ border:1px solid {c['accent']}; }}
    QScrollBar:vertical {{ background:transparent; width:7px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{c['border']}; border-radius:3px; min-height:25px; }}
    """


def _theme_name(page) -> str:
    try:
        from monitor_noticias.ui import art_studio_v161
        return art_studio_v161._theme_id(page)
    except Exception:
        return "escuro" if page.palette().color(QPalette.ColorRole.Window).lightness() < 128 else "claro"


def _wrap_theme_stylesheet() -> None:
    from monitor_noticias.ui import art_studio_v161
    if getattr(art_studio_v161, "_v176_skin_wrapped", False):
        return
    original = art_studio_v161._skin_stylesheet

    def stylesheet_with_v176(theme: str) -> str:
        return original(theme) + _visual_stylesheet(theme)

    art_studio_v161._skin_stylesheet = stylesheet_with_v176
    art_studio_v161._v176_skin_wrapped = True


def _apply_theme(page) -> None:
    try:
        from monitor_noticias.ui import art_studio_v161
        page.setStyleSheet(art_studio_v161._skin_stylesheet(_theme_name(page)))
    except Exception:
        page.setStyleSheet(_visual_stylesheet(_theme_name(page)))


def _selection(page) -> list:
    try:
        selected = [
            item for item in page.scene.selectedItems()
            if not item.data(FRAME_CHILD_KEY) and item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
        ]
    except RuntimeError:
        return []
    return selected_roots(selected, lambda item: item.parentItem())


def _kind(item) -> str:
    if isinstance(item, QGraphicsTextItem):
        return "Texto"
    if isinstance(item, QGraphicsPixmapItem):
        return "Imagem"
    if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
        return "Forma"
    if isinstance(item, QGraphicsItemGroup):
        return "Grupo"
    return "Objeto"


def _page_color(page, data: dict) -> QColor:
    canvas = data.get("canvas") or {}
    config = data.get("v150_background") or {}
    value = config.get("color", canvas.get("background", "#FFFFFFFF"))
    color = QColor(str(value))
    return color if color.isValid() else QColor("#FFFFFF")


def _render_page_preview(page, entry: dict, size: QSize = QSize(232, 142)) -> QPixmap:
    """Renderiza uma página serializada em cena auxiliar, sem tocar na cena ativa."""
    data = entry.get("data") if isinstance(entry, dict) else None
    if not isinstance(data, dict):
        raise ValueError("Dados da página inválidos.")
    canvas = data.get("canvas") or {}
    width = max(64, min(5000, int(canvas.get("width", 1080))))
    height = max(64, min(5000, int(canvas.get("height", 1080))))
    target_w, target_h = page_preview_size(width, height, max_width=size.width(), max_height=size.height())
    pixmap = QPixmap(size)
    colors = _palette(_theme_name(page))
    pixmap.fill(QColor(colors["stage"]))

    scene = QGraphicsScene()
    scene.setSceneRect(QRectF(0, 0, width, height))
    background = QGraphicsRectItem(0, 0, width, height)
    background.setBrush(_page_color(page, data))
    background.setPen(QPen(Qt.PenStyle.NoPen))
    background.setZValue(-100000)
    scene.addItem(background)

    background_config = data.get("v150_background") or {}
    mode = str(background_config.get("mode", "solid"))
    try:
        if mode == "gradient":
            from monitor_noticias.ui.art_studio_v150 import _gradient_brush
            background.setBrush(_gradient_brush(width, height, background_config))
        elif mode == "image":
            encoded = str(background_config.get("image_png_base64", ""))
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 20 * 1024 * 1024:
                raise ValueError("Imagem de fundo muito grande para a prévia.")
            bg_pixmap = QPixmap()
            if not bg_pixmap.loadFromData(raw, "PNG"):
                raise ValueError("Imagem de fundo inválida.")
            scaled = bg_pixmap.scaled(
                QSize(width, height), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            bg_item = QGraphicsPixmapItem(scaled)
            bg_item.setPos((width - scaled.width()) / 2, (height - scaled.height()) / 2)
            bg_item.setZValue(-99999)
            bg_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            bg_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            scene.addItem(bg_item)
    except Exception:
        log.exception("Não foi possível montar o fundo da miniatura da página")

    items = data.get("items") or []
    if not isinstance(items, list) or len(items) > 500:
        raise ValueError("A página ultrapassa o limite de objetos permitido para prévia.")
    for item_data in items:
        if not isinstance(item_data, dict):
            continue
        try:
            item = page._build_item_from_data(item_data)
            item.setSelected(False)
            scene.addItem(item)
        except Exception:
            log.exception("Uma camada não pôde ser exibida na prévia da página")

    result = QPixmap(size)
    result.fill(QColor(colors["stage"]))
    painter = QPainter(result)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.SmoothPixmapTransform
        | QPainter.RenderHint.TextAntialiasing
    )
    target = QRectF((size.width() - target_w) / 2, (size.height() - target_h) / 2, target_w, target_h)
    scene.render(painter, target, QRectF(0, 0, width, height), Qt.AspectRatioMode.KeepAspectRatio)
    painter.setPen(QPen(QColor(colors["border"]), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(target.adjusted(-0.5, -0.5, 0.5, 0.5), 4, 4)
    painter.end()
    scene.clear()
    return result


class _PageCard(QFrame):
    """Cartão que recebe páginas arrastadas para reorganizar o documento."""

    def __init__(self, index: int, move_callback, parent=None):
        super().__init__(parent)
        self.index = int(index)
        self._move_callback = move_callback
        self.setAcceptDrops(True)
        self.setProperty("dropTarget", False)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        if text.startswith("central-studio-page:"):
            self.setProperty("dropTarget", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        if text.startswith("central-studio-page:"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.setProperty("dropTarget", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API
        text = event.mimeData().text() if event.mimeData().hasText() else ""
        self.setProperty("dropTarget", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if text.startswith("central-studio-page:"):
            try:
                source = int(text.rsplit(":", 1)[1])
            except (TypeError, ValueError):
                event.ignore()
                return
            if source != self.index:
                self._move_callback(source, self.index)
            event.acceptProposedAction()
            return
        event.ignore()


class _PageDragHandle(QToolButton):
    """Alça explícita de arraste para não conflitar com os botões do cartão."""

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._index = int(index)
        self.setObjectName("artStudioPageDragHandleV176")
        self._press_position: QPoint | None = None
        self.setText("⠿")
        self.setToolTip("Arraste para reorganizar esta página")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMinimumSize(25, 25)
        self.setMaximumSize(28, 28)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        if (
            self._press_position is None
            or not (event.buttons() & Qt.MouseButton.LeftButton)
            or (event.position().toPoint() - self._press_position).manhattanLength() < QApplication.startDragDistance()
        ):
            super().mouseMoveEvent(event)
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"central-studio-page:{self._index}")
        drag.setMimeData(mime)
        card = self.parentWidget()
        if card is not None:
            preview = card.grab()
            if not preview.isNull():
                drag.setPixmap(preview.scaled(180, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        drag.exec(Qt.DropAction.MoveAction)
        self._press_position = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._press_position = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class _PageOverviewDialog(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self._page_ref = weakref.ref(page)
        self._render_queue: list[tuple[int, QLabel]] = []
        self._cards: list[QFrame] = []
        self.setWindowTitle("Visão geral das páginas · Central Studio")
        self.setMinimumSize(780, 540)
        self.resize(1040, 700)
        self.setModal(True)
        colors = _palette(_theme_name(page))
        self.setStyleSheet(
            f"QDialog {{ background:{colors['stage']}; color:{colors['text']}; }}"
            + _visual_stylesheet(_theme_name(page))
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)
        header = QHBoxLayout()
        text_block = QVBoxLayout()
        text_block.setSpacing(2)
        title = QLabel("Páginas do projeto", self)
        title.setStyleSheet(f"font-size:16px;font-weight:900;color:{colors['text']};")
        self.subtitle = QLabel("Organize, duplique, renomeie e revise cada página.", self)
        self.subtitle.setStyleSheet(f"font-size:9px;color:{colors['muted']};")
        text_block.addWidget(title)
        text_block.addWidget(self.subtitle)
        header.addLayout(text_block, 1)
        self.add_button = QPushButton("+ Nova página", self)
        self.add_button.setProperty("gold", True)
        self.add_button.clicked.connect(self._add_page)
        header.addWidget(self.add_button)
        close = QPushButton("Fechar", self)
        close.clicked.connect(self.accept)
        header.addWidget(close)
        root.addLayout(header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget(scroll)
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(2, 2, 8, 8)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)
        scroll.setWidget(self.container)
        root.addWidget(scroll, 1)

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(25)
        self._render_timer.timeout.connect(self._render_next)
        self._build_cards()

    def _clear_cards(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        self._render_queue = []

    def _build_cards(self) -> None:
        page = self._page_ref()
        if page is None:
            return
        self._clear_cards()
        try:
            from monitor_noticias.ui.art_studio_v150 import _capture_active_page
            _capture_active_page(page)
        except Exception:
            log.exception("Não foi possível atualizar o estado da página ativa antes da prévia")
        entries = list(getattr(page, "_v150_pages", []) or [])
        active = int(getattr(page, "_v150_active_index", 0))
        self.subtitle.setText(f"{len(entries)} página(s) · página atual {active + 1}. Arraste pela alça ⠿ ou use as setas para reorganizar.")
        width = max(780, self.width() - 50)
        columns = page_grid_columns(width, min_card_width=244, gap=14, max_columns=4)
        for index, entry in enumerate(entries):
            card = _PageCard(index, self._move_page, self.container)
            card.setObjectName("artStudioPageCardV176")
            card.setProperty("active", index == active)
            card.setMinimumWidth(220)
            card.setMaximumWidth(360)
            box = QVBoxLayout(card)
            box.setContentsMargins(10, 10, 10, 10)
            box.setSpacing(7)
            preview = QLabel("Preparando prévia…", card)
            preview.setObjectName("artStudioPagePreviewV176")
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setMinimumSize(210, 132)
            preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            box.addWidget(preview)
            row = QHBoxLayout()
            name = QLabel(str(entry.get("name") or f"Página {index + 1}"), card)
            name.setObjectName("artStudioPageTitleV176")
            name.setWordWrap(True)
            row.addWidget(name, 1)
            page_index = QLabel(f"{index + 1:02d}", card)
            page_index.setStyleSheet(f"color:{_palette(_theme_name(page))['muted']};font-size:9px;font-weight:900;")
            row.addWidget(page_index)
            row.addWidget(_PageDragHandle(index, card))
            box.addLayout(row)
            data = entry.get("data") or {}
            canvas = data.get("canvas") or {}
            meta = QLabel(f"{canvas.get('width',1080)} × {canvas.get('height',1080)} px", card)
            meta.setObjectName("artStudioPageMetaV176")
            box.addWidget(meta)
            actions = QHBoxLayout()
            open_button = QPushButton("Abrir", card)
            open_button.setProperty("gold", True)
            open_button.clicked.connect(lambda _checked=False, idx=index: self._open_page(idx))
            duplicate_button = QPushButton("Duplicar", card)
            duplicate_button.clicked.connect(lambda _checked=False, idx=index: self._duplicate_page(idx))
            more_button = QToolButton(card)
            more_button.setText("•••")
            more_button.setToolTip("Mais ações da página")
            menu = QMenu(more_button)
            action_rename = menu.addAction("Renomear")
            action_delete = menu.addAction("Excluir")
            action_rename.triggered.connect(lambda _checked=False, idx=index: self._rename_page(idx))
            action_delete.triggered.connect(lambda _checked=False, idx=index: self._delete_page(idx))
            more_button.setMenu(menu)
            more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            actions.addWidget(open_button, 1)
            actions.addWidget(duplicate_button)
            actions.addWidget(more_button)
            box.addLayout(actions)
            order = QHBoxLayout()
            up = QToolButton(card)
            up.setText("↑")
            up.setToolTip("Mover página para a esquerda")
            up.setEnabled(index > 0)
            up.clicked.connect(lambda _checked=False, idx=index: self._move_page(idx, idx - 1))
            down = QToolButton(card)
            down.setText("↓")
            down.setToolTip("Mover página para a direita")
            down.setEnabled(index < len(entries) - 1)
            down.clicked.connect(lambda _checked=False, idx=index: self._move_page(idx, idx + 1))
            order.addWidget(QLabel("Ordem", card))
            order.addStretch(1)
            order.addWidget(up)
            order.addWidget(down)
            box.addLayout(order)
            self.grid.addWidget(card, index // columns, index % columns)
            self._cards.append(card)
            self._render_queue.append((index, preview))
        self._render_timer.start()

    def _render_next(self) -> None:
        page = self._page_ref()
        if page is None or not self._render_queue:
            return
        index, label = self._render_queue.pop(0)
        entries = getattr(page, "_v150_pages", [])
        if 0 <= index < len(entries):
            try:
                image = _render_page_preview(page, entries[index])
                label.setPixmap(image)
                label.setText("")
            except Exception as exc:
                log.exception("Falha ao gerar miniatura da página %s", index + 1)
                label.setText("Prévia indisponível")
                label.setToolTip(str(exc))
        if self._render_queue:
            self._render_timer.start()

    def _open_page(self, index: int) -> None:
        page = self._page_ref()
        if page is None:
            return
        self._activate(index)
        self.accept()

    def _activate(self, index: int) -> None:
        page = self._page_ref()
        if page is None or not 0 <= index < len(page._v150_pages):
            return
        if index != page._v150_active_index:
            from monitor_noticias.ui.art_studio_v150 import _switch_page
            _switch_page(page, index)
            page.v150_tab_bar.setCurrentIndex(index)

    def _duplicate_page(self, index: int) -> None:
        page = self._page_ref()
        if page is None:
            return
        self._activate(index)
        from monitor_noticias.ui.art_studio_v150 import _duplicate_page
        _duplicate_page(page)
        self._build_cards()

    def _add_page(self) -> None:
        page = self._page_ref()
        if page is None:
            return
        from monitor_noticias.ui.art_studio_v150 import _add_page
        _add_page(page)
        self._build_cards()

    def _rename_page(self, index: int) -> None:
        page = self._page_ref()
        if page is None or not 0 <= index < len(page._v150_pages):
            return
        from PySide6.QtWidgets import QInputDialog
        old = str(page._v150_pages[index].get("name") or f"Página {index + 1}")
        value, accepted = QInputDialog.getText(self, "Renomear página", "Nome da página:", text=old)
        if not accepted or not value.strip():
            return
        page._v150_pages[index]["name"] = value.strip()[:80]
        from monitor_noticias.ui.art_studio_v150 import _update_tabs
        _update_tabs(page)
        page._v150_update_page_chrome()
        self._build_cards()

    def _delete_page(self, index: int) -> None:
        page = self._page_ref()
        if page is None:
            return
        from monitor_noticias.ui.art_studio_v150 import _delete_page
        _delete_page(page, index)
        self._build_cards()

    def _move_page(self, source: int, target: int) -> None:
        page = self._page_ref()
        if page is None or not (0 <= source < len(page._v150_pages) and 0 <= target < len(page._v150_pages)):
            return
        from monitor_noticias.ui.art_studio_v150 import _tab_moved
        _tab_moved(page, source, target)
        self._build_cards()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self._build_cards)


def _install_page_overview(page) -> None:
    if getattr(page, "_v176_page_overview_installed", False):
        return
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return
    button = QToolButton(toolbar)
    button.setText("▦")
    button.setAccessibleName("Visão geral das páginas")
    button.setToolTip("Abrir visão geral com miniaturas de todas as páginas · Ctrl+Shift+P")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(30)
    button.setMaximumHeight(33)
    button.setObjectName("artStudioPanelToggleV175")
    button.clicked.connect(lambda: _PageOverviewDialog(page).exec())
    pages_toggle = getattr(page, "v174_pages_toggle", None)
    index = layout.indexOf(pages_toggle) if pages_toggle is not None else -1
    if index >= 0:
        layout.insertWidget(index + 1, button)
    else:
        layout.insertWidget(max(0, layout.count() - 2), button)
    page.v176_page_grid_button = button

    action = QAction("Visão geral das páginas", page)
    action.setShortcut(QKeySequence("Ctrl+Shift+P"))
    action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    action.triggered.connect(lambda _checked=False: _PageOverviewDialog(page).exec())
    page.addAction(action)
    page._v176_page_overview_action = action
    page._v176_page_overview_installed = True


def _install_inspector_summary(page) -> None:
    if getattr(page, "_v176_summary_installed", False):
        return
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    tab = QWidget(tabs)
    tab.setObjectName("artStudioSummaryTabV176")
    outer = QVBoxLayout(tab)
    outer.setContentsMargins(9, 9, 9, 10)
    outer.setSpacing(10)

    title = QLabel("RESUMO DA SELEÇÃO", tab)
    title.setObjectName("artStudioSectionHeading")
    hint = QLabel("Informações e ações rápidas do objeto selecionado.", tab)
    hint.setObjectName("artStudioSectionHint")
    hint.setWordWrap(True)
    outer.addWidget(title)
    outer.addWidget(hint)

    card = QFrame(tab)
    card.setObjectName("artStudioSummaryCardV176")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(11, 11, 11, 11)
    card_layout.setSpacing(7)
    page.v176_selection_kind = QLabel("Nenhum objeto selecionado", card)
    page.v176_selection_kind.setObjectName("artStudioSummaryValueV176")
    page.v176_selection_kind.setWordWrap(True)
    card_layout.addWidget(page.v176_selection_kind)
    name_label = QLabel("Nome da camada", card)
    name_label.setObjectName("artStudioSummaryCaptionV176")
    card_layout.addWidget(name_label)
    page.v176_object_name = QLineEdit(card)
    page.v176_object_name.setObjectName("artStudioObjectNameV176")
    page.v176_object_name.setPlaceholderText("Nome do objeto")
    card_layout.addWidget(page.v176_object_name)
    page.v176_geometry = QLabel("Posição e dimensões aparecerão aqui.", card)
    page.v176_geometry.setObjectName("artStudioSectionHint")
    page.v176_geometry.setWordWrap(True)
    card_layout.addWidget(page.v176_geometry)
    page.v176_state = QLabel("—", card)
    page.v176_state.setObjectName("artStudioSectionHint")
    card_layout.addWidget(page.v176_state)
    outer.addWidget(card)

    page.v176_lock_button = QPushButton("Bloquear seleção", tab)
    page.v176_lock_button.setProperty("secondary", True)
    page.v176_transform_button = QPushButton("Abrir transformação", tab)
    page.v176_transform_button.setProperty("gold", True)
    page.v176_duplicate_button = QPushButton("Duplicar", tab)
    page.v176_delete_button = QPushButton("Excluir", tab)
    page.v176_delete_button.setProperty("danger", True)
    actions = QHBoxLayout()
    actions.addWidget(page.v176_lock_button)
    actions.addWidget(page.v176_duplicate_button)
    outer.addLayout(actions)
    outer.addWidget(page.v176_transform_button)
    outer.addWidget(page.v176_delete_button)
    outer.addStretch(1)
    tabs.addTab(tab, "Resumo")
    page.v176_summary_tab = tab

    page.v176_object_name.editingFinished.connect(lambda: _rename_selected(page))
    page.v176_lock_button.clicked.connect(lambda: _toggle_selection_lock(page))
    page.v176_transform_button.clicked.connect(lambda: _open_transform_tab(page))
    page.v176_duplicate_button.clicked.connect(lambda: _click_page_action(page, "duplicate_button"))
    page.v176_delete_button.clicked.connect(lambda: _click_page_action(page, "delete_button"))
    page.scene.selectionChanged.connect(lambda: _sync_summary(page))
    layers = getattr(page, "layers", None)
    if layers is not None:
        layers.itemSelectionChanged.connect(lambda: _sync_summary(page))
    page._v176_summary_installed = True
    _sync_summary(page)


def _rename_selected(page) -> None:
    items = _selection(page)
    if len(items) != 1:
        return
    item = items[0]
    value = page.v176_object_name.text().strip()[:100]
    if not value:
        page.v176_object_name.setText(str(item.data(ITEM_NAME_KEY) or _kind(item)))
        return
    item.setData(ITEM_NAME_KEY, value)
    page._refresh_layers(select_item=item)
    _schedule_history(page)
    _schedule_autosave(page)
    page.status_label.setText(f"Camada renomeada para '{value}'.")
    _sync_summary(page)


def _toggle_selection_lock(page) -> None:
    items = _selection(page)
    if not items:
        return
    unlock = all(bool(item.data(LOCKED_KEY)) for item in items)
    locked = not unlock
    for item in items:
        try:
            item.setData(LOCKED_KEY, locked)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)
        except RuntimeError:
            continue
    page._refresh_layers(select_item=items[0] if len(items) == 1 else None)
    page._update_selection_controls(items[0] if len(items) == 1 else None)
    callback = getattr(page, "_v145_update_v145_controls", None)
    if callable(callback):
        callback()
    _schedule_history(page)
    _schedule_autosave(page)
    page.scene.update()
    page.status_label.setText("Seleção desbloqueada." if unlock else "Seleção bloqueada.")
    _sync_summary(page)


def _click_page_action(page, name: str) -> None:
    button = getattr(page, name, None)
    if isinstance(button, QPushButton) and button.isEnabled():
        button.click()
    QTimer.singleShot(0, lambda: _sync_summary(page))


def _open_transform_tab(page) -> None:
    tabs = getattr(page, "_v161_inspector_tabs", None)
    if not isinstance(tabs, QTabWidget):
        return
    target = page.findChild(QWidget, "artStudioTransformTabV172")
    if target is not None:
        _set_panel_visible(page, "right", True)
        index = tabs.indexOf(target)
        if index >= 0:
            tabs.setCurrentIndex(index)


def _set_panel_visible(page, side: str, visible: bool) -> None:
    from monitor_noticias.ui.art_studio_v175 import _set_panel_visible as set_visible
    set_visible(page, side, visible)


def _sync_summary(page) -> None:
    items = _selection(page)
    count = len(items)
    page.v176_selection_kind.setText("Nenhum objeto selecionado" if not count else f"{count} {('objeto selecionado' if count == 1 else 'objetos selecionados')}")
    single = items[0] if count == 1 else None
    page.v176_object_name.blockSignals(True)
    page.v176_object_name.setEnabled(single is not None and not bool(single.data(LOCKED_KEY)))
    page.v176_object_name.setText(str(single.data(ITEM_NAME_KEY) or _kind(single)) if single is not None else "")
    page.v176_object_name.blockSignals(False)
    page.v176_transform_button.setEnabled(bool(count))
    page.v176_lock_button.setEnabled(bool(count))
    page.v176_duplicate_button.setEnabled(bool(count) and all(not bool(item.data(LOCKED_KEY)) for item in items))
    page.v176_delete_button.setEnabled(bool(count) and all(not bool(item.data(LOCKED_KEY)) for item in items))
    if not count:
        page.v176_geometry.setText("Selecione um objeto no canvas ou no painel de camadas.")
        page.v176_state.setText("—")
        page.v176_lock_button.setText("Bloquear seleção")
        return
    rects = [item.sceneBoundingRect() for item in items]
    summary = selection_summary(
        [(rect.left(), rect.top(), rect.width(), rect.height()) for rect in rects],
        rotation=float(single.rotation()) if single is not None else None,
        opacity=float(single.opacity()) if single is not None else None,
    )
    page.v176_geometry.setText(
        f"X  {summary['x']:.1f} px     Y  {summary['y']:.1f} px\n"
        f"Largura  {summary['width']:.1f} px\nAltura  {summary['height']:.1f} px"
        + (f"\nRotação  {summary['rotation']:.1f}°     Opacidade  {summary['opacity'] * 100:.0f}%" if single is not None else "")
    )
    kinds = sorted({_kind(item) for item in items})
    page.v176_selection_kind.setText(kinds[0] if len(kinds) == 1 else "Seleção mista")
    locked_count = sum(bool(item.data(LOCKED_KEY)) for item in items)
    page.v176_state.setText(f"{locked_count} bloqueada(s) · {count - locked_count} editável(is)")
    page.v176_lock_button.setText("Desbloquear seleção" if locked_count == count else "Bloquear seleção")


def _install_visual_refinements(page) -> None:
    _apply_theme(page)
    toolbar = page.findChild(QFrame, "artStudioToolbar")
    if toolbar is not None:
        toolbar.setMinimumHeight(48)
        toolbar.setMaximumHeight(54)
        layout = toolbar.layout()
        if layout is not None:
            layout.setContentsMargins(8, 5, 8, 5)
            layout.setSpacing(5)
    for button in page.findChildren(QPushButton):
        if button.objectName() in {"artStudioApplyTransformV172", "artStudioDeleteLayersV170"}:
            button.setMinimumHeight(30)
            button.setMaximumHeight(34)
    workspace = page.findChild(QFrame, "artStudioWorkspace")
    if workspace is not None:
        workspace.setContentsMargins(5, 5, 5, 5)

    # O tema V176 remove o dourado constante dos painéis do editor; a cor passa
    # a marcar ações e estados, não a contornar cada cartão.
    for heading in page.findChildren(QLabel, "artPanelTitle"):
        heading.setStyleSheet("border-bottom:1px solid palette(mid); padding-bottom:7px;")


def enhance_art_studio_page_v176(page) -> None:
    if getattr(page, "_v176_installed", False):
        return
    _install_visual_refinements(page)
    _install_page_overview(page)
    _install_inspector_summary(page)
    page._v176_installed = True
    page.status_label.setText("Central Studio V176: visão geral de páginas, resumo contextual e identidade visual refinada.")


def install_art_studio_v176() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _wrap_theme_stylesheet()
    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v176_integration_installed", False):
        _INSTALLED = True
        return
    original_init = MainWindow.__init__

    def init_with_v176(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v176(page)
            page_ref = weakref.ref(page)
            QTimer.singleShot(520, lambda ref=page_ref: _apply_theme_from_ref(ref))

    MainWindow.__init__ = init_with_v176
    MainWindow._v176_integration_installed = True
    _INSTALLED = True


def _apply_theme_from_ref(page_ref) -> None:
    page = page_ref()
    if page is not None:
        _apply_theme(page)
