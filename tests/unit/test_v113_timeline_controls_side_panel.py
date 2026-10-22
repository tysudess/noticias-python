from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget
import pytest

from monitor_noticias.ui.video_preview_layout_patch import install_video_preview_layout_patch
from monitor_noticias.ui.video_timeline_side_controls_patch import (
    install_video_timeline_side_controls_patch,
)
from monitor_noticias.ui.video_editor_reference_page import ReferenceAdvancedVideoEditorWidget


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def _is_descendant(widget, ancestor):
    current = widget
    while current is not None:
        if current is ancestor:
            return True
        current = current.parentWidget()
    return False


def test_timeline_controls_are_relocated_to_right_side_panel(app, tmp_path):
    install_video_preview_layout_patch()
    install_video_timeline_side_controls_patch()
    widget = ReferenceAdvancedVideoEditorWidget(
        tmp_path / "Videos", tmp_path / "ffmpeg", tmp_path / "ffprobe"
    )
    panel = widget._timeline_side_controls_panel
    quick_column = widget.btn_mark_start.parentWidget()

    assert panel.parentWidget() is quick_column
    assert quick_column.layout().indexOf(panel) >= 0
    for control in [
        *widget.nudge_buttons,
        widget.btn_duplicate,
        widget.btn_up,
        widget.btn_down,
        widget.btn_cut,
        widget.btn_remove,
    ]:
        assert _is_descendant(control, panel)

    widget.close()
    widget.deleteLater()


def test_controls_are_not_duplicated_and_timeline_remains(app, tmp_path):
    install_video_preview_layout_patch()
    install_video_timeline_side_controls_patch()
    widget = ReferenceAdvancedVideoEditorWidget(
        tmp_path / "Videos", tmp_path / "ffmpeg", tmp_path / "ffprobe"
    )
    controls = [
        *widget.nudge_buttons,
        widget.btn_duplicate,
        widget.btn_up,
        widget.btn_down,
        widget.btn_cut,
        widget.btn_remove,
    ]
    buttons = widget.findChildren(type(widget.btn_cut))
    for control in controls:
        assert buttons.count(control) == 1
    assert widget.timeline is not None
    assert widget.timeline_scroll is not None

    widget.close()
    widget.deleteLater()
