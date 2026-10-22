from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

_PATCHED = False


GHOST_COMPACT = """
QPushButton {
    background:#FFFFFF;
    border:1px solid #C9DDF2;
    color:#0C3974;
    border-radius:7px;
    padding:5px 6px;
    min-height:28px;
    font-size:9pt;
    font-weight:750;
}
QPushButton:hover { background:#EEF6FF; border-color:#8EBBEA; }
"""

PRIMARY_COMPACT = """
QPushButton {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7737F6,stop:1 #087AF7);
    border:0;
    color:#FFFFFF;
    border-radius:8px;
    padding:5px 8px;
    min-height:30px;
    font-size:9pt;
    font-weight:850;
}
QPushButton:hover { border:1px solid #7A8BFF; }
"""

DANGER_COMPACT = """
QPushButton {
    background:#FFF1F4;
    border:1px solid #FFB3C5;
    color:#D62852;
    border-radius:8px;
    padding:5px 7px;
    min-height:30px;
    font-size:9pt;
    font-weight:800;
}
QPushButton:hover { background:#FFE5EB; }
"""


def _remove_from_layout(layout, widget) -> bool:
    """Remove um widget de qualquer layout aninhado, sem destruir o controle."""
    if layout is None:
        return False
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is widget:
            layout.removeWidget(widget)
            return True
        nested = item.layout()
        if nested is not None and _remove_from_layout(nested, widget):
            return True
    return False


def _detach_control(widget, editor=None) -> None:
    # Sobe pela hierarquia até encontrar o layout que contém o botão, incluindo
    # sublayouts aninhados de precisão/gestão do cartão da timeline.
    parent = widget.parentWidget()
    while parent is not None:
        layout = parent.layout()
        if layout is not None and _remove_from_layout(layout, widget):
            return
        parent = parent.parentWidget()


def _compact_button(widget, style: str) -> None:
    widget.setStyleSheet(style)
    widget.setMinimumWidth(0)
    widget.setMaximumWidth(16777215)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    widget.setMinimumHeight(30 if style != GHOST_COMPACT else 28)


def _make_row(parent, layout, controls, style=GHOST_COMPACT) -> None:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(5)
    for control in controls:
        _compact_button(control, style)
        row.addWidget(control, 1)
    layout.addLayout(row)


def _install_or_refresh_controls(widget) -> None:
    quick = widget.btn_mark_start.parentWidget()
    quick_layout = quick.layout() if quick is not None else None
    if quick is None or quick_layout is None:
        return

    panel = getattr(widget, "_timeline_side_controls_panel", None)
    if panel is None:
        panel = QFrame(quick)
        panel.setObjectName("timelineSideControlsPanel")
        panel.setStyleSheet(
            "QFrame#timelineSideControlsPanel {"
            "background:#F7FAFF; border:1px solid #DCE9F6; border-radius:9px;"
            "}"
            "QLabel#timelineSideControlsTitle {"
            "color:#08245F; font-size:10pt; font-weight:850;"
            "background:transparent; border:0;"
            "}"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 7, 8, 8)
        panel_layout.setSpacing(6)

        heading = QLabel("Controles da timeline", panel)
        heading.setObjectName("timelineSideControlsTitle")
        panel_layout.addWidget(heading)

        controls = list(getattr(widget, "nudge_buttons", ()) or ())
        all_controls = [
            *controls,
            widget.btn_duplicate,
            widget.btn_up,
            widget.btn_down,
            widget.btn_cut,
            widget.btn_remove,
        ]
        # Primeiro desligamos os widgets dos layouts antigos; só depois eles
        # são adicionados ao painel novo, evitando remover acidentalmente os
        # widgets do próprio painel durante a busca recursiva.
        for control in all_controls:
            _detach_control(control, widget)
            control.setParent(panel)

        if len(controls) >= 6:
            _make_row(panel, panel_layout, controls[:3])
            _make_row(panel, panel_layout, controls[3:6])
        elif controls:
            _make_row(panel, panel_layout, controls)

        _make_row(
            panel,
            panel_layout,
            [widget.btn_duplicate, widget.btn_up, widget.btn_down],
        )
        _make_row(
            panel,
            panel_layout,
            [widget.btn_cut, widget.btn_remove],
        )

        # Corte e exclusão mantêm estilos diferentes e as mesmas conexões.
        _compact_button(widget.btn_cut, PRIMARY_COMPACT)
        _compact_button(widget.btn_remove, DANGER_COMPACT)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Insere o painel depois da ajuda de marcação e antes do espaçador final.
        info_index = quick_layout.indexOf(widget.info_label)
        insert_at = info_index + 1 if info_index >= 0 else quick_layout.count()
        quick_layout.insertWidget(insert_at, panel)
        widget._timeline_side_controls_panel = panel

    # Reaplica estilos compactos caso o tema seja reconstruído em tempo de execução.
    for control in getattr(widget, "nudge_buttons", ()):
        _compact_button(control, GHOST_COMPACT)
    for control in (widget.btn_duplicate, widget.btn_up, widget.btn_down):
        _compact_button(control, GHOST_COMPACT)
    _compact_button(widget.btn_cut, PRIMARY_COMPACT)
    _compact_button(widget.btn_remove, DANGER_COMPACT)


def install_video_timeline_side_controls_patch() -> None:
    """Move os controles da timeline para a coluna branca à direita da prévia."""
    global _PATCHED
    if _PATCHED:
        return

    from monitor_noticias.ui.video_editor_reference_page import (
        ReferenceAdvancedVideoEditorWidget,
    )

    cls = ReferenceAdvancedVideoEditorWidget
    original_style = cls._apply_reference_style

    def apply_style_with_side_controls(widget) -> None:
        original_style(widget)
        _install_or_refresh_controls(widget)

    apply_style_with_side_controls._central_timeline_side_controls_patch = True
    cls._apply_reference_style = apply_style_with_side_controls
    _PATCHED = True
