from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


def _find_layout_with_widget(
    layout: QLayout | None,
    widget: QWidget,
):
    if layout is None:
        return None

    for index in range(
        layout.count()
    ):
        item = layout.itemAt(
            index
        )
        child_widget = (
            item.widget()
        )

        if (
            child_widget
            is widget
        ):
            return layout

        child_layout = (
            item.layout()
        )

        if (
            child_layout
            is not None
        ):
            found = (
                _find_layout_with_widget(
                    child_layout,
                    widget,
                )
            )

            if (
                found
                is not None
            ):
                return found

        if (
            child_widget
            is not None
        ):
            owned_layout = (
                child_widget.layout()
            )

            if (
                owned_layout
                is not None
            ):
                found = (
                    _find_layout_with_widget(
                        owned_layout,
                        widget,
                    )
                )

                if (
                    found
                    is not None
                ):
                    return found

    return None


def _apply_shadow(
    widget: QWidget,
    blur: int = 24,
    offset_y: int = 5,
):
    shadow = (
        QGraphicsDropShadowEffect(
            widget
        )
    )

    shadow.setBlurRadius(
        blur
    )
    shadow.setOffset(
        0,
        offset_y,
    )
    shadow.setColor(
        QColor(
            33,
            86,
            146,
            28,
        )
    )

    widget.setGraphicsEffect(
        shadow
    )


def _style_chip(
    label: QLabel,
    kind: str,
):
    text = (
        label.text()
        .lower()
    )

    if kind == "proxy":
        ready = (
            "pronto" in text
            or "ativo" in text
        )

        bg = (
            "#EEF9F1"
            if ready
            else "#F7FBF8"
        )

        fg = (
            "#1E7D46"
            if ready
            else "#2E6C4A"
        )

        bd = "#BFE4CB"

    elif (
        kind
        == "automation"
    ):
        bg = "#F0FBF6"
        fg = "#15764B"
        bd = "#BEE4D1"

    elif (
        kind
        == "user"
    ):
        bg = "#F4F7FD"
        fg = "#113B71"
        bd = "#C8D9EE"

    else:
        bg = "#F8FBFE"
        fg = "#103566"
        bd = "#C8DAED"

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

    _apply_shadow(
        label,
        blur=18,
        offset_y=3,
    )


def _style_button(
    button: QPushButton,
    danger: bool = False,
):
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

    _apply_shadow(
        button,
        blur=18,
        offset_y=3,
    )


def _style_clock(
    clock: QWidget,
):
    if not hasattr(
        clock,
        "setStyleSheet",
    ):
        return

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

    _apply_shadow(
        clock,
        blur=22,
        offset_y=4,
    )


def _hide_search(
    window,
) -> None:
    """V65 — esconde SOMENTE a caixa de busca.

    V64 tentava esconder o parentWidget() quando o layout do pai tinha
    poucos itens. Na MainWindow real, o parent da busca é o QWidget
    ``content`` — o mesmo container que contém cabeçalho, QStackedWidget
    e rodapé.

    Resultado da V64:
        esconder busca => esconder toda a área principal.

    Regra V65:
        NUNCA esconder pai/avô/layout.
        Somente o QLineEdit da busca pode ser ocultado.
    """

    candidates: list[
        QLineEdit
    ] = []

    direct = getattr(
        window,
        "global_search",
        None,
    )

    if isinstance(
        direct,
        QLineEdit,
    ):
        candidates.append(
            direct
        )

    if not candidates:
        for edit in (
            window.findChildren(
                QLineEdit
            )
        ):
            placeholder = (
                edit.placeholderText()
                or ""
            ).lower()

            if (
                "buscar notícias"
                in placeholder
                or "buscar noticias"
                in placeholder
            ):
                candidates.append(
                    edit
                )

    for edit in candidates:
        # CRÍTICO:
        # não tocar no parentWidget().
        edit.hide()

        edit.setMinimumWidth(
            0
        )
        edit.setMaximumWidth(
            0
        )

        # O QSizePolicy.Ignored ajuda o QHBoxLayout do cabeçalho
        # a devolver imediatamente o espaço da busca aos demais
        # elementos, sem afetar o QWidget content.
        policy = edit.sizePolicy()
        policy.setHorizontalPolicy(
            QSizePolicy.Policy.Ignored
        )
        edit.setSizePolicy(
            policy
        )


def _apply(
    window,
):
    _hide_search(
        window
    )

    if (
        hasattr(
            window,
            "clock",
        )
        and window.clock
        is not None
    ):
        _style_clock(
            window.clock
        )

        header_layout = (
            _find_layout_with_widget(
                window
                .centralWidget()
                .layout(),
                window.clock,
            )
        )

        if (
            header_layout
            is not None
        ):
            try:
                header_layout.setSpacing(
                    14
                )
            except Exception:
                pass

    if hasattr(
        window,
        "_auth_user_label",
    ):
        _style_chip(
            window._auth_user_label,
            "user",
        )

    if hasattr(
        window,
        "_auth_account_button",
    ):
        _style_button(
            window._auth_account_button,
            danger=False,
        )

    if hasattr(
        window,
        "_auth_logout_button",
    ):
        _style_button(
            window._auth_logout_button,
            danger=True,
        )

    for label in (
        window.findChildren(
            QLabel
        )
    ):
        text = (
            label.text()
            or ""
        ).strip().lower()

        if not text:
            continue

        if (
            "proxy "
            in text
        ):
            _style_chip(
                label,
                "proxy",
            )

        elif (
            "automação ativa"
            in text
            or "automacao ativa"
            in text
        ):
            _style_chip(
                label,
                "automation",
            )


_INSTALLED_ON: set[
    int
] = set()


def install_header_refinement(
    window,
) -> None:
    key = id(
        window
    )

    if (
        key
        in _INSTALLED_ON
    ):
        return

    _INSTALLED_ON.add(
        key
    )

    QTimer.singleShot(
        0,
        lambda:
            _apply(
                window
            ),
    )
