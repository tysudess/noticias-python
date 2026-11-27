from __future__ import annotations

import gc
import weakref
from types import SimpleNamespace

from monitor_noticias.ui.art_studio_v175_theme_guard import (
    install_art_studio_v175_theme_refresh_guard,
)


class _Page:
    def __init__(self, theme: str):
        self.theme = theme
        self._v175_active_theme = theme


def _fake_v175(apply_callback):
    return SimpleNamespace(
        _apply_theme_from_ref=apply_callback,
        _theme_name=lambda page: page.theme,
        _central_theme_refresh_guard_installed=False,
    )


def test_redundant_forced_stylechange_does_not_reapply_the_same_theme():
    calls = []

    def apply_theme(page_ref, *, force=False):
        page = page_ref()
        calls.append((page, force))

    v175 = _fake_v175(apply_theme)
    page = _Page("escuro")
    ref = weakref.ref(page)

    assert install_art_studio_v175_theme_refresh_guard(v175) is True
    # O filtro V175 antigo envia force=True para cada StyleChange.
    v175._apply_theme_from_ref(ref, force=True)
    v175._apply_theme_from_ref(ref, force=True)

    assert calls == []


def test_real_theme_change_is_applied_once_even_with_queued_stylechange_events():
    calls = []

    def apply_theme(page_ref, *, force=False):
        page = page_ref()
        calls.append(force)
        # Simula o resultado de page.setStyleSheet() e a atualização do cache.
        page._v175_active_theme = page.theme

    v175 = _fake_v175(apply_theme)
    page = _Page("escuro")
    ref = weakref.ref(page)
    install_art_studio_v175_theme_refresh_guard(v175)

    # A aplicação global do tema muda o identificador claro/escuro.
    page.theme = "claro"
    v175._apply_theme_from_ref(ref, force=True)
    # Eventos StyleChange gerados pela própria folha voltam a chamar o filtro.
    v175._apply_theme_from_ref(ref, force=True)
    v175._apply_theme_from_ref(ref, force=True)

    assert calls == [False]
    assert page._v175_active_theme == "claro"


def test_destroyed_page_reference_is_ignored_safely():
    calls = []
    v175 = _fake_v175(lambda *_args, **_kwargs: calls.append("called"))
    page = _Page("escuro")
    ref = weakref.ref(page)
    install_art_studio_v175_theme_refresh_guard(v175)

    del page
    gc.collect()
    assert ref() is None
    assert v175._apply_theme_from_ref(ref, force=True) is None
    assert calls == []


def test_guard_installation_is_idempotent():
    v175 = _fake_v175(lambda *_args, **_kwargs: None)
    assert install_art_studio_v175_theme_refresh_guard(v175) is True
    first_wrapper = v175._apply_theme_from_ref
    assert install_art_studio_v175_theme_refresh_guard(v175) is False
    assert v175._apply_theme_from_ref is first_wrapper


def test_v176_performance_installer_activates_v175_guard_before_layers():
    from pathlib import Path
    import ast

    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src/monitor_noticias/ui/art_studio_v176_performance_patch.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    installer = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "install_art_studio_v176_performance_patch"
    )
    calls = [
        node.func.id for node in ast.walk(installer)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "install_art_studio_v175_theme_refresh_guard" in calls
