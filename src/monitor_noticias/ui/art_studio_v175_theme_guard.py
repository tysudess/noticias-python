from __future__ import annotations

"""Evita o ciclo de StyleChange causado pelo refresh forçado do tema V175.

O filtro V175 agenda _apply_theme_from_ref(..., force=True) para todo
QEvent.StyleChange. Como setStyleSheet() também gera StyleChange, forçar a
mesma folha novamente cria uma cadeia contínua de QTimer.singleShot(0).
Este guard só permite a reaplicação quando o identificador do tema realmente
mudou; após a primeira aplicação, eventos subsequentes tornam-se no-op.
"""

import logging
from functools import wraps

log = logging.getLogger(__name__)


def _guard_callback(module):
    original = getattr(module, "_apply_theme_from_ref", None)
    theme_reader = getattr(module, "_theme_name", None)
    if not callable(original) or not callable(theme_reader):
        raise RuntimeError("A V175 não expõe os callbacks esperados para o guard de tema.")

    @wraps(original)
    def apply_theme_only_when_changed(page_ref, *, force: bool = False):
        page = page_ref()
        if page is None:
            return None

        try:
            current_theme = theme_reader(page)
            applied_theme = getattr(page, "_v175_active_theme", None)
        except (RuntimeError, ReferenceError):
            # O wrapper Qt pode continuar referenciado em Python após deleteLater().
            return None
        except Exception:
            log.exception("[ArtStudioV175] Não foi possível identificar o tema atual.")
            return None

        # A flag force=True do filtro antigo ignorava o cache e causava o loop.
        # Só encaminhamos a chamada quando houve uma troca real claro/escuro.
        if applied_theme == current_theme:
            log.debug(
                "[ArtStudioV175] Refresh redundante ignorado (tema %s já aplicado).",
                current_theme,
            )
            return None

        return original(page_ref, force=False)

    return apply_theme_only_when_changed


def install_art_studio_v175_theme_refresh_guard(module=None) -> bool:
    """Instala o guard uma única vez; aceita módulo falso nos testes unitários."""
    if module is None:
        from monitor_noticias.ui import art_studio_v175 as module

    if getattr(module, "_central_theme_refresh_guard_installed", False):
        return False

    module._apply_theme_from_ref = _guard_callback(module)
    module._central_theme_refresh_guard_installed = True
    log.info(
        "[ArtStudioV175] Proteção instalada: StyleChange não reaplica tema sem mudança real."
    )
    return True
