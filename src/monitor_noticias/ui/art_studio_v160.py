from __future__ import annotations

"""V160 — tipografia avançada e correção de contraste da navegação lateral.

- Adiciona espaçamento entre caracteres à barra de texto, preservando seleção,
  histórico e autosave do formato .centralart.
- Faz os ícones da navegação manterem contraste nos temas Claro/Escuro.
- Inclui botões extras (como Estúdio de Artes) no mesmo comportamento compacto.
"""

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QDoubleSpinBox, QPushButton, QGraphicsTextItem

from monitor_noticias.ui.art_studio_v145 import LOCKED_KEY
from monitor_noticias.ui.art_studio_v157 import _schedule_autosave
from monitor_noticias.ui.sidebar_widgets import SidebarNavItem


_INSTALLED = False


def _selected_editable_text(page) -> QGraphicsTextItem | None:
    selected = list(page.scene.selectedItems())
    if len(selected) != 1 or not isinstance(selected[0], QGraphicsTextItem):
        page.status_label.setText("Selecione uma única caixa de texto para ajustar o espaçamento entre caracteres.")
        return None
    item = selected[0]
    if bool(item.data(LOCKED_KEY)) or not item.isVisible():
        page.status_label.setText("Desbloqueie e mostre a camada de texto antes de editá-la.")
        return None
    return item


def _whole_or_selected_cursor(item: QGraphicsTextItem) -> QTextCursor:
    cursor = item.textCursor()
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.Document)
    return cursor


def _apply_letter_spacing(page) -> None:
    item = _selected_editable_text(page)
    if item is None:
        return
    control = getattr(page, "v160_letter_spacing", None)
    value = float(control.value()) if control is not None else 0.0

    char_format = QTextCharFormat()
    char_format.setFontLetterSpacingType(QFont.SpacingType.AbsoluteSpacing)
    char_format.setFontLetterSpacing(value)

    cursor = _whole_or_selected_cursor(item)
    cursor.mergeCharFormat(char_format)
    item.setTextCursor(cursor)
    item.update()
    page.scene.update()

    history_timer = getattr(page, "_v145_history_timer", None)
    if history_timer is not None and not getattr(page, "_v145_history_suspended", False):
        history_timer.start()
    _schedule_autosave(page)
    page.status_label.setText(
        f"Espaçamento entre caracteres ajustado para {value:.1f} px."
    )


def _sync_letter_spacing_control(page) -> None:
    selected = list(page.scene.selectedItems())
    valid = bool(
        len(selected) == 1
        and isinstance(selected[0], QGraphicsTextItem)
        and selected[0].isVisible()
        and not bool(selected[0].data(LOCKED_KEY))
    )
    for name in ("v160_letter_spacing", "v160_letter_spacing_apply"):
        control = getattr(page, name, None)
        if control is not None:
            control.setEnabled(valid)


def enhance_art_studio_page_v160(page) -> None:
    if getattr(page, "_v160_typography_installed", False):
        return
    toolbar = getattr(page, "v147_text_toolbar", None)
    layout = toolbar.layout() if toolbar is not None else None
    if layout is None:
        return

    page.v160_letter_spacing = QDoubleSpinBox(toolbar)
    page.v160_letter_spacing.setObjectName("artStudioLetterSpacingV160")
    page.v160_letter_spacing.setRange(-5.0, 30.0)
    page.v160_letter_spacing.setSingleStep(0.5)
    page.v160_letter_spacing.setDecimals(1)
    page.v160_letter_spacing.setValue(0.0)
    page.v160_letter_spacing.setSuffix(" px")
    page.v160_letter_spacing.setFixedWidth(82)
    page.v160_letter_spacing.setToolTip(
        "Ajusta a distância entre letras do trecho selecionado ou de toda a caixa de texto."
    )

    page.v160_letter_spacing_apply = QPushButton("Letras")
    page.v160_letter_spacing_apply.setObjectName("artStudioApplyLetterSpacingV160")
    page.v160_letter_spacing_apply.setProperty("secondary", True)
    page.v160_letter_spacing_apply.setToolTip("Aplicar o espaçamento entre caracteres")

    layout.addWidget(page.v160_letter_spacing)
    layout.addWidget(page.v160_letter_spacing_apply)
    page.v160_letter_spacing_apply.clicked.connect(lambda: _apply_letter_spacing(page))
    page.scene.selectionChanged.connect(lambda: _sync_letter_spacing_control(page))
    page._v160_typography_installed = True
    _sync_letter_spacing_control(page)


# ---------------------------------------------------------------------------
# Navegação lateral: o QSS antigo usava azul muito claro para ícones inativos.
# No tema claro ele ficava quase igual ao fundo. A cor passada por seção era
# recebida no construtor SidebarNavItem, mas não era aplicada ao QLabel.
# ---------------------------------------------------------------------------
def _darken_for_light_theme(color_value: str) -> str:
    color = QColor(str(color_value or ""))
    if not color.isValid():
        color = QColor("#526F84")
    hue, saturation, value, alpha = color.getHsv()
    if hue < 0:
        hue = 205
    # Cores mais escuras mantêm contraste no tema claro. O theme_engine
    # transforma esses tons em cores claras no tema escuro.
    value = max(92, min(158, round(value * 0.60)))
    saturation = max(90, saturation)
    adjusted = QColor.fromHsv(hue, saturation, value, alpha)
    return adjusted.name()


def _sidebar_owner_theme(widget) -> str | None:
    owner = widget
    while owner is not None:
        theme = getattr(owner, "_central_theme", None)
        if theme:
            return str(theme)
        owner = owner.parentWidget()
    return None


def _style_sidebar_icon(item: SidebarNavItem) -> None:
    icon = getattr(item, "icon", None)
    if icon is None:
        return
    if bool(getattr(item, "_v160_sidebar_active", False)):
        # O QSS global fornece a cor escura do ícone sobre o fundo selecionado.
        icon.setStyleSheet("")
        return

    base_color = str(getattr(item, "_v160_icon_color", "#526F84"))
    icon.setStyleSheet(
        "QLabel#sidebarNavIcon {"
        f"color:{base_color};font-family:'Segoe UI Symbol';font-size:17px;font-weight:800;"
        "background:transparent;border:0;}"
    )
    theme = _sidebar_owner_theme(item)
    if theme:
        try:
            from monitor_noticias.ui.theme_preferences import apply_widget_theme_stylesheet
            apply_widget_theme_stylesheet(icon, theme)
        except Exception:
            pass


def _install_sidebar_icon_contrast() -> None:
    if getattr(SidebarNavItem, "_v160_icon_patch_installed", False):
        return

    original_init = SidebarNavItem.__init__
    original_set_active = SidebarNavItem.set_active

    def init_with_visible_icon(self, icon_text, label_text, icon_color, parent=None):
        original_init(self, icon_text, label_text, icon_color, parent)
        self._v160_icon_color = _darken_for_light_theme(icon_color)
        self._v160_sidebar_active = False
        # Reserva geometria para o ícone tanto expandido quanto compacto.
        self.icon_wrap.setFixedSize(30, 30)
        self.icon_wrap.setMinimumSize(30, 30)
        self.icon.setMinimumSize(26, 26)
        self.icon.setAlignment(self.icon.alignment())
        self.icon.setVisible(True)
        self.icon_wrap.setVisible(True)
        self.text.setMinimumWidth(0)
        _style_sidebar_icon(self)

    def set_active_with_icon(self, value: bool) -> None:
        original_set_active(self, value)
        self._v160_sidebar_active = bool(value)
        _style_sidebar_icon(self)

    SidebarNavItem.__init__ = init_with_visible_icon
    SidebarNavItem.set_active = set_active_with_icon
    SidebarNavItem._v160_icon_patch_installed = True


def _install_compact_sidebar_compatibility() -> None:
    """Aplica o recolhimento a TODOS os itens SidebarNavItem, inclusive extras."""
    try:
        from monitor_noticias.ui import art_studio_v153 as v153
    except Exception:
        return

    if getattr(v153, "_v160_sidebar_compact_patch_installed", False):
        return

    original_set_compact = v153._set_sidebar_compact

    def set_compact_all_items(window, compact: bool) -> None:
        original_set_compact(window, compact)
        sidebar = getattr(window, "sidebar", None)
        if sidebar is None:
            return
        compact = bool(compact)
        for item in sidebar.findChildren(SidebarNavItem):
            # O botão Estúdio de Artes usa objectName próprio; por isso não era
            # alcançado pelo findChildren(..., "sidebarNavItem") da V153.
            item.text.setVisible(not compact)
            item.current_mark.setVisible(not compact)
            item.icon_wrap.setVisible(True)
            item.icon.setVisible(True)
            item.setMinimumWidth(0)
            row = item.layout()
            if row is not None:
                row.setContentsMargins(5 if compact else 8, 0, 5 if compact else 10, 0)
                row.setSpacing(0 if compact else 8)
            item.icon_wrap.setFixedSize(32 if compact else 30, 30)
            item.setToolTip(item.accessibleName() if compact else "")
            _style_sidebar_icon(item)
        sidebar.updateGeometry()
        sidebar.update()

    v153._set_sidebar_compact = set_compact_all_items
    v153._v160_sidebar_compact_patch_installed = True


def install_art_studio_v160() -> None:
    """Instala o ajuste dos ícones e os novos controles do Estúdio de Artes."""
    global _INSTALLED
    if _INSTALLED:
        return

    _install_sidebar_icon_contrast()
    _install_compact_sidebar_compatibility()

    from monitor_noticias.ui.main_window import MainWindow
    if getattr(MainWindow, "_v160_integration_installed", False):
        _INSTALLED = True
        return

    original_init = MainWindow.__init__

    def init_with_v160(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        page = getattr(self, "art_studio_page", None)
        if page is not None:
            enhance_art_studio_page_v160(page)
        # A navegação pode ter sido remontada depois da criação dos botões.
        # Reaplica contraste sem mudar largura, grupos ou seção selecionada.
        sidebar = getattr(self, "sidebar", None)
        if sidebar is not None:
            for item in sidebar.findChildren(SidebarNavItem):
                _style_sidebar_icon(item)

    MainWindow.__init__ = init_with_v160
    MainWindow._v160_integration_installed = True
    _INSTALLED = True
