from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.sections import Section
from monitor_noticias.ui.theme_engine import transform_stylesheet
from monitor_noticias.ui.theme_store import (
    THEME_CLARO,
    THEME_ESCURO,
    load_saved_theme,
    normalize_theme,
    save_theme,
)

_BASE_QSS_PROPERTY = "_central_theme_base_qss_v138"
_APPLIED_QSS_PROPERTY = "_central_theme_applied_qss_v138"


def _apply_widget_stylesheet(widget: QWidget, theme_id: str) -> None:
    current = widget.styleSheet() or ""
    last_applied = widget.property(_APPLIED_QSS_PROPERTY)
    stored_base = widget.property(_BASE_QSS_PROPERTY)

    # Quando outro módulo atualiza seu QSS, a nova folha vira a nova origem.
    if stored_base is None or current != last_applied:
        base = current
        widget.setProperty(_BASE_QSS_PROPERTY, base)
    else:
        base = str(stored_base)

    if not base.strip():
        widget.setProperty(_APPLIED_QSS_PROPERTY, current)
        return

    transformed = transform_stylesheet(base, theme_id, widget.objectName())
    widget.setProperty(_APPLIED_QSS_PROPERTY, transformed)
    if transformed != current:
        widget.setStyleSheet(transformed)


def apply_widget_theme_stylesheet(widget: QWidget, theme_id: str) -> None:
    """Aplica a conversão a um widget novo ou cujo QSS mudou durante o uso."""
    _apply_widget_stylesheet(widget, normalize_theme(theme_id))


def _apply_palette(window: QWidget, theme_id: str) -> None:
    palette = QPalette(window.palette())
    if theme_id == THEME_ESCURO:
        values = {
            QPalette.ColorRole.Window: "#0D1926",
            QPalette.ColorRole.WindowText: "#E5EDF4",
            QPalette.ColorRole.Base: "#152637",
            QPalette.ColorRole.AlternateBase: "#1C3043",
            QPalette.ColorRole.ToolTipBase: "#21394F",
            QPalette.ColorRole.ToolTipText: "#F0F4F8",
            QPalette.ColorRole.Text: "#E5EDF4",
            QPalette.ColorRole.Button: "#1B2D3F",
            QPalette.ColorRole.ButtonText: "#E5EDF4",
            QPalette.ColorRole.BrightText: "#FFFFFF",
            QPalette.ColorRole.Highlight: "#C6A15B",
            QPalette.ColorRole.HighlightedText: "#0A1C2A",
            QPalette.ColorRole.PlaceholderText: "#8FA4B7",
        }
    else:
        values = {
            QPalette.ColorRole.Window: "#F4F7FA",
            QPalette.ColorRole.WindowText: "#1D3548",
            QPalette.ColorRole.Base: "#FFFFFF",
            QPalette.ColorRole.AlternateBase: "#F1F5F8",
            QPalette.ColorRole.ToolTipBase: "#FFFFFF",
            QPalette.ColorRole.ToolTipText: "#1D3548",
            QPalette.ColorRole.Text: "#20384C",
            QPalette.ColorRole.Button: "#F0F4F7",
            QPalette.ColorRole.ButtonText: "#20384C",
            QPalette.ColorRole.BrightText: "#FFFFFF",
            QPalette.ColorRole.Highlight: "#315F7B",
            QPalette.ColorRole.HighlightedText: "#FFFFFF",
            QPalette.ColorRole.PlaceholderText: "#71879A",
        }
    for role, value in values.items():
        palette.setColor(role, QColor(value))
    window.setPalette(palette)


class ThemePreferencesCard(QFrame):
    """Seletor global de aparência incluído no início da aba Configurações."""

    def __init__(self, window, preference_file: Path, initial_theme: str) -> None:
        super().__init__()
        self.window = window
        self.preference_file = Path(preference_file)
        self.current_theme = normalize_theme(initial_theme)
        self.setObjectName("appearanceCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 13, 16, 13)
        root.setSpacing(10)

        heading = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(3)

        title = QLabel("Aparência do programa")
        title.setObjectName("appearanceTitle")
        subtitle = QLabel(
            "Altere as cores de todas as abas. A escolha é aplicada imediatamente e fica salva neste computador."
        )
        subtitle.setObjectName("appearanceSubtitle")
        subtitle.setWordWrap(True)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        heading.addLayout(title_block, 1)

        self.feedback = QLabel("Tema atual")
        self.feedback.setObjectName("appearanceFeedback")
        heading.addWidget(self.feedback, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(heading)

        choices = QHBoxLayout()
        choices.setSpacing(10)
        self.theme_buttons: dict[str, QPushButton] = {}
        self._add_choice(choices, THEME_ESCURO, "◐  ESCURO  ·  Marinho + dourado")
        self._add_choice(choices, THEME_CLARO, "☼  CLARO  ·  Neutro + azul")
        root.addLayout(choices)

        self.setStyleSheet(self._stylesheet())
        self._sync_buttons(self.current_theme)

    def _add_choice(self, layout: QHBoxLayout, theme_id: str, text: str) -> None:
        button = QPushButton(text)
        button.setObjectName("themeChoice")
        button.setProperty("themeId", theme_id)
        button.setCheckable(True)
        button.setMinimumHeight(58)
        button.setMinimumWidth(180)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setToolTip(
            "Tema Escuro: interface em azul-marinho, com detalhes dourados."
            if theme_id == THEME_ESCURO
            else "Tema Claro: interface em tons claros, com detalhes em azul."
        )
        button.clicked.connect(lambda _checked=False, chosen=theme_id: self._choose(chosen))
        self.theme_buttons[theme_id] = button
        layout.addWidget(button, 1)

    def _sync_buttons(self, theme_id: str) -> None:
        for key, button in self.theme_buttons.items():
            button.blockSignals(True)
            button.setChecked(key == theme_id)
            button.blockSignals(False)

    def _choose(self, theme_id: str) -> None:
        selected = normalize_theme(theme_id)
        apply_theme(self.window, selected)
        self.current_theme = selected
        self._sync_buttons(selected)
        try:
            save_theme(self.preference_file, selected)
        except OSError as exc:
            self.feedback.setText("Tema aplicado; não foi possível salvar a preferência.")
            self.feedback.setToolTip(str(exc))
            return
        self.feedback.setText("Tema salvo para a próxima abertura")
        self.feedback.setToolTip("")

    @staticmethod
    def _stylesheet() -> str:
        return """
        QFrame#appearanceCard {
            background:#FFFFFF;
            border:1px solid #D6E3EE;
            border-radius:13px;
        }
        QLabel#appearanceTitle {
            color:#102F49;
            background:transparent;
            border:0;
            font-size:16px;
            font-weight:850;
        }
        QLabel#appearanceSubtitle {
            color:#6D8294;
            background:transparent;
            border:0;
            font-size:10px;
        }
        QLabel#appearanceFeedback {
            color:#6B8294;
            background:#F1F6F9;
            border:1px solid #E1EAF0;
            border-radius:8px;
            padding:7px 10px;
            font-size:9px;
            font-weight:700;
        }
        QPushButton#themeChoice {
            text-align:left;
            background:#F5F8FA;
            color:#29475C;
            border:1px solid #DCE6ED;
            border-radius:10px;
            padding:9px 13px;
            font-size:11px;
            font-weight:700;
        }
        QPushButton#themeChoice:hover {
            background:#EDF3F7;
            border:1px solid #A9C0D0;
        }
        QPushButton#themeChoice[themeId="escuro"] {
            background:#0B2B45;
            color:#F4F7FA;
            border:1px solid #294D67;
        }
        QPushButton#themeChoice[themeId="escuro"]:checked {
            background:#123B58;
            color:#FFFFFF;
            border:2px solid #C6A15B;
        }
        QPushButton#themeChoice[themeId="claro"]:checked {
            background:#E6EFF5;
            color:#102F49;
            border:2px solid #6489A4;
        }
        """


def apply_theme(window, theme_id: str) -> None:
    """Aplica o tema a todos os widgets atuais sem recriar páginas ou estado."""
    selected = normalize_theme(theme_id)
    window._central_theme = selected
    window._central_theme_applying = True
    try:
        _apply_palette(window, selected)
        widgets = [window, *window.findChildren(QWidget)]
        for widget in widgets:
            _apply_widget_stylesheet(widget, selected)
    finally:
        window._central_theme_applying = False
    window.update()


def install_theme_preferences(window) -> None:
    """Instala o seletor, restaura a escolha e acompanha widgets dinâmicos."""
    if getattr(window, "_theme_preferences_installed", False):
        return

    settings_page = getattr(window, "pages", {}).get(Section.SETTINGS)
    layout = getattr(settings_page, "root", None)
    if not isinstance(layout, QVBoxLayout):
        return

    preference_file = Path(window.paths.data) / "preferences" / "appearance.json"
    selected = load_saved_theme(preference_file)
    card = ThemePreferencesCard(window, preference_file, selected)
    layout.insertWidget(1, card)

    window.theme_preferences_card = card
    window.theme_preference_file = preference_file
    window._theme_preferences_installed = True
    apply_theme(window, selected)
