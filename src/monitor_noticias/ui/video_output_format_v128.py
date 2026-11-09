from __future__ import annotations

"""V128 — formato original ou quadro horizontal 16:9 no Editor de Vídeo."""

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from monitor_noticias.video_editor.output_format import (
    LANDSCAPE_16_9_FORMAT,
    ORIGINAL_FORMAT,
    decode_resolution_choice,
    encode_resolution_choice,
    landscape_canvas_dimensions,
)


_PATCHED = False


class _ResolutionChoiceProxy:
    """Expõe currentText() no formato esperado pelo exportador legado."""

    def __init__(self, original: QComboBox, output_format: QComboBox) -> None:
        self._original = original
        self._output_format = output_format

    def currentText(self) -> str:
        return encode_resolution_choice(
            self._original.currentText(),
            str(self._output_format.currentData() or ORIGINAL_FORMAT),
        )

    def __getattr__(self, name: str):
        # O exportador legado também chama setEnabled() durante o disparo do
        # worker; encaminhe qualquer outra operação ao QComboBox real.
        return getattr(self._original, name)


def _with_output_choice(widget, callback: Callable, *args, **kwargs):
    original_combo = widget.resolution
    widget.resolution = _ResolutionChoiceProxy(
        original_combo,
        widget.output_format_mode,
    )
    try:
        return callback(widget, *args, **kwargs)
    finally:
        widget.resolution = original_combo


def _find_layout_containing(layout, target):
    if layout is None:
        return None, -1
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout, index
        nested = item.layout()
        if nested is not None:
            found, found_index = _find_layout_containing(nested, target)
            if found is not None:
                return found, found_index
        child = item.widget()
        if child is not None and child.layout() is not None:
            found, found_index = _find_layout_containing(child.layout(), target)
            if found is not None:
                return found, found_index
    return None, -1


def _install_output_selector(widget) -> None:
    if hasattr(widget, "output_format_mode"):
        return

    target_check = getattr(widget, "target_check", None)
    if target_check is None or target_check.parentWidget() is None:
        return

    parent = target_check.parentWidget()
    layout, index = _find_layout_containing(parent.layout(), target_check)
    if layout is None or index < 0:
        return

    row = QHBoxLayout()
    row.setContentsMargins(0, 2, 0, 2)
    row.setSpacing(8)

    label = QLabel("Formato do vídeo:", parent)
    label.setObjectName("videoOutputFormatLabel")
    label.setToolTip(
        "Original usa a proporção do primeiro vídeo da timeline. "
        "Celular deitado cria um quadro horizontal 16:9."
    )

    combo = QComboBox(parent)
    combo.setObjectName("videoOutputFormat")
    combo.addItem("Original — manter formato do vídeo", ORIGINAL_FORMAT)
    combo.addItem("Celular deitado — 16:9", LANDSCAPE_16_9_FORMAT)
    combo.setCurrentIndex(0)
    combo.setMinimumWidth(245)
    combo.setToolTip(
        "Original: mantém a proporção do primeiro vídeo.\n"
        "Celular deitado (16:9): cria um quadro horizontal; não estica nem corta. "
        "Quando necessário, o espaço restante recebe faixas pretas."
    )

    hint = QLabel(
        "Ajusta sem esticar ou cortar; pode criar faixas para completar o quadro.",
        parent,
    )
    hint.setObjectName("videoOutputFormatHint")
    hint.setWordWrap(True)
    hint.setStyleSheet(
        "color:#6079A5;background:transparent;border:none;font-size:9pt;"
    )

    row.addWidget(label)
    row.addWidget(combo)
    row.addWidget(hint, 1)
    layout.insertLayout(index, row)

    label.setStyleSheet(
        "color:#08245F;background:transparent;border:none;font-weight:700;"
    )
    combo.setStyleSheet(
        "QComboBox{background:#FFFFFF;color:#08245F;border:1px solid #C9DDF2;"
        "border-radius:8px;padding:6px 9px;min-height:25px;}"
        "QComboBox:focus{border:1px solid #087AF7;}"
    )

    widget.output_format_label = label
    widget.output_format_mode = combo
    combo.currentIndexChanged.connect(
        lambda *_: widget.update_export_controls(True)
    )

    # A prévia deve caber no espaço disponível sem alterar a proporção da fonte.
    video = getattr(widget, "video", None)
    if video is not None and hasattr(video, "setAspectRatioMode"):
        video.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)


def install_video_output_format_patch(editor_class) -> None:
    """Instala o seletor e conecta a escolha à estimativa e ao render final."""
    global _PATCHED
    if _PATCHED:
        return

    from monitor_noticias.video_editor.integrated_editor import advanced_editor as base

    original_resolve = base.resolve_target_dimensions
    original_bitrate_profile = base.bitrate_profile

    def resolve_target_dimensions_v128(first_info, resolution_choice):
        output_format, resolution = decode_resolution_choice(resolution_choice)
        if output_format == LANDSCAPE_16_9_FORMAT:
            return landscape_canvas_dimensions(first_info, resolution)
        return original_resolve(first_info, resolution)

    def bitrate_profile_v128(codec, resolution_choice, first_info=None):
        _output_format, resolution = decode_resolution_choice(resolution_choice)
        return original_bitrate_profile(codec, resolution, first_info)

    base.resolve_target_dimensions = resolve_target_dimensions_v128
    base.bitrate_profile = bitrate_profile_v128

    original_init = editor_class.__init__
    original_update_export = editor_class.update_export_controls
    original_export = editor_class.export_timeline
    original_update_controls = editor_class._update_controls

    def init_v128(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _install_output_selector(self)
        if hasattr(self, "output_format_mode"):
            self._update_controls()
            self.update_export_controls(False)

    def update_export_controls_v128(self, reset_to_recommended=True):
        if not hasattr(self, "output_format_mode"):
            return original_update_export(self, reset_to_recommended)

        result = _with_output_choice(
            self,
            original_update_export,
            reset_to_recommended,
        )
        if str(self.output_format_mode.currentData()) == LANDSCAPE_16_9_FORMAT:
            suffix = (
                " • Celular deitado 16:9 — conteúdo preservado, sem cortes; "
                "faixas aparecem quando a proporção de origem é diferente."
            )
            current = self.estimate_label.text()
            if suffix not in current:
                self.estimate_label.setText(current + suffix)
        return result

    def export_timeline_v128(self):
        if not hasattr(self, "output_format_mode"):
            return original_export(self)
        return _with_output_choice(self, original_export)

    def update_controls_v128(self):
        result = original_update_controls(self)
        combo = getattr(self, "output_format_mode", None)
        if combo is not None:
            worker = getattr(self, "export_worker", None)
            busy = bool(worker and worker.isRunning())
            combo.setEnabled(not busy)
        return result

    init_v128._central_video_output_format_v128 = True
    update_export_controls_v128._central_video_output_format_v128 = True
    export_timeline_v128._central_video_output_format_v128 = True
    update_controls_v128._central_video_output_format_v128 = True

    editor_class.__init__ = init_v128
    editor_class.update_export_controls = update_export_controls_v128
    editor_class.export_timeline = export_timeline_v128
    editor_class._update_controls = update_controls_v128
    _PATCHED = True
