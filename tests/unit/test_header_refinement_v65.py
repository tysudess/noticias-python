from __future__ import annotations

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.ui.header_refinement_patch import (
    _hide_search,
)


def test_hide_search_never_hides_main_content():
    app = (
        QApplication.instance()
        or QApplication([])
    )

    window = QMainWindow()

    root = QWidget()
    window.setCentralWidget(
        root
    )

    outer = QHBoxLayout(
        root
    )

    sidebar = QWidget()
    outer.addWidget(
        sidebar
    )

    content = QWidget()
    outer.addWidget(
        content
    )

    content_layout = (
        QVBoxLayout(
            content
        )
    )

    header = QHBoxLayout()

    window.global_search = (
        QLineEdit()
    )

    window.global_search.setPlaceholderText(
        "Buscar notícias, vídeos, demandas ou fontes..."
    )

    header.addWidget(
        window.global_search
    )

    content_layout.addLayout(
        header
    )

    stack = QStackedWidget()
    stack.addWidget(
        QLabel(
            "Conteúdo principal"
        )
    )

    content_layout.addWidget(
        stack
    )

    footer = QLabel(
        "Rodapé"
    )
    content_layout.addWidget(
        footer
    )

    # Exatamente o cenário que quebrava na V64:
    # o parent da busca possui um layout com 3 itens.
    assert (
        window.global_search
        .parentWidget()
        is content
    )

    assert (
        content.layout()
        .count()
        == 3
    )

    _hide_search(
        window
    )

    assert (
        window.global_search
        .isHidden()
    )

    # Regressão crítica V64:
    # estes widgets NÃO podem ser escondidos.
    assert not content.isHidden()
    assert not stack.isHidden()
    assert not footer.isHidden()

    window.close()
    app.processEvents()
