from __future__ import annotations

"""V159 — controle de espaçamento tipográfico.

Adiciona espaçamento entre palavras e entrelinhas usando propriedades do
QTextDocument compatíveis com o HTML rico já usado pelo projeto .centralart.
Não altera o formato dos projetos nem cria uma camada gráfica paralela.
"""

from PySide6.QtGui import QTextBlockFormat, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QDoubleSpinBox, QPushButton, QGraphicsTextItem

from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave


def _editable_text(page) -> QGraphicsTextItem | None:
    selected = list(page.scene.selectedItems())
    if len(selected) != 1 or not isinstance(selected[0], QGraphicsTextItem):
        page.status_label.setText("Selecione uma única caixa de texto para ajustar o espaçamento.")
        return None
    item = selected[0]
    if bool(item.data(LOCKED_KEY)) or not item.isVisible():
        page.status_label.setText("Desbloqueie e mostre a camada de texto antes de editá-la.")
        return None
    return item


def _selected_cursor(item: QGraphicsTextItem) -> QTextCursor:
    cursor = item.textCursor()
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.Document)
    return cursor


def _finish_change(page, item: QGraphicsTextItem, message: str) -> None:
    item.update()
    page.scene.update()
    history_timer = getattr(page, "_v145_history_timer", None)
    if history_timer is not None and not getattr(page, "_v145_history_suspended", False):
        history_timer.start()
    _schedule_autosave(page)
    page.status_label.setText(message)


def _apply_word_spacing(page) -> None:
    item = _editable_text(page)
    if item is None:
        return
    control = getattr(page, "v159_word_spacing", None)
    value = float(control.value()) if control is not None else 0.0
    char_format = QTextCharFormat()
    char_format.setFontWordSpacing(value)
    cursor = _selected_cursor(item)
    cursor.mergeCharFormat(char_format)
    item.setTextCursor(cursor)
    _finish_change(page, item, f"Espaçamento entre palavras ajustado para {value:.1f} px.")


def _apply_line_spacing(page) -> None:
    item = _editable_text(page)
    if item is None:
        return
    control = getattr(page, "v159_line_spacing", None)
    value = int(round(control.value())) if control is not None else 100
    block_format = QTextBlockFormat()
    block_format.setLineHeight(
        float(value),
        QTextBlockFormat.LineHeightTypes.ProportionalHeight,
    )
    cursor = _selected_cursor(item)
    cursor.mergeBlockFormat(block_format)
    item.setTextCursor(cursor)
    _finish_change(page, item, f"Entrelinhas ajustadas para {value}%.")


def _sync_controls(page) -> None:
    selected = list(page.scene.selectedItems())
    valid = bool(
        len(selected) == 1
        and isinstance(selected[0], QGraphicsTextItem)
        and selected[0].isVisible()
        and not bool(selected[0].data(LOCKED_KEY))
    )
    for name in (
        "v159_word_spacing",
        "v159_word_spacing_apply",
        "v159_line_spacing",
        "v159_line_spacing_apply",
    ):
        control = getattr(page, name, None)
        if control is not None:
            control.setEnabled(valid)


def _install_controls(page) -> None:
    toolbar = getattr(page, "v147_text_toolbar", None)
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None or getattr(page, "_v159_typography_installed", False):
        return

    page.v159_word_spacing = QDoubleSpinBox(toolbar)
    page.v159_word_spacing.setObjectName("artStudioWordSpacingV159")
    page.v159_word_spacing.setRange(0.0, 30.0)
    page.v159_word_spacing.setSingleStep(0.5)
    page.v159_word_spacing.setDecimals(1)
    page.v159_word_spacing.setValue(0.0)
    page.v159_word_spacing.setSuffix(" px")
    page.v159_word_spacing.setFixedWidth(78)
    page.v159_word_spacing.setToolTip("Distância adicional entre as palavras do texto selecionado")
    layout.addWidget(page.v159_word_spacing)

    page.v159_word_spacing_apply = QPushButton("Palavras")
    page.v159_word_spacing_apply.setObjectName("artStudioApplyWordSpacingV159")
    page.v159_word_spacing_apply.setProperty("secondary", True)
    page.v159_word_spacing_apply.setToolTip("Aplicar o espaçamento entre palavras")
    layout.addWidget(page.v159_word_spacing_apply)

    page.v159_line_spacing = QDoubleSpinBox(toolbar)
    page.v159_line_spacing.setObjectName("artStudioLineSpacingV159")
    page.v159_line_spacing.setRange(80.0, 250.0)
    page.v159_line_spacing.setSingleStep(5.0)
    page.v159_line_spacing.setDecimals(0)
    page.v159_line_spacing.setValue(100.0)
    page.v159_line_spacing.setSuffix(" %")
    page.v159_line_spacing.setFixedWidth(76)
    page.v159_line_spacing.setToolTip("Altura das linhas em relação ao tamanho padrão")
    layout.addWidget(page.v159_line_spacing)

    page.v159_line_spacing_apply = QPushButton("Linhas")
    page.v159_line_spacing_apply.setObjectName("artStudioApplyLineSpacingV159")
    page.v159_line_spacing_apply.setProperty("secondary", True)
    page.v159_line_spacing_apply.setToolTip("Aplicar o espaçamento entre linhas")
    layout.addWidget(page.v159_line_spacing_apply)

    page.v159_word_spacing_apply.clicked.connect(lambda: _apply_word_spacing(page))
    page.v159_line_spacing_apply.clicked.connect(lambda: _apply_line_spacing(page))
    page.scene.selectionChanged.connect(lambda: _sync_controls(page))
    page._v159_typography_installed = True
    _sync_controls(page)


def enhance_art_studio_page_v159(page) -> None:
    if getattr(page, "_v159_installed", False):
        return
    _install_controls(page)
    if getattr(page, "_v159_typography_installed", False):
        page._v159_installed = True


def install_art_studio_v159() -> None:
    """Instala os controles V159 depois da tipografia V158."""
    from monitor_noticias.ui.main_window import MainWindow

    if getattr(MainWindow, "_v159_integration_installed", False):
        return
    original_init = MainWindow.__init__

    def init_with_v159(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v159(page)

    MainWindow.__init__ = init_with_v159
    MainWindow._v159_integration_installed = True
