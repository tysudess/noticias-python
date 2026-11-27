from __future__ import annotations

"""Otimizações de abertura do Estúdio de Artes (V174–V177).

Preserva os recursos já implementados, mas evita trabalho visual duplicado
na primeira abertura: não reaplica folhas de estilo globais já instaladas,
limita atualizações repetidas do filtro V174, acelera o escalonamento das
camadas sem bloquear o event loop e adia a primeira miniatura até a página
estar visível.
"""

import logging
import time
import weakref
from functools import wraps

log = logging.getLogger(__name__)
_INSTALLED = False


def _install_v175_visual_refinements_without_theme_rebuild(page) -> None:
    """Mantém os refinamentos locais V175 sem reconstruir o stylesheet global.

    O tema completo já foi aplicado pela V161. Os wrappers de tema V175–V177
    foram registrados antes da criação da janela; portanto, seus seletores já
    fazem parte da folha aplicada ao editor. Reaplicá-la aqui só recalcula toda
    a árvore de widgets e aumenta o tempo de abertura.
    """
    from PySide6.QtWidgets import QLabel, QPushButton, QTabWidget
    from monitor_noticias.ui import art_studio_v175 as v175

    started = time.perf_counter()
    log.info("[ArtStudioPerf] V175: refinamentos locais iniciados.")
    try:
        left_tabs = getattr(page, "_v161_left_tabs", None)
        right_tabs = getattr(page, "_v161_inspector_tabs", None)
        for tabs in (left_tabs, right_tabs):
            if isinstance(tabs, QTabWidget):
                tabs.tabBar().setUsesScrollButtons(True)
                tabs.tabBar().setExpanding(False)
                tabs.tabBar().setElideMode(v175.Qt.TextElideMode.ElideRight)
                tabs.tabBar().setDrawBase(False)

        for heading in page.findChildren(QLabel, "artPanelTitle"):
            if heading.text().strip().upper() == "CAMADAS E OBJETOS":
                heading.setText("PROPRIEDADES")
            elif heading.text().strip().upper() == "ELEMENTOS":
                heading.setText("ELEMENTOS")

        for button in page.findChildren(QPushButton):
            button.setMinimumHeight(min(button.minimumHeight() or 30, 36))
            button.setStyleSheet(
                button.styleSheet()
                + "QPushButton {font-family:'Segoe UI';font-size:9px;padding:5px 9px;border-radius:7px;}"
            )

        for tabs_name in ("_v161_left_tabs", "_v161_inspector_tabs"):
            tabs = getattr(page, tabs_name, None)
            if isinstance(tabs, QTabWidget):
                tabs.tabBar().setMinimumHeight(30)
                tabs.tabBar().setMaximumHeight(34)
                tabs.tabBar().setStyleSheet(
                    tabs.tabBar().styleSheet()
                    + "QTabBar::tab {font-family:'Segoe UI';font-size:9px;padding:6px 8px;border-color:transparent;}"
                    + "QTabBar::tab:selected {border:1px solid #9AAEBD;border-bottom:2px solid #168E98;}"
                )

        for button_name in ("save_button", "export_button"):
            button = getattr(page, button_name, None)
            if isinstance(button, QPushButton):
                button.setProperty("gold", True)
                button.style().unpolish(button)
                button.style().polish(button)

        # O guard de tema usa esta marca para ignorar StyleChange redundante.
        page._v175_active_theme = v175._theme_name(page)
    finally:
        elapsed = time.perf_counter() - started
        log.info("[ArtStudioPerf] V175: refinamentos locais concluídos em %.3fs.", elapsed)
        if elapsed >= 0.5:
            log.warning("[ArtStudioPerf] V175 refinamentos locais demoraram %.3fs.", elapsed)



def _install_visual_refinements_without_theme_rebuild(page) -> None:
    """Executa apenas ajustes locais V176, sem reaplicar o tema completo."""
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    started = time.perf_counter()
    log.info("[ArtStudioPerf] V176: refinamentos locais iniciados.")
    try:
        toolbar = page.findChild(QFrame, "artStudioToolbar")
        if toolbar is not None:
            toolbar.setMinimumHeight(48)
            toolbar.setMaximumHeight(54)
            layout = toolbar.layout()
            if layout is not None:
                layout.setContentsMargins(8, 5, 8, 5)
                layout.setSpacing(5)

        for button in page.findChildren(QPushButton):
            if button.objectName() in {
                "artStudioApplyTransformV172",
                "artStudioDeleteLayersV170",
            }:
                button.setMinimumHeight(30)
                button.setMaximumHeight(34)

        workspace = page.findChild(QFrame, "artStudioWorkspace")
        if workspace is not None:
            workspace.setContentsMargins(5, 5, 5, 5)

        for heading in page.findChildren(QLabel, "artPanelTitle"):
            heading.setStyleSheet(
                "border-bottom:1px solid palette(mid); padding-bottom:7px;"
            )
    finally:
        elapsed = time.perf_counter() - started
        log.info("[ArtStudioPerf] V176: refinamentos locais concluídos em %.3fs.", elapsed)
        if elapsed >= 0.5:
            log.warning("[ArtStudioPerf] V176 refinamentos locais demoraram %.3fs.", elapsed)

def _guard_refresh_on_theme_change(refresh, theme_reader):
    """Executa refresh visual somente quando o tema efetivamente muda."""
    @wraps(refresh)
    def guarded(page_ref, *args, **kwargs):
        page = page_ref() if callable(page_ref) else None
        if page is None:
            return None
        try:
            theme = theme_reader(page)
            previous = getattr(page, "_art_studio_v174_compact_theme", None)
            if previous == theme:
                return None
            # Grava antes do refresh para que StyleChange provocado pelo próprio
            # refresh seja reconhecido como repetição e não entre em ciclo.
            page._art_studio_v174_compact_theme = theme
        except (RuntimeError, ReferenceError):
            return None
        except Exception:
            log.exception("[ArtStudioPerf] Não foi possível verificar a mudança de tema V174.")
            return None
        return refresh(page_ref, *args, **kwargs)

    return guarded


def _restyle_v177_tiles_only(page, theme_reader, restyle_tiles) -> None:
    """Atualiza a biblioteca V177 sem reaplicar o stylesheet de toda a página."""
    started = time.perf_counter()
    try:
        restyle_tiles(page)
        page._art_studio_v177_tiles_theme = theme_reader(page)
    finally:
        elapsed = time.perf_counter() - started
        log.info("[ArtStudioPerf] V177: atualização local da biblioteca em %.3fs.", elapsed)
        if elapsed >= 0.5:
            log.warning("[ArtStudioPerf] V177 biblioteca demorou %.3fs.", elapsed)


def _promote_active_load_timer_to_zero(window) -> None:
    """Remove os 15 ms artificiais entre camadas sem usar processEvents()."""
    timer = getattr(window, "_art_studio_load_timer", None)
    if timer is None:
        return
    try:
        if timer.isActive() and timer.isSingleShot() and timer.interval() > 0:
            timer.setInterval(0)
    except RuntimeError:
        log.debug("[ArtStudioPerf] Timer de abertura já foi destruído.")


def _make_fast_loader_callback(original):
    @wraps(original)
    def fast_loader(window, *args, **kwargs):
        result = original(window, *args, **kwargs)
        _promote_active_load_timer_to_zero(window)
        return result
    return fast_loader


def _make_thumbnail_renderer_deferred(original):
    @wraps(original)
    def render_after_open(page, page_index: int, *args, **kwargs):
        try:
            owner = page.window()
            if getattr(owner, "_art_studio_loading", False):
                log.debug("[ArtStudioPerf] Miniatura inicial adiada até a abertura do editor.")
                return None
        except RuntimeError:
            return None
        return original(page, page_index, *args, **kwargs)
    return render_after_open


def _schedule_first_thumbnail(page, renderer, delay_ms: int = 260) -> None:
    """Agenda uma única prévia leve depois que o editor já está visível."""
    if getattr(page, "_art_studio_first_thumbnail_scheduled", False):
        return
    page._art_studio_first_thumbnail_scheduled = True
    page_ref = weakref.ref(page)

    def render_first():
        target = page_ref()
        if target is None:
            return
        try:
            owner = target.window()
            if getattr(owner, "_art_studio_loading", False):
                return
            pages = getattr(target, "_v150_pages", []) or []
            index = int(getattr(target, "_v150_active_index", 0))
            if not (0 <= index < len(pages)):
                return
            entry = pages[index]
            page_id = str(entry.get("id") or index) if isinstance(entry, dict) else str(index)
            cache = getattr(target, "_v175_thumbnail_cache", {})
            if isinstance(cache, dict) and page_id in cache:
                return
            renderer(target, index)
        except RuntimeError:
            log.debug("[ArtStudioPerf] Página liberada antes da primeira miniatura.")
        except Exception:
            log.exception("[ArtStudioPerf] Falha na primeira miniatura adiada.")

    from PySide6.QtCore import QTimer
    QTimer.singleShot(max(0, int(delay_ms)), render_first)


def _timed(original, label: str):
    @wraps(original)
    def measured(page, *args, **kwargs):
        started = time.perf_counter()
        log.info("[ArtStudioPerf] INÍCIO %s.", label)
        try:
            return original(page, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - started
            log.info("[ArtStudioPerf] FIM %s em %.3fs.", label, elapsed)
            if elapsed >= 0.5:
                log.warning("[ArtStudioPerf] %s demorou %.3fs.", label, elapsed)
    return measured


def install_art_studio_v176_performance_patch() -> None:
    """Instala otimizações V174–V177 antes de aplicar a fila de recursos."""
    global _INSTALLED
    if _INSTALLED:
        return

    from monitor_noticias.ui import (
        art_studio_v174 as v174,
        art_studio_v175 as v175,
        art_studio_v176 as v176,
        art_studio_v177 as v177,
    )
    from monitor_noticias.ui import art_studio_integration as integration
    from monitor_noticias.ui.art_studio_v175_theme_guard import (
        install_art_studio_v175_theme_refresh_guard,
    )
    from monitor_noticias.ui import art_studio_v161

    # Interrompe a sequência StyleChange -> refresh -> novo StyleChange.
    install_art_studio_v175_theme_refresh_guard()

    if not getattr(v174, "_art_studio_perf_refresh_guard", False):
        v174._refresh_theme_styles = _guard_refresh_on_theme_change(
            v174._refresh_theme_styles, art_studio_v161._theme_id
        )
        v174._art_studio_perf_refresh_guard = True

    if not getattr(v175, "_art_studio_perf_visuals_installed", False):
        v175._install_visual_refinements = _install_v175_visual_refinements_without_theme_rebuild
        v175._art_studio_perf_visuals_installed = True

    if not getattr(v176, "_central_v176_performance_patch", False):
        v176._install_visual_refinements = _install_visual_refinements_without_theme_rebuild
        v176._install_page_overview = _timed(
            v176._install_page_overview, "V176 visão geral de páginas"
        )
        v176._install_inspector_summary = _timed(
            v176._install_inspector_summary, "V176 resumo contextual"
        )
        v176._central_v176_performance_patch = True

    if not getattr(v177, "_art_studio_perf_theme_installed", False):
        def apply_v177_theme_without_rebuild(page):
            _restyle_v177_tiles_only(
                page, v177._theme_name, v177._restyle_component_tiles
            )
        v177._apply_theme = apply_v177_theme_without_rebuild
        v177._art_studio_perf_theme_installed = True

    # As miniaturas não competem com a criação dos painéis. O primeiro render
    # acontece pouco depois de a página ser exibida pela primeira vez.
    if not getattr(v175, "_art_studio_perf_thumbnail_deferred", False):
        v175._render_page_thumbnail = _make_thumbnail_renderer_deferred(
            v175._render_page_thumbnail
        )
        v175._art_studio_perf_thumbnail_deferred = True

    # Os 15 ms serviam apenas para espaçar as camadas. Timer de 0 ms continua
    # devolvendo o controle ao Qt entre callbacks, mas elimina a espera fixa.
    if not getattr(integration, "_art_studio_perf_fast_loader", False):
        integration._advance_art_studio_loading = _make_fast_loader_callback(
            integration._advance_art_studio_loading
        )
        integration._start_art_studio_loading = _make_fast_loader_callback(
            integration._start_art_studio_loading
        )
        original_show = integration._show_art_studio

        @wraps(original_show)
        def show_and_warm_thumbnail(window, page):
            result = original_show(window, page)
            if getattr(window, "_art_studio_ready", False):
                _schedule_first_thumbnail(page, v175._render_page_thumbnail)
            return result

        integration._show_art_studio = show_and_warm_thumbnail
        integration._art_studio_perf_fast_loader = True

    _INSTALLED = True
    log.info(
        "[ArtStudioPerf] Otimizações instaladas: tema sem reconstrução, filtros idempotentes, "
        "fila sem espera artificial e miniatura após primeira exibição."
    )
