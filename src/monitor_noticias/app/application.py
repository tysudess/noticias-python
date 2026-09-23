from __future__ import annotations

import logging
import os
import sys

from .exceptions import install_global_exception_hooks
from .logging_setup import configure_logging
from .paths import AppPaths


class Application:
    def __init__(
        self,
        paths: AppPaths | None = None,
    ) -> None:
        self.paths = paths or AppPaths.discover()

    def run(self) -> int:
        self.paths.ensure_runtime_dirs()
        configure_logging(self.paths)
        install_global_exception_hooks()

        log = logging.getLogger(
            "monitor_noticias.application"
        )
        log.info(
            "Inicializando Central Inteligente de Mídia PySide6"
        )

        if sys.platform.startswith("win"):
            os.environ.setdefault(
                "QT_MEDIA_BACKEND",
                "ffmpeg",
            )
            os.environ.setdefault(
                "QT_FFMPEG_DECODING_HW_DEVICE_TYPES",
                ",",
            )
            os.environ.setdefault(
                "QT_DISABLE_HW_TEXTURES_CONVERSION",
                "1",
            )

        from PySide6.QtWidgets import QApplication
        from monitor_noticias.app.composition import AppContainer

        from monitor_noticias.ui.extractor_proxy_patch import (
            install_extractor_proxy_patch,
        )
        from monitor_noticias.ui.settings_proxy_toggle_patch import (
            install_settings_proxy_toggle_patch,
        )
        from monitor_noticias.ui.covers_web_proxy_patch import (
            install_covers_web_proxy_patch,
        )
        from monitor_noticias.ui.covers_frontpages_browser_capture_patch import (
            install_covers_browser_capture_patch,
        )
        from monitor_noticias.ui.covers_valor_gmail_only_patch import (
            install_valor_gmail_only_patch,
        )
        from monitor_noticias.ui.news_extractor_proxy_patch import (
            install_news_extractor_proxy_patch,
        )
        from monitor_noticias.ui.news_direct_link_patch import (
            install_news_direct_link_patch,
        )

        install_extractor_proxy_patch()
        install_settings_proxy_toggle_patch()

        # Capas:
        # V35 = Proxy Geral / fluxo base.
        # V42 = captura do navegador para o fallback web.
        # V43 = Valor Econômico usa exclusivamente Gmail.
        install_covers_web_proxy_patch()
        install_covers_browser_capture_patch()
        install_valor_gmail_only_patch()

        install_news_extractor_proxy_patch()
        install_news_direct_link_patch()

        from monitor_noticias.ui.main_window import MainWindow
        from monitor_noticias.ui.screen_recorder_integration import (
            install_screen_recorder,
        )
        from monitor_noticias.ui.demands_news_actions_integration import (
            install_demands_news_actions,
        )
        from monitor_noticias.ui.removed_integrations_guard import (
            install_removed_integrations_guard,
            remove_legacy_pages,
        )
        from monitor_noticias.ui.home_dashboard_patch import (
            install_home_dashboard_patch,
        )
        from monitor_noticias.ui.visual_refinement_patch import (
            install_visual_refinement_patch,
        )

        install_removed_integrations_guard(MainWindow)

        qt_app = QApplication.instance() or QApplication(sys.argv)
        qt_app.setApplicationName("Central Inteligente de Mídia")
        qt_app.setApplicationDisplayName("Central Inteligente de Mídia")
        qt_app.setOrganizationName("Central Inteligente de Mídia")

        container = AppContainer.build(self.paths)

        window = MainWindow(
            controller=container.controller,
            paths=self.paths,
        )

        remove_legacy_pages(window)
        install_screen_recorder(window)
        install_demands_news_actions(window)

        # V44 — ajustes visuais e de layout da Home.
        install_home_dashboard_patch(window)

        # V45 — refinamento visual global sem alterar funcionalidades.
        install_visual_refinement_patch(
            qt_app,
            window,
        )

        window.show()

        try:
            result = qt_app.exec()
        finally:
            container.close()

        log.info(
            "Aplicação encerrada com código %s",
            result,
        )
        return int(result)


def main() -> int:
    return Application().run()
