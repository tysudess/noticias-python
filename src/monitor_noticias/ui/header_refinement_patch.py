from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


def _iter_child_widgets(root: QWidget):
    for child in root.findChildren(QWidget):
        yield child


def _find_layout_with_widget(layout: QLayout | None, widget: QWidget):
    if layout is None:
        return None

    for index in range(layout.count()):
        item = layout.itemAt(index)
        child_widget = item.widget()

        if child_widget is widget:
            return layout

        child_layout = item.layout()
        if child_layout is not None:
            found = _find_layout_with_widget(child_layout, widget)
            if found is not None:
                return found

        if child_widget is not None:
            owned_layout = child_widget.layout()
            if owned_layout is not None:
                found = _find_layout_with_widget(owned_layout, widget)
                if found is not None:
                    return found

    return None


def _apply_shadow(widget: QWidget, blur: int = 24, offset_y: int = 5):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(33, 86, 146, 28))
    widget.setGraphicsEffect(shadow)


def _style_chip(label: QLabel, kind: str):
    text = label.text().lower()

    if kind == 'proxy':
        bg = '#EEF9F1' if 'pronto' in text or 'ativo' in text else '#F7FBF8'
        fg = '#1E7D46' if 'pronto' in text or 'ativo' in text else '#2E6C4A'
        bd = '#BFE4CB'
    elif kind == 'automation':
        bg = '#F0FBF6'
        fg = '#15764B'
        bd = '#BEE4D1'
    elif kind == 'user':
        bg = '#F4F7FD'
        fg = '#113B71'
        bd = '#C8D9EE'
    else:
        bg = '#F8FBFE'
        fg = '#103566'
        bd = '#C8DAED'

    label.setStyleSheet(
        f"""
        QLabel {{
            background:{bg};
            color:{fg};
            border:1px solid {bd};
            border-radius:16px;
            padding:12px 16px;
            font-size:12px;
            font-weight:800;
        }}
        """
    )
    _apply_shadow(label, blur=18, offset_y=3)


def _style_button(button: QPushButton, danger: bool = False):
    if danger:
        button.setStyleSheet(
            """
            QPushButton {
                background:#FFFFFF;
                color:#B11E3A;
                border:1px solid #E7C1CA;
                border-radius:16px;
                padding:12px 18px;
                font-weight:800;
            }
            QPushButton:hover {
                background:#FFF7F8;
                border-color:#E1AAB7;
            }
            """
        )
    else:
        button.setStyleSheet(
            """
            QPushButton {
                background:#FFFFFF;
                color:#164A84;
                border:1px solid #C8DAED;
                border-radius:16px;
                padding:12px 18px;
                font-weight:800;
            }
            QPushButton:hover {
                background:#F7FBFF;
                border-color:#B5D0EB;
            }
            """
        )
    _apply_shadow(button, blur=18, offset_y=3)


def _style_clock(clock: QWidget):
    if hasattr(clock, 'setStyleSheet'):
        clock.setStyleSheet(
            """
            QLabel {
                background:#F8FBFF;
                color:#0F3365;
                border:1px solid #C7D9EC;
                border-radius:18px;
                padding:12px 18px;
                font-size:15px;
                font-weight:800;
            }
            """
        )
        _apply_shadow(clock, blur=22, offset_y=4)


def _hide_search(window):
    candidates = []
    for edit in window.findChildren(QLineEdit):
        placeholder = (edit.placeholderText() or '').lower()
        if 'buscar notícias' in placeholder or 'buscar noticias' in placeholder:
            candidates.append(edit)

    for edit in candidates:
        target = edit
        parent = edit.parentWidget()
        if parent is not None and parent.layout() is not None and parent.layout().count() <= 3:
            target = parent
        target.hide()
        target.setMaximumWidth(0)
        target.setMinimumWidth(0)


def _apply(window):
    _hide_search(window)

    if hasattr(window, 'clock') and window.clock is not None:
        _style_clock(window.clock)

        header_layout = _find_layout_with_widget(
            window.centralWidget().layout(),
            window.clock,
        )

        if header_layout is not None:
            try:
                header_layout.setSpacing(14)
            except Exception:
                pass

    if hasattr(window, '_auth_user_label'):
        _style_chip(window._auth_user_label, 'user')

    if hasattr(window, '_auth_account_button'):
        _style_button(window._auth_account_button, danger=False)

    if hasattr(window, '_auth_logout_button'):
        _style_button(window._auth_logout_button, danger=True)

    for label in window.findChildren(QLabel):
        text = (label.text() or '').strip().lower()
        if not text:
            continue
        if 'proxy ' in text:
            _style_chip(label, 'proxy')
        elif 'automação ativa' in text or 'automacao ativa' in text:
            _style_chip(label, 'automation')


_INSTALLED_ON = set()


def install_header_refinement(window):
    key = id(window)
    if key in _INSTALLED_ON:
        return
    _INSTALLED_ON.add(key)
    QTimer.singleShot(0, lambda: _apply(window))
