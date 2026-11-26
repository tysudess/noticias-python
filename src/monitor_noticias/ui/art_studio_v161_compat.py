from __future__ import annotations

"""Compatibilidade de importação para a camada V161 do Estúdio de Artes.

A V161 utiliza `weakref.ref`, que pertence à biblioteca padrão do Python,
mas a versão publicada importa `weakref` de PySide6.QtCore. Esta correção
registra o módulo padrão no namespace QtCore antes da importação da V161,
sem alterar o comportamento das ferramentas ou os projetos .centralart.
"""

import weakref

from PySide6 import QtCore


def install_art_studio_v161_weakref_compatibility() -> None:
    """Expõe o módulo padrão `weakref` no QtCore para a importação legada V161."""
    if getattr(QtCore, "weakref", None) is not weakref:
        setattr(QtCore, "weakref", weakref)
