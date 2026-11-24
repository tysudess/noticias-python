from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from PySide6.QtCore import QBuffer, QIODevice, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
)
from PIL import Image as PILImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QFontDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

PROJECT_FORMAT = "central-inteligente-art-studio"
PROJECT_VERSION = 1
CANVAS_BG_KEY = "canvas-background"
ITEM_KIND_KEY = 0
ITEM_NAME_KEY = 1

PRESETS: tuple[tuple[str, int, int], ...] = (
    ("Post quadrado · 1080 × 1080", 1080, 1080),
    ("Story / Reels · 1080 × 1920", 1080, 1920),
    ("Paisagem · 1920 × 1080", 1920, 1080),
    ("Capa YouTube · 1280 × 720", 1280, 720),
    ("A4 retrato · 2480 × 3508", 2480, 3508),
    ("Personalizado", 1080, 1080),
)


class ArtCanvasView(QGraphicsView):
    """Canvas com zoom por roda do mouse e ajuste automático à área de trabalho."""

    zoomChanged = Signal(int)

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setObjectName("artCanvasView")
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#DCE3EA"))
        self.setMinimumSize(420, 360)

    def _publish_zoom(self) -> None:
        self.zoomChanged.emit(max(1, int(round(self.transform().m11() * 100))))

    def fit_canvas(self) -> None:
        rect = self.scene().sceneRect()
        if rect.width() > 0 and rect.height() > 0:
            self.resetTransform()
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self._publish_zoom()

    def zoom_by(self, factor: float) -> None:
        current = max(0.001, self.transform().m11())
        target = max(0.05, min(8.0, current * float(factor)))
        self.scale(target / current, target / current)
        self._publish_zoom()

    def actual_size(self) -> None:
        self.resetTransform()
        self.centerOn(self.scene().sceneRect().center())
        self._publish_zoom()

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            steps = event.angleDelta().y() / 120.0
            if steps:
                self.zoom_by(1.15 ** steps)
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self.fit_canvas)


class ArtStudioPage(QWidget):
    """Editor gráfico local, sem serviços externos ou dependências adicionais."""

    project_changed = Signal(str)

    def __init__(self, projects_dir: Path | str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("artStudioPage")
        self.projects_dir = Path(projects_dir).expanduser()
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.current_file: Path | None = None
        self._loading = False
        self._layer_objects: dict[int, QGraphicsItem] = {}
        self._width = 1080
        self._height = 1080
        self._canvas_color = QColor("#FFFFFF")

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, self._width, self._height))
        self.scene.setBackgroundBrush(QColor("#DCE3EA"))
        self._canvas_item = QGraphicsRectItem(0, 0, self._width, self._height)
        self._canvas_item.setBrush(QBrush(self._canvas_color))
        self._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        self._canvas_item.setZValue(-100000)
        self._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        self._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        self.scene.addItem(self._canvas_item)

        self._build_ui()
        self.scene.selectionChanged.connect(self._selection_changed)
        self._refresh_layers()
        self.view.fit_canvas()

        delete_action = QAction("Excluir objeto", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected)
        self.addAction(delete_action)

        save_action = QAction("Salvar projeto", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        self.addAction(save_action)

        open_action = QAction("Abrir projeto", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        self.addAction(open_action)

        zoom_in_action = QAction("Aumentar zoom", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
        zoom_in_action.triggered.connect(lambda: self.view.zoom_by(1.15))
        self.addAction(zoom_in_action)
        zoom_out_action = QAction("Diminuir zoom", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(lambda: self.view.zoom_by(1 / 1.15))
        self.addAction(zoom_out_action)
        fit_action = QAction("Ajustar canvas", self)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_action.triggered.connect(self.view_fit)
        self.addAction(fit_action)

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(10)

        top = QFrame()
        top.setObjectName("artStudioToolbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(7)

        self.new_button = self._button("Novo", secondary=True)
        self.open_button = self._button("Abrir projeto", secondary=True)
        self.save_button = self._button("Salvar projeto")
        self.export_button = self._button("Exportar arte")
        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.export_button.clicked.connect(self.export_art)
        for button in (self.new_button, self.open_button, self.save_button, self.export_button):
            top_layout.addWidget(button)
        top_layout.addStretch(1)
        self.project_label = QLabel("Projeto sem título")
        self.project_label.setObjectName("artProjectName")
        top_layout.addWidget(self.project_label)
        root.addWidget(top)

        workspace = QHBoxLayout()
        workspace.setSpacing(10)
        root.addLayout(workspace, 1)

        left = self._panel("ELEMENTOS")
        left.setFixedWidth(184)
        left_layout = left.layout()
        self.add_image_button = self._button("＋  Imagem", secondary=True)
        self.add_text_button = self._button("T  Texto", secondary=True)
        self.add_rect_button = self._button("▭  Retângulo", secondary=True)
        self.add_ellipse_button = self._button("◯  Círculo", secondary=True)
        self.background_button = self._button("Fundo da arte", secondary=True)
        self.templates_button = self._button("Modelos rápidos", secondary=True)
        self.add_image_button.clicked.connect(self.add_image)
        self.add_text_button.clicked.connect(self.add_text)
        self.add_rect_button.clicked.connect(lambda: self.add_shape("rect"))
        self.add_ellipse_button.clicked.connect(lambda: self.add_shape("ellipse"))
        self.background_button.clicked.connect(self.choose_canvas_color)
        self.templates_button.clicked.connect(self.apply_quick_template)
        for button in (
            self.add_image_button,
            self.add_text_button,
            self.add_rect_button,
            self.add_ellipse_button,
            self.background_button,
            self.templates_button,
        ):
            button.setMinimumHeight(38)
            left_layout.addWidget(button)

        left_layout.addSpacing(14)
        left_layout.addWidget(self._small_label("FORMATO DA ARTE"))
        self.preset_combo = QComboBox()
        for label, width, height in PRESETS:
            self.preset_combo.addItem(label, (width, height))
        self.preset_combo.currentIndexChanged.connect(self._preset_changed)
        left_layout.addWidget(self.preset_combo)

        dimensions = QFormLayout()
        dimensions.setContentsMargins(0, 2, 0, 2)
        dimensions.setHorizontalSpacing(6)
        dimensions.setVerticalSpacing(5)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 5000)
        self.width_spin.setValue(self._width)
        self.width_spin.setToolTip("Largura em pixels")
        self.width_spin.setMinimumWidth(0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 5000)
        self.height_spin.setValue(self._height)
        self.height_spin.setToolTip("Altura em pixels")
        self.height_spin.setMinimumWidth(0)
        dimensions.addRow("Largura (px)", self.width_spin)
        dimensions.addRow("Altura (px)", self.height_spin)
        left_layout.addLayout(dimensions)
        self.apply_size_button = self._button("Aplicar tamanho", secondary=True)
        self.apply_size_button.clicked.connect(self.apply_canvas_size)
        left_layout.addWidget(self.apply_size_button)
        left_layout.addStretch(1)
        workspace.addWidget(left)

        center = QFrame()
        center.setObjectName("artStudioWorkspace")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(6)
        canvas_header = QHBoxLayout()
        self.canvas_size_label = QLabel("1080 × 1080 px")
        self.canvas_size_label.setObjectName("muted")
        canvas_header.addWidget(self.canvas_size_label)
        canvas_header.addStretch(1)
        self.zoom_out_button = self._button("−", secondary=True)
        self.zoom_out_button.setFixedWidth(36)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_in_button = self._button("+", secondary=True)
        self.zoom_in_button.setFixedWidth(36)
        self.actual_size_button = self._button("100%", secondary=True)
        self.fit_button = self._button("Ajustar à tela", secondary=True)
        self.zoom_out_button.clicked.connect(lambda: self.view.zoom_by(1 / 1.15))
        self.zoom_in_button.clicked.connect(lambda: self.view.zoom_by(1.15))
        self.actual_size_button.clicked.connect(self.view.actual_size)
        self.fit_button.clicked.connect(self.view_fit)
        canvas_header.addWidget(self.zoom_out_button)
        canvas_header.addWidget(self.zoom_label)
        canvas_header.addWidget(self.zoom_in_button)
        canvas_header.addWidget(self.actual_size_button)
        canvas_header.addWidget(self.fit_button)
        center_layout.addLayout(canvas_header)
        self.view = ArtCanvasView(self.scene)
        self.view.zoomChanged.connect(lambda value: self.zoom_label.setText(f"{value}%"))
        center_layout.addWidget(self.view, 1)
        workspace.addWidget(center, 1)

        right = self._panel("CAMADAS E OBJETOS")
        right.setFixedWidth(260)
        right_layout = right.layout()
        self.selection_label = QLabel("Nenhum objeto selecionado")
        self.selection_label.setObjectName("muted")
        self.selection_label.setWordWrap(True)
        right_layout.addWidget(self.selection_label)
        self.layers = QListWidget()
        self.layers.setObjectName("artLayersList")
        self.layers.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layers.currentItemChanged.connect(self._layer_selected)
        right_layout.addWidget(self.layers, 1)

        transform_title = self._small_label("PROPRIEDADES DO OBJETO")
        right_layout.addWidget(transform_title)
        transform_form = QFormLayout()
        transform_form.setContentsMargins(0, 0, 0, 0)
        transform_form.setVerticalSpacing(4)
        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360.0, 360.0)
        self.rotation_spin.setDecimals(1)
        self.rotation_spin.setSingleStep(5.0)
        self.rotation_spin.setSuffix("°")
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.05, 8.0)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setSingleStep(0.10)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        transform_form.addRow("Rotação", self.rotation_spin)
        transform_form.addRow("Escala", self.scale_spin)
        transform_form.addRow("Opacidade", self.opacity_slider)
        right_layout.addLayout(transform_form)
        self.apply_transform_button = self._button("Aplicar transformações", secondary=True)
        self.apply_transform_button.clicked.connect(self.apply_selected_transform)
        right_layout.addWidget(self.apply_transform_button)

        self.edit_text_button = self._button("Editar texto", secondary=True)
        self.font_button = self._button("Fonte e estilo", secondary=True)
        self.color_button = self._button("Cor do objeto", secondary=True)
        self.center_button = self._button("Centralizar no canvas", secondary=True)
        self.duplicate_button = self._button("Duplicar", secondary=True)
        self.forward_button = self._button("Trazer para frente", secondary=True)
        self.backward_button = self._button("Enviar para trás", secondary=True)
        self.delete_button = self._button("Excluir objeto", secondary=True)
        self.delete_button.setProperty("danger", True)
        self.edit_text_button.clicked.connect(self.edit_selected_text)
        self.font_button.clicked.connect(self.change_selected_font)
        self.color_button.clicked.connect(self.change_selected_color)
        self.center_button.clicked.connect(self.center_selected)
        self.duplicate_button.clicked.connect(self.duplicate_selected)
        self.forward_button.clicked.connect(self.bring_to_front)
        self.backward_button.clicked.connect(self.send_to_back)
        self.delete_button.clicked.connect(self.delete_selected)
        for button in (
            self.edit_text_button,
            self.font_button,
            self.color_button,
            self.center_button,
            self.duplicate_button,
            self.forward_button,
            self.backward_button,
            self.delete_button,
        ):
            right_layout.addWidget(button)
        workspace.addWidget(right)

        self.status_label = QLabel(
            "Dica: selecione um objeto e arraste para posicioná-lo. Use Ctrl+S para salvar."
        )
        self.status_label.setObjectName("muted")
        root.addWidget(self.status_label)
        self._update_selection_controls(None)

    @staticmethod
    def _button(text: str, *, secondary: bool = False) -> QPushButton:
        button = QPushButton(text)
        if secondary:
            button.setProperty("secondary", True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    @staticmethod
    def _small_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("artSmallLabel")
        return label

    @staticmethod
    def _panel(title: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("artStudioPanel")
        frame.setMinimumWidth(140)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setObjectName("artPanelTitle")
        layout.addWidget(label)
        return frame

    # ------------------------------------------------------------------
    # Tela e objetos
    # ------------------------------------------------------------------
    def refresh(self, _state: Any = None) -> None:
        """Compatibilidade com o ciclo de atualização das páginas da Central."""
        return None

    def _preset_changed(self, index: int) -> None:
        value = self.preset_combo.itemData(index)
        if not value:
            return
        width, height = value
        self.width_spin.setValue(int(width))
        self.height_spin.setValue(int(height))
        if index != len(PRESETS) - 1:
            self.apply_canvas_size()

    def apply_canvas_size(self) -> None:
        width = int(self.width_spin.value())
        height = int(self.height_spin.value())
        self._width, self._height = width, height
        self.scene.setSceneRect(QRectF(0, 0, width, height))
        self._canvas_item.setRect(0, 0, width, height)
        self.canvas_size_label.setText(f"{width} × {height} px")
        self.view_fit()
        self.status_label.setText(f"Formato da arte atualizado para {width} × {height} pixels.")

    def view_fit(self) -> None:
        self.view.fit_canvas()

    def choose_canvas_color(self) -> None:
        color = QColorDialog.getColor(self._canvas_color, self, "Escolher cor do fundo")
        if not color.isValid():
            return
        self._canvas_color = color
        self._canvas_item.setBrush(QBrush(color))
        self.status_label.setText(f"Fundo alterado para {color.name()}.")

    def _make_movable(self, item: QGraphicsItem, kind: str, name: str) -> None:
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        item.setData(ITEM_KIND_KEY, kind)
        item.setData(ITEM_NAME_KEY, name)
        item.setTransformOriginPoint(item.boundingRect().center())
        max_z = max(
            (float(candidate.zValue()) for candidate in self._content_items()),
            default=0.0,
        )
        item.setZValue(max_z + 1.0)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self._refresh_layers()

    def add_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Adicionar imagem",
            str(Path.home()),
            "Imagens (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Imagem inválida", "Não foi possível abrir essa imagem.")
            return
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        factor = min(
            1.0,
            (self._width * 0.78) / max(1, pixmap.width()),
            (self._height * 0.78) / max(1, pixmap.height()),
        )
        item.setScale(factor)
        item.setPos(
            (self._width - pixmap.width() * factor) / 2,
            (self._height - pixmap.height() * factor) / 2,
        )
        item.setData(2, Path(path).name)
        self._make_movable(item, "image", Path(path).name)
        self.status_label.setText(f"Imagem adicionada: {Path(path).name}.")

    def add_text(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "Adicionar texto", "Digite o texto da arte:")
        if not ok or not text.strip():
            return
        size, size_ok = QInputDialog.getInt(
            self, "Tamanho do texto", "Tamanho da fonte (px):", 54, 8, 500, 1
        )
        if not size_ok:
            return
        color = QColorDialog.getColor(QColor("#102A43"), self, "Cor do texto")
        if not color.isValid():
            color = QColor("#102A43")
        item = QGraphicsTextItem(text.strip())
        font = QFont("Segoe UI")
        font.setPixelSize(size)
        font.setWeight(QFont.Weight.Bold)
        item.setFont(font)
        item.setDefaultTextColor(color)
        item.setTextWidth(min(self._width * 0.82, max(260.0, item.boundingRect().width())))
        rect = item.boundingRect()
        item.setPos((self._width - rect.width()) / 2, (self._height - rect.height()) / 2)
        item.setData(2, "Texto")
        self._make_movable(item, "text", text.strip().splitlines()[0][:40])
        self.status_label.setText("Texto adicionado. Arraste para posicionar e use 'Editar texto' para alterar.")

    def add_shape(self, shape: str) -> None:
        default = QColor("#0B79F7") if shape == "rect" else QColor("#E6A700")
        color = QColorDialog.getColor(default, self, "Cor da forma")
        if not color.isValid():
            return
        if shape == "ellipse":
            item: QGraphicsItem = QGraphicsEllipseItem(QRectF(0, 0, 360, 240))
            name = "Círculo"
        else:
            item = QGraphicsRectItem(QRectF(0, 0, 440, 250))
            name = "Retângulo"
        item.setBrush(QBrush(color))
        item.setPen(QPen(Qt.PenStyle.NoPen))
        shape_rect = item.rect() if isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)) else QRectF(0, 0, 440, 250)
        item.setPos((self._width - shape_rect.width()) / 2, (self._height - shape_rect.height()) / 2)
        self._make_movable(item, "shape", name)
        self.status_label.setText(f"{name} adicionado à arte.")

    def apply_quick_template(self) -> None:
        choices = ["Destaque de notícia", "Comunicado", "Convite", "Card informativo"]
        choice, accepted = QInputDialog.getItem(
            self, "Modelos rápidos", "Escolha um modelo para começar:", choices, 0, False
        )
        if not accepted or not choice:
            return
        if self._content_items():
            answer = QMessageBox.question(
                self,
                "Aplicar modelo",
                "O modelo substituirá os objetos da arte atual. Deseja continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._reset_for_template()
        if choice == "Destaque de notícia":
            self._width, self._height = 1920, 1080
            self._canvas_color = QColor("#091F33")
            self._set_template_canvas()
            self._template_rect(0, 0, 22, 1080, "#D6B66D", "Detalhe dourado")
            self._template_text("DESTAQUE DO DIA", 40, "#E4C77B", 130, 125, 1500)
            self._template_text("TÍTULO DA NOTÍCIA", 112, "#FFFFFF", 130, 320, 1640)
            self._template_text("Inclua aqui o resumo ou a chamada principal da matéria.", 52, "#C5D3DE", 134, 640, 1510, bold=False)
            self._template_text("CENTRAL INTELIGENTE DE MÍDIA", 26, "#91A8BA", 134, 960, 1200)
        elif choice == "Comunicado":
            self._width, self._height = 1080, 1080
            self._canvas_color = QColor("#F2F5F8")
            self._set_template_canvas()
            self._template_rect(0, 0, 1080, 280, "#0B263D", "Cabeçalho")
            self._template_rect(0, 280, 1080, 16, "#D6B66D", "Faixa dourada")
            self._template_text("COMUNICADO", 76, "#FFFFFF", 82, 92, 900)
            self._template_text("Título principal", 70, "#102A43", 82, 390, 900)
            self._template_text("Escreva aqui a informação que precisa ser divulgada.", 42, "#43596B", 84, 535, 900, bold=False)
            self._template_text("CENTRAL INTELIGENTE DE MÍDIA", 25, "#667C8E", 84, 980, 900)
        elif choice == "Convite":
            self._width, self._height = 1080, 1920
            self._canvas_color = QColor("#F8F1E4")
            self._set_template_canvas()
            self._template_rect(0, 0, 1080, 460, "#102A43", "Faixa superior")
            self._template_rect(0, 1460, 1080, 460, "#102A43", "Faixa inferior")
            self._template_text("VOCÊ ESTÁ CONVIDADO", 58, "#E4C77B", 85, 180, 910)
            self._template_text("NOME DO EVENTO", 90, "#FFFFFF", 80, 330, 930)
            self._template_text("Data • Horário • Local", 54, "#102A43", 90, 760, 900)
            self._template_text("Confirme sua presença", 44, "#43596B", 90, 920, 900, bold=False)
            self._template_text("INFORMAÇÕES E CONTATO", 34, "#E4C77B", 90, 1650, 900)
        else:
            self._width, self._height = 1080, 1080
            self._canvas_color = QColor("#102A43")
            self._set_template_canvas()
            self._template_rect(0, 0, 1080, 20, "#D6B66D", "Faixa superior")
            self._template_rect(80, 170, 180, 10, "#D6B66D", "Detalhe")
            self._template_text("INFORMAÇÃO EM DESTAQUE", 76, "#FFFFFF", 80, 270, 900)
            self._template_text("Inclua aqui os principais dados ou a mensagem que deseja destacar.", 42, "#C5D3DE", 84, 515, 900, bold=False)
            self._template_text("CENTRAL INTELIGENTE DE MÍDIA", 25, "#D6B66D", 84, 950, 900)
        self.width_spin.setValue(self._width)
        self.height_spin.setValue(self._height)
        self.canvas_size_label.setText(f"{self._width} × {self._height} px")
        self.scene.clearSelection()
        self._refresh_layers()
        self.view_fit()
        self.status_label.setText(f"Modelo '{choice}' aplicado. Edite os textos e mova os elementos para personalizar.")

    def _reset_for_template(self) -> None:
        self.scene.clear()
        self.current_file = None
        self.project_label.setText("Projeto sem título")
        self.scene.setSceneRect(QRectF(0, 0, self._width, self._height))

    def _set_template_canvas(self) -> None:
        self.scene.setSceneRect(QRectF(0, 0, self._width, self._height))
        self._canvas_item = QGraphicsRectItem(0, 0, self._width, self._height)
        self._canvas_item.setBrush(QBrush(self._canvas_color))
        self._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        self._canvas_item.setZValue(-100000)
        self._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        self._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        self.scene.addItem(self._canvas_item)

    def _template_rect(self, x: float, y: float, width: float, height: float, color: str, name: str) -> None:
        item = QGraphicsRectItem(QRectF(0, 0, width, height))
        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(Qt.PenStyle.NoPen))
        item.setPos(x, y)
        self._make_movable(item, "shape", name)

    def _template_text(
        self,
        text: str,
        size: int,
        color: str,
        x: float,
        y: float,
        width: float,
        *,
        bold: bool = True,
    ) -> None:
        item = QGraphicsTextItem(text)
        font = QFont("Segoe UI")
        font.setPixelSize(size)
        font.setBold(bold)
        item.setFont(font)
        item.setDefaultTextColor(QColor(color))
        item.setTextWidth(width)
        item.setPos(x, y)
        self._make_movable(item, "text", text.splitlines()[0][:40])

    def _content_items(self) -> list[QGraphicsItem]:
        return [
            item
            for item in self.scene.items()
            if item.data(ITEM_KIND_KEY) != CANVAS_BG_KEY
        ]

    def _selection_changed(self) -> None:
        selected = self.scene.selectedItems()
        item = selected[0] if selected else None
        self._update_selection_controls(item)
        self._refresh_layers(select_item=item)

    def _update_selection_controls(self, item: QGraphicsItem | None) -> None:
        enabled = item is not None
        self.selection_label.setText(
            "Nenhum objeto selecionado"
            if item is None
            else f"Selecionado: {item.data(ITEM_NAME_KEY) or 'Objeto'}\n"
                 f"Posição: {item.pos().x():.0f}, {item.pos().y():.0f}"
        )
        is_text = enabled and item.data(ITEM_KIND_KEY) == "text"
        is_shape = enabled and item.data(ITEM_KIND_KEY) == "shape"
        for button in (self.edit_text_button, self.font_button):
            button.setEnabled(bool(is_text))
        self.color_button.setEnabled(bool(is_text or is_shape))
        for button in (
            self.center_button,
            self.apply_transform_button,
            self.duplicate_button,
            self.forward_button,
            self.backward_button,
            self.delete_button,
        ):
            button.setEnabled(enabled)
        if item is not None:
            self.rotation_spin.blockSignals(True)
            self.scale_spin.blockSignals(True)
            self.opacity_slider.blockSignals(True)
            self.rotation_spin.setValue(float(item.rotation()))
            self.scale_spin.setValue(float(item.scale()))
            self.opacity_slider.setValue(max(10, min(100, round(item.opacity() * 100))))
            self.rotation_spin.blockSignals(False)
            self.scale_spin.blockSignals(False)
            self.opacity_slider.blockSignals(False)

    def _refresh_layers(self, select_item: QGraphicsItem | None = None) -> None:
        if not hasattr(self, "layers"):
            return
        current = select_item
        if current is None:
            selected = self.scene.selectedItems()
            current = selected[0] if selected else None
        self._loading = True
        self._layer_objects = {}
        self.layers.clear()
        items = sorted(self._content_items(), key=lambda obj: obj.zValue(), reverse=True)
        for item in items:
            kind = str(item.data(ITEM_KIND_KEY) or "objeto")
            name = str(item.data(ITEM_NAME_KEY) or "Objeto")
            prefix = {"image": "▧", "text": "T", "shape": "▱"}.get(kind, "•")
            row = QListWidgetItem(f"{prefix}  {name}")
            item_key = id(item)
            self._layer_objects[item_key] = item
            row.setData(Qt.ItemDataRole.UserRole, item_key)
            row.setToolTip(name)
            self.layers.addItem(row)
            if item is current:
                self.layers.setCurrentItem(row)
        self._loading = False

    def _layer_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if self._loading or current is None:
            return
        try:
            item_key = int(current.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            return
        item = self._layer_objects.get(item_key)
        if item is not None and item.scene() is self.scene:
            self.scene.clearSelection()
            item.setSelected(True)
            self.view.ensureVisible(item)

    def edit_selected_text(self) -> None:
        item = self._selected_item()
        if item is None or item.data(ITEM_KIND_KEY) != "text":
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "Editar texto", "Conteúdo:", item.toPlainText()
        )
        if ok and text.strip():
            item.setPlainText(text)
            item.setData(ITEM_NAME_KEY, text.strip().splitlines()[0][:40])
            self._refresh_layers(select_item=item)
            self._update_selection_controls(item)

    def change_selected_font(self) -> None:
        item = self._selected_item()
        if not isinstance(item, QGraphicsTextItem):
            return
        selected_font, accepted = QFontDialog.getFont(item.font(), self, "Fonte e estilo")
        if not accepted:
            return
        item.setFont(selected_font)
        self._update_selection_controls(item)
        self.status_label.setText("Fonte e estilo do texto atualizados.")

    def apply_selected_transform(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setRotation(float(self.rotation_spin.value()))
        item.setScale(float(self.scale_spin.value()))
        item.setOpacity(float(self.opacity_slider.value()) / 100.0)
        self._update_selection_controls(item)
        self._refresh_layers(select_item=item)
        self.status_label.setText("Rotação, escala e opacidade aplicadas ao objeto.")

    def center_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        bounds = item.sceneBoundingRect()
        target = self.scene.sceneRect().center()
        delta = target - bounds.center()
        item.moveBy(delta.x(), delta.y())
        self._update_selection_controls(item)
        self.status_label.setText("Objeto centralizado no canvas.")

    def change_selected_color(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        current = item.defaultTextColor() if isinstance(item, QGraphicsTextItem) else item.brush().color()
        color = QColorDialog.getColor(current, self, "Cor do objeto")
        if not color.isValid():
            return
        if isinstance(item, QGraphicsTextItem):
            item.setDefaultTextColor(color)
        elif isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            item.setBrush(QBrush(color))

    def duplicate_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        clone = self._clone_item(item)
        if clone is None:
            return
        clone.setPos(item.pos() + self._offset_for_item(item))
        clone.setRotation(item.rotation())
        clone.setScale(item.scale())
        clone.setOpacity(item.opacity())
        self._make_movable(
            clone,
            str(item.data(ITEM_KIND_KEY)),
            f"{item.data(ITEM_NAME_KEY) or 'Objeto'} — cópia",
        )

    @staticmethod
    def _offset_for_item(_item: QGraphicsItem):
        from PySide6.QtCore import QPointF
        return QPointF(24, 24)

    def _clone_item(self, item: QGraphicsItem) -> QGraphicsItem | None:
        if isinstance(item, QGraphicsPixmapItem):
            clone: QGraphicsItem = QGraphicsPixmapItem(QPixmap(item.pixmap()))
            clone.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        elif isinstance(item, QGraphicsTextItem):
            clone = QGraphicsTextItem(item.toPlainText())
            clone.setFont(item.font())
            clone.setDefaultTextColor(item.defaultTextColor())
            clone.setTextWidth(item.textWidth())
        elif isinstance(item, QGraphicsEllipseItem):
            clone = QGraphicsEllipseItem(item.rect())
            clone.setBrush(item.brush())
            clone.setPen(item.pen())
        elif isinstance(item, QGraphicsRectItem):
            clone = QGraphicsRectItem(item.rect())
            clone.setBrush(item.brush())
            clone.setPen(item.pen())
        else:
            return None
        clone.setData(2, item.data(2))
        return clone

    def bring_to_front(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        item.setZValue(max((i.zValue() for i in self._content_items()), default=0) + 1)
        self._refresh_layers(select_item=item)

    def send_to_back(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        item.setZValue(min((i.zValue() for i in self._content_items()), default=0) - 1)
        self._refresh_layers(select_item=item)

    def delete_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        self.scene.removeItem(item)
        del item
        self._refresh_layers()
        self._update_selection_controls(None)

    def _selected_item(self) -> QGraphicsItem | None:
        selected = self.scene.selectedItems()
        return selected[0] if selected else None

    # ------------------------------------------------------------------
    # Projeto: JSON com imagens incorporadas em Base64
    # ------------------------------------------------------------------
    @staticmethod
    def _pixmap_to_base64(pixmap: QPixmap) -> str:
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not pixmap.save(buffer, "PNG"):
            raise OSError("Não foi possível codificar uma imagem do projeto.")
        return base64.b64encode(bytes(buffer.data())).decode("ascii")

    @staticmethod
    def _pixmap_from_base64(encoded: str) -> QPixmap:
        raw = base64.b64decode(encoded, validate=True)
        pixmap = QPixmap()
        if not pixmap.loadFromData(raw, "PNG"):
            raise ValueError("Uma imagem incorporada ao projeto está corrompida.")
        return pixmap

    def _serialize_item(self, item: QGraphicsItem) -> dict[str, Any]:
        pos = item.pos()
        data: dict[str, Any] = {
            "kind": item.data(ITEM_KIND_KEY),
            "name": item.data(ITEM_NAME_KEY) or "Objeto",
            "x": float(pos.x()),
            "y": float(pos.y()),
            "rotation": float(item.rotation()),
            "scale": float(item.scale()),
            "opacity": float(item.opacity()),
            "z": float(item.zValue()),
        }
        if isinstance(item, QGraphicsPixmapItem):
            data["image_png_base64"] = self._pixmap_to_base64(item.pixmap())
            data["smooth"] = True
        elif isinstance(item, QGraphicsTextItem):
            font = item.font()
            color = item.defaultTextColor()
            data.update(
                {
                    "text": item.toPlainText(),
                    "font_family": font.family(),
                    "font_serialized": font.toString(),
                    "font_pixel_size": font.pixelSize(),
                    "font_size_px": font.pixelSize() if font.pixelSize() > 0 else 16,
                    "font_bold": font.bold(),
                    "font_italic": font.italic(),
                    "text_color": color.name(QColor.NameFormat.HexArgb),
                    "text_width": float(item.textWidth()),
                }
            )
        elif isinstance(item, (QGraphicsRectItem, QGraphicsEllipseItem)):
            rect = item.rect()
            brush = item.brush()
            data.update(
                {
                    "shape": "ellipse" if isinstance(item, QGraphicsEllipseItem) else "rect",
                    "rect": [float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height())],
                    "fill": brush.color().name(QColor.NameFormat.HexArgb),
                }
            )
        else:
            raise TypeError(f"Tipo de objeto não suportado: {type(item).__name__}")
        return data

    def _build_item_from_data(self, data: dict[str, Any]) -> QGraphicsItem:
        kind = data.get("kind")
        if kind == "image":
            item: QGraphicsItem = QGraphicsPixmapItem(self._pixmap_from_base64(str(data["image_png_base64"])))
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        elif kind == "text":
            item = QGraphicsTextItem(str(data.get("text", "")))
            font = QFont(str(data.get("font_family", "Segoe UI")))
            serialized_font = str(data.get("font_serialized", ""))
            restored_font = bool(serialized_font and font.fromString(serialized_font))
            if restored_font and int(data.get("font_pixel_size", -1)) > 0:
                font.setPixelSize(int(data["font_pixel_size"]))
            if not restored_font:
                font.setPixelSize(max(1, int(data.get("font_size_px", 16))))
                font.setBold(bool(data.get("font_bold", False)))
                font.setItalic(bool(data.get("font_italic", False)))
            item.setFont(font)
            item.setDefaultTextColor(QColor(str(data.get("text_color", "#FF102A43"))))
            item.setTextWidth(float(data.get("text_width", -1)))
        elif kind == "shape":
            coords = data.get("rect", [0, 0, 300, 180])
            rect = QRectF(*(float(v) for v in coords))
            if data.get("shape") == "ellipse":
                item = QGraphicsEllipseItem(rect)
            else:
                item = QGraphicsRectItem(rect)
            item.setBrush(QBrush(QColor(str(data.get("fill", "#FF0B79F7")))))
            item.setPen(QPen(Qt.PenStyle.NoPen))
        else:
            raise ValueError(f"Tipo de objeto desconhecido no projeto: {kind!r}")

        item.setData(ITEM_KIND_KEY, kind)
        item.setData(ITEM_NAME_KEY, str(data.get("name", "Objeto")))
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        item.setPos(float(data.get("x", 0)), float(data.get("y", 0)))
        item.setTransformOriginPoint(item.boundingRect().center())
        item.setRotation(float(data.get("rotation", 0)))
        item.setScale(float(data.get("scale", 1)))
        item.setOpacity(max(0.1, min(1.0, float(data.get("opacity", 1.0)))))
        item.setZValue(float(data.get("z", 1)))
        return item

    def _project_data(self) -> dict[str, Any]:
        return {
            "format": PROJECT_FORMAT,
            "version": PROJECT_VERSION,
            "canvas": {
                "width": self._width,
                "height": self._height,
                "background": self._canvas_color.name(QColor.NameFormat.HexArgb),
            },
            "items": [self._serialize_item(item) for item in self._content_items()],
        }

    def save_project(self) -> None:
        if self.current_file is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar projeto de arte",
                str(self.projects_dir / "Minha arte.centralart"),
                "Projeto da Central (*.centralart)",
            )
            if not path:
                return
            self.current_file = Path(path)
            if self.current_file.suffix.lower() != ".centralart":
                self.current_file = self.current_file.with_suffix(".centralart")
        try:
            payload = json.dumps(self._project_data(), ensure_ascii=False, indent=2)
            self.current_file.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{self.current_file.name}.",
                suffix=".tmp",
                dir=str(self.current_file.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self.current_file)
            except Exception:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
        except Exception as exc:
            log.exception("Falha ao salvar projeto de arte")
            QMessageBox.critical(self, "Erro ao salvar", f"Não foi possível salvar o projeto.\n\n{exc}")
            return
        self.project_label.setText(self.current_file.name)
        self.status_label.setText(f"Projeto salvo em: {self.current_file}")
        self.project_changed.emit(str(self.current_file))

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir projeto de arte",
            str(self.projects_dir),
            "Projeto da Central (*.centralart *.json)",
        )
        if not path:
            return
        if self._content_items():
            answer = QMessageBox.question(
                self,
                "Abrir outro projeto",
                "A arte atual será substituída. Salve o projeto atual antes, se desejar mantê-lo. Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if data.get("format") != PROJECT_FORMAT:
                raise ValueError("Esse arquivo não é um projeto compatível do Estúdio de Artes.")
            if int(data.get("version", 0)) > PROJECT_VERSION:
                raise ValueError("O projeto foi criado por uma versão mais recente do Estúdio de Artes.")
            canvas = data.get("canvas") or {}
            width = max(64, min(5000, int(canvas.get("width", 1080))))
            height = max(64, min(5000, int(canvas.get("height", 1080))))
            color = QColor(str(canvas.get("background", "#FFFFFFFF")))
            if not color.isValid():
                raise ValueError("A cor de fundo do projeto é inválida.")
            item_data = data.get("items", [])
            if not isinstance(item_data, list) or len(item_data) > 500:
                raise ValueError("O projeto excede o limite de 500 objetos desta versão ou possui uma lista inválida.")
            restored = [self._build_item_from_data(item) for item in item_data]
        except Exception as exc:
            log.exception("Falha ao abrir projeto de arte")
            QMessageBox.critical(self, "Não foi possível abrir", str(exc))
            return

        self.scene.clear()
        self._width, self._height = width, height
        self._canvas_color = color
        self.scene.setSceneRect(QRectF(0, 0, width, height))
        self.scene.setBackgroundBrush(QColor("#DCE3EA"))
        self._canvas_item = QGraphicsRectItem(0, 0, width, height)
        self._canvas_item.setBrush(QBrush(color))
        self._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        self._canvas_item.setZValue(-100000)
        self._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        self._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        self.scene.addItem(self._canvas_item)
        for item in restored:
            self.scene.addItem(item)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.canvas_size_label.setText(f"{width} × {height} px")
        self.current_file = Path(path)
        self.project_label.setText(self.current_file.name)
        self._refresh_layers()
        self.view_fit()
        self.status_label.setText(f"Projeto aberto: {self.current_file.name}")

    def new_project(self) -> None:
        if self._content_items():
            answer = QMessageBox.question(
                self,
                "Criar nova arte",
                "Deseja descartar o conteúdo atual e começar uma nova arte? Salve o projeto antes, se necessário.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.scene.clear()
        self._width = 1080
        self._height = 1080
        self._canvas_color = QColor("#FFFFFF")
        self.scene.setSceneRect(QRectF(0, 0, self._width, self._height))
        self._canvas_item = QGraphicsRectItem(0, 0, self._width, self._height)
        self._canvas_item.setBrush(QBrush(self._canvas_color))
        self._canvas_item.setPen(QPen(QColor("#B8C3CE"), 1))
        self._canvas_item.setZValue(-100000)
        self._canvas_item.setData(ITEM_KIND_KEY, CANVAS_BG_KEY)
        self._canvas_item.setData(ITEM_NAME_KEY, "Fundo da arte")
        self.scene.addItem(self._canvas_item)
        self.width_spin.setValue(self._width)
        self.height_spin.setValue(self._height)
        self.canvas_size_label.setText("1080 × 1080 px")
        self.current_file = None
        self.project_label.setText("Projeto sem título")
        self._refresh_layers()
        self._update_selection_controls(None)
        self.view_fit()

    # ------------------------------------------------------------------
    # Exportação em alta resolução
    # ------------------------------------------------------------------
    def _render_art(self) -> QImage:
        image = QImage(
            QSize(self._width, self._height),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.scene.render(
            painter,
            QRectF(0, 0, self._width, self._height),
            QRectF(0, 0, self._width, self._height),
            Qt.AspectRatioMode.IgnoreAspectRatio,
        )
        painter.end()
        return image

    def export_art(self) -> None:
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar arte",
            str(self.projects_dir / "Minha arte.png"),
            "Imagem PNG (*.png);;Imagem JPEG (*.jpg *.jpeg);;Documento PDF (*.pdf)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if not suffix:
            suffix = ".pdf" if "PDF" in selected_filter else ".jpg" if "JPEG" in selected_filter else ".png"
            path += suffix
        suffix = Path(path).suffix.lower()
        try:
            image = self._render_art()
            if suffix in {".jpg", ".jpeg"}:
                rgb = QImage(image.size(), QImage.Format.Format_RGB32)
                rgb.fill(self._canvas_color)
                painter = QPainter(rgb)
                painter.drawImage(0, 0, image)
                painter.end()
                ok = rgb.save(path, "JPEG", 95)
            elif suffix == ".pdf":
                png_buffer = QBuffer()
                png_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                if not image.save(png_buffer, "PNG"):
                    raise OSError("Não foi possível preparar a imagem para o PDF.")
                pdf_image = PILImage.open(BytesIO(bytes(png_buffer.data()))).convert("RGB")
                pdf_image.save(path, "PDF", resolution=300.0)
                ok = Path(path).is_file() and Path(path).stat().st_size > 0
            elif suffix == ".png":
                ok = image.save(path, "PNG")
            else:
                raise ValueError("Formato não suportado. Use PNG, JPG ou PDF.")
            if not ok:
                raise OSError("O formato escolhido não conseguiu gravar o arquivo.")
        except Exception as exc:
            log.exception("Falha ao exportar arte")
            QMessageBox.critical(self, "Erro na exportação", f"Não foi possível exportar a arte.\n\n{exc}")
            return
        self.status_label.setText(f"Arte exportada com sucesso: {path}")
        QMessageBox.information(self, "Exportação concluída", f"Arquivo criado em:\n{path}")
