from __future__ import annotations

import os
from pathlib import Path
import threading

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.extractor import (
    ExtractorEngine,
    ExtractorPortableStateStore,
    GloboplaySessionStore,
    YtDlpUpdater,
)
from monitor_noticias.networking.proxy import ProxySettings
from monitor_noticias.platform.current import is_linux
from monitor_noticias.platform.processes import HiddenProcessRunner
from monitor_noticias.ui import extractor_page as extractor_page_module
from monitor_noticias.ui.news_extractor_page import NewsExtractorPage


_INSTALLED = False


def _paths_for(
    app_root: Path,
) -> AppPaths:
    return AppPaths.for_app_root(
        Path(app_root)
    )


def _patch_state_store() -> None:
    original = ExtractorPortableStateStore.__init__

    if getattr(
        original,
        "_central_linux_paths",
        False,
    ):
        return

    def patched(
        self,
        app_root: Path,
    ) -> None:
        paths = _paths_for(
            app_root
        )
        original(
            self,
            Path(
                paths.state_root
            ),
        )

    patched._central_linux_paths = True
    ExtractorPortableStateStore.__init__ = patched


def _patch_globoplay_session_store() -> None:
    original = GloboplaySessionStore.__init__

    if getattr(
        original,
        "_central_linux_paths",
        False,
    ):
        return

    def patched(
        self,
        app_root: Path,
    ) -> None:
        paths = _paths_for(
            app_root
        )

        if not is_linux():
            original(
                self,
                Path(
                    paths.state_root
                ),
            )
            return

        from monitor_noticias.platform.credentials import (
            LinuxKeyringTextStore,
        )

        self.session_dir = (
            paths.data
            / "extractor"
        )
        self.session_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.encrypted_file = (
            self.session_dir
            / "globoplay.session.keyring"
        )

        self.store = LinuxKeyringTextStore(
            service_name="CentralInteligenteDeMidia",
            account_name="globoplay-session",
        )

    patched._central_linux_paths = True
    GloboplaySessionStore.__init__ = patched


def _patch_extractor_engine() -> None:
    original = ExtractorEngine.__init__

    if getattr(
        original,
        "_central_linux_paths",
        False,
    ):
        return

    def patched(
        self,
        app_root: Path,
        runner=None,
    ) -> None:
        if not is_linux():
            original(
                self,
                app_root,
                runner,
            )
            return

        paths = _paths_for(
            app_root
        )

        self.app_root = (
            paths.root
        )
        self.state_root = Path(
            paths.state_root
        )
        self.bin_dir = (
            paths.bin
        )
        self.videos_dir = (
            paths.videos
        )
        self.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.yt_dlp = (
            paths.runtime_binary(
                "yt-dlp"
            )
        )
        self.yt_dlp_stable = (
            paths.runtime_binary(
                "yt-dlp-stable"
            )
        )
        self.ffmpeg = (
            paths.runtime_binary(
                "ffmpeg"
            )
        )
        self.ffprobe = (
            paths.runtime_binary(
                "ffprobe"
            )
        )
        self.deno = (
            paths.runtime_binary(
                "deno"
            )
        )

        self.runner = (
            runner
            or HiddenProcessRunner()
        )

        self.session_store = (
            GloboplaySessionStore(
                paths.root
            )
        )

        self._lock = threading.Lock()
        self._active = None
        self._cancelled = False

    patched._central_linux_paths = True
    ExtractorEngine.__init__ = patched


def _patch_extractor_page() -> None:
    cls = (
        extractor_page_module
        .ExtractorPage
    )

    original_init = cls.__init__
    original_refresh_session = (
        cls._refresh_session
    )

    if getattr(
        original_init,
        "_central_linux_paths",
        False,
    ):
        return

    def patched_init(
        self,
        app_root: Path,
    ) -> None:
        original_init(
            self,
            app_root,
        )

        paths = _paths_for(
            app_root
        )
        self._runtime_paths = (
            paths
        )
        self._download_log = (
            paths.logs
            / "extractor-video.log"
        )

    def patched_refresh_session(
        self,
    ) -> None:
        if not is_linux():
            original_refresh_session(
                self
            )
            return

        saved = (
            self.session_store
            .has_saved_session()
        )

        self.session_status.setText(
            (
                "Sessão protegida salva "
                "no cofre seguro do Ubuntu."
            )
            if saved
            else (
                "Nenhuma sessão "
                "Globoplay salva."
            )
        )

        self.delete_session_button.setEnabled(
            saved
        )

    patched_init._central_linux_paths = True
    patched_refresh_session._central_linux_paths = True

    cls.__init__ = patched_init
    cls._refresh_session = (
        patched_refresh_session
    )


def _patch_news_extractor_page() -> None:
    original = NewsExtractorPage.__init__

    if getattr(
        original,
        "_central_linux_paths",
        False,
    ):
        return

    def patched(
        self,
        app_root: Path,
    ) -> None:
        original(
            self,
            app_root,
        )

        if not is_linux():
            return

        paths = _paths_for(
            app_root
        )

        self.bundle_root = (
            paths.root
        )

        self.app_root = Path(
            paths.state_root
        )

        self.exe = (
            paths.root
            / "tools"
            / "news_extractor"
            / "ExtratorMateriasPortable-V1.25.19"
        )

    patched._central_linux_paths = True
    NewsExtractorPage.__init__ = patched


def _patch_extractor_proxy_settings() -> None:
    from monitor_noticias.ui import (
        extractor_proxy_patch,
    )

    def settings_for(
        app_root: Path,
    ) -> ProxySettings:
        paths = _paths_for(
            app_root
        )

        prefs = SharedPreferences(
            paths.data
            / "prefs"
            / "monitor_prefs.properties"
        )

        return ProxySettings(
            prefs,
            data_dir=paths.data,
        )

    extractor_proxy_patch._settings_for = (
        settings_for
    )


def _patch_ytdlp_updater() -> None:
    original_init = (
        YtDlpUpdater.__init__
    )
    original_validate = (
        YtDlpUpdater._validate
    )
    original_update = (
        YtDlpUpdater.update
    )

    if getattr(
        original_init,
        "_central_linux_paths",
        False,
    ):
        return

    def patched_init(
        self,
        engine: ExtractorEngine,
    ) -> None:
        original_init(
            self,
            engine,
        )

        if not is_linux():
            return

        paths = _paths_for(
            engine.app_root
        )

        self.target = (
            paths.writable_binary(
                "yt-dlp"
            )
        )

        # Standalone Linux executable. Não depende do Python do sistema.
        self.URL = (
            "https://github.com/yt-dlp/yt-dlp/"
            "releases/latest/download/yt-dlp_linux"
        )

    def patched_validate(
        self,
        executable: Path,
    ) -> str:
        path = Path(
            executable
        )

        if (
            is_linux()
            and path.is_file()
        ):
            try:
                path.chmod(
                    path.stat().st_mode
                    | 0o111
                )
            except OSError:
                pass

        return original_validate(
            self,
            path,
        )

    def patched_update(
        self,
        progress=lambda _message: None,
    ):
        result = original_update(
            self,
            progress,
        )

        if (
            is_linux()
            and result.success
        ):
            try:
                self.target.chmod(
                    self.target.stat().st_mode
                    | 0o111
                )
            except OSError:
                pass

            self.engine.yt_dlp = (
                self.target
            )

        return result

    patched_init._central_linux_paths = True
    patched_validate._central_linux_paths = True
    patched_update._central_linux_paths = True

    YtDlpUpdater.__init__ = (
        patched_init
    )
    YtDlpUpdater._validate = (
        patched_validate
    )
    YtDlpUpdater.update = (
        patched_update
    )


def install_cross_platform_runtime_patch() -> None:
    global _INSTALLED

    if _INSTALLED:
        return

    _patch_state_store()
    _patch_globoplay_session_store()
    _patch_extractor_engine()
    _patch_extractor_page()
    _patch_news_extractor_page()
    _patch_extractor_proxy_settings()
    _patch_ytdlp_updater()

    _INSTALLED = True
