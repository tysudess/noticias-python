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

        from monitor_noticias.platform.tls import (
            install_system_trust_store,
        )

        tls_ok, tls_status = (
            install_system_trust_store()
        )

        if tls_ok:
            log.info(
                "TLS: %s",
                tls_status,
            )
        else:
            log.warning(
                "TLS: %s",
                tls_status,
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

        from PySide6.QtWidgets import (
            QApplication,
            QDialog,
        )
        from monitor_noticias.app.composition import AppContainer

        from monitor_noticias.ui.extractor_proxy_patch import (
            install_extractor_proxy_patch,
        )
        from monitor_noticias.ui.settings_credentials_patch import (
            install_settings_credentials_patch,
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
        from monitor_noticias.ui.news_extractor_speed_patch import (
            install_news_extractor_speed_patch,
        )
        from monitor_noticias.ui.cross_platform_runtime_patch import (
            install_cross_platform_runtime_patch,
        )
        from monitor_noticias.ui.pdf_export_quality_fix import (
            install_pdf_export_quality_fix,
        )

        install_extractor_proxy_patch()
        install_settings_credentials_patch()
        install_settings_proxy_toggle_patch()

        install_covers_web_proxy_patch()
        install_covers_browser_capture_patch()
        install_valor_gmail_only_patch()

        install_news_extractor_proxy_patch()
        install_news_direct_link_patch()
        install_news_extractor_speed_patch()
        install_cross_platform_runtime_patch()
        install_pdf_export_quality_fix()

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
        from monitor_noticias.ui.app_icon_loader import load_app_icon
        from monitor_noticias.ui.linux_boot_patch import (
            install_linux_boot_patch,
        )
        from monitor_noticias.ui.screen_recorder_linux_patch import (
            install_linux_screen_recorder_patch,
        )
        from monitor_noticias.ui.header_refinement_patch import (
            install_header_refinement,
        )
        from monitor_noticias.ui.sources_bahia_patch import (
            install_sources_bahia_patch,
        )

        install_removed_integrations_guard(MainWindow)
        install_linux_boot_patch(MainWindow)
        install_linux_screen_recorder_patch()

        qt_app = (
            QApplication.instance()
            or QApplication(
                sys.argv
            )
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

        app_icon = load_app_icon()

        if not app_icon.isNull():
            qt_app.setWindowIcon(
                app_icon
            )

        auth_runtime = None
        auth_session = None

        from monitor_noticias.auth.config import (
            auth_server_configured,
        )

        if auth_server_configured():
            from monitor_noticias.auth.runtime import (
                AuthRuntime,
            )
            from monitor_noticias.ui.login_dialog import (
                LoginDialog,
            )

            auth_runtime = AuthRuntime(
                self.paths
            )

            login = LoginDialog(
                auth_runtime,
                app_icon=app_icon,
            )

            result = login.exec()

            if (
                result
                != QDialog.DialogCode.Accepted
                or login.session is None
            ):
                log.info(
                    "Acesso não autenticado. Aplicação encerrada."
                )
                return 0

            auth_session = (
                login.session
            )

        else:
            log.warning(
                "Servidor de autenticação ainda não configurado. "
                "Login obrigatório permanece desativado."
            )

        container = AppContainer.build(
            self.paths
        )

        window = MainWindow(
            controller=container.controller,
            paths=self.paths,
        )

        if not app_icon.isNull():
            window.setWindowIcon(
                app_icon
            )

        remove_legacy_pages(
            window
        )
        install_screen_recorder(
            window
        )
        install_demands_news_actions(
            window
        )
        install_home_dashboard_patch(
            window
        )
        install_visual_refinement_patch(
            qt_app,
            window,
        )
        install_sources_bahia_patch(
            window
        )

        if (
            auth_runtime is not None
            and auth_session is not None
        ):
            from monitor_noticias.ui.auth_window_integration import (
                install_authenticated_window,
            )

            install_authenticated_window(
                window,
                auth_runtime,
                auth_session,
            )

        install_header_refinement(window)

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
