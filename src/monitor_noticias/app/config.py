from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    """Infraestrutura vazia de configuração.

    Chaves reais não são declaradas aqui até serem migradas com evidência do Kotlin.
    """

    pass
