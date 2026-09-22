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
        self.paths = (
            paths
            or AppPaths.discover()
        )

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

        # Correção da pré-visualização de alguns MP4 no Windows.
        # Estas variáveis precisam ser definidas ANTES de importar os módulos
        # Qt Multimedia usados pelo Editor de Vídeo.
        if sys.platform.startswith(
            "win"
        ):
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

        from PySide6.QtWidgets import (
            QApplication,
        )
        from monitor_noticias.app.composition import (
            AppContainer,
        )

        # Patches instalados antes de MainWindow importar as páginas.
        from monitor_noticias.ui.extractor_proxy_patch import (
            install_extractor_proxy_patch,
        )
        from monitor_noticias.ui.settings_proxy_toggle_patch import (
            install_settings_proxy_toggle_patch,
        )
        from monitor_noticias.ui.covers_web_proxy_patch import (
            install_covers_web_proxy_patch,
        )
        from monitor_noticias.ui.spreadsheet_shared_whatsapp_patch import (
            install_spreadsheet_shared_whatsapp_patch,
        )
        from monitor_noticias.ui.news_extractor_proxy_patch import (
            install_news_extractor_proxy_patch,
        )
        from monitor_noticias.ui.spreadsheet_keyboard_focus_patch import (
            install_spreadsheet_keyboard_focus_patch,
        )

        install_extractor_proxy_patch()
        install_settings_proxy_toggle_patch()
        install_covers_web_proxy_patch()
        install_spreadsheet_shared_whatsapp_patch()
        install_news_extractor_proxy_patch()
        install_spreadsheet_keyboard_focus_patch()

        from monitor_noticias.ui.main_window import (
            MainWindow,
        )
        from monitor_noticias.ui.screen_recorder_integration import (
            install_screen_recorder,
        )
        from monitor_noticias.ui.whatsapp_browser_integration import (
            install_whatsapp_browser,
        )

        qt_app = (
            QApplication.instance()
            or QApplication(sys.argv)
        )
        qt_app.setApplicationName(
            "Central Inteligente de Mídia"
        )
        qt_app.setApplicationDisplayName(
            "Central Inteligente de Mídia"
        )
        qt_app.setOrganizationName(
            "Central Inteligente de Mídia"
        )

        container = AppContainer.build(
            self.paths
        )
        window = MainWindow(
            controller=container.controller,
            paths=self.paths,
        )

        install_screen_recorder(
            window
        )
        install_whatsapp_browser(
            window
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
