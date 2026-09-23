from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from monitor_noticias.app.paths import AppPaths
from monitor_noticias.platform.current import (
    is_appimage,
    is_linux,
    is_windows,
)


_INSTALLED = False


def runtime_platform_label() -> str:
    if is_windows():
        return "Windows Portable v4.0.2"

    if is_linux():
        if is_appimage():
            return "Ubuntu AppImage v4.0.2"

        return "Ubuntu/Linux v4.0.2"

    return "Multiplataforma v4.0.2"


def _install_main_window_identity(
    main_window_class,
) -> None:
    original_init = (
        main_window_class.__init__
    )
    original_tick = (
        main_window_class._tick
    )

    if getattr(
        original_init,
        "_central_linux_identity",
        False,
    ):
        return

    def apply_identity(
        window,
    ) -> None:
        label = (
            runtime_platform_label()
        )

        window.setWindowTitle(
            "Central Inteligente de Mídia - "
            + label
        )

        sidebar = getattr(
            window,
            "sidebar_status",
            None,
        )

        if sidebar is not None:
            sidebar.setText(
                label
            )

    def patched_init(
        self,
        *args,
        **kwargs,
    ):
        original_init(
            self,
            *args,
            **kwargs,
        )
        apply_identity(
            self
        )

    def patched_tick(
        self,
    ):
        result = original_tick(
            self
        )
        apply_identity(
            self
        )
        return result

    patched_init._central_linux_identity = True
    patched_tick._central_linux_identity = True

    main_window_class.__init__ = patched_init
    main_window_class._tick = patched_tick


def _install_settings_identity() -> None:
    from monitor_noticias.ui.settings_reference_page import (
        ReferenceSettingsPage,
    )

    original_init = (
        ReferenceSettingsPage.__init__
    )

    if getattr(
        original_init,
        "_central_linux_identity",
        False,
    ):
        return

    def patched_init(
        self,
        controller,
    ) -> None:
        original_init(
            self,
            controller,
        )

        if not is_linux():
            return

        for label in self.findChildren(
            QLabel
        ):
            text = (
                label.text()
                or ""
            ).strip()

            if (
                text
                == "Iniciar com o Windows"
            ):
                label.setText(
                    "Iniciar com o sistema"
                )

    patched_init._central_linux_identity = True
    ReferenceSettingsPage.__init__ = patched_init


def _install_reference_video_editor_paths() -> None:
    from monitor_noticias.ui.video_editor_reference_page import (
        ReferenceAdvancedVideoEditorWidget,
        ReferenceVideoEditorPage,
    )

    original_init = (
        ReferenceVideoEditorPage.__init__
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
        if not is_linux():
            original_init(
                self,
                app_root,
            )
            return

        QWidget.__init__(
            self
        )

        self.paths = (
            AppPaths.for_app_root(
                Path(app_root)
            )
        )

        self.app_root = (
            self.paths.root
        )
        self.videos_dir = (
            self.paths.videos
        )
        self.bin_dir = (
            self.paths.bin
        )

        self.videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ffmpeg = (
            self.paths
            .runtime_binary(
                "ffmpeg"
            )
        )
        self.ffprobe = (
            self.paths
            .runtime_binary(
                "ffprobe"
            )
        )

        root = QVBoxLayout(
            self
        )
        root.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root.setSpacing(0)

        self.scroll = (
            QScrollArea(
                self
            )
        )
        self.scroll.setObjectName(
            "referenceVideoEditorScroll"
        )
        self.scroll.setWidgetResizable(
            True
        )
        self.scroll.setFrameShape(
            QScrollArea.Shape.NoFrame
        )
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.editor = (
            ReferenceAdvancedVideoEditorWidget(
                self.videos_dir,
                self.ffmpeg,
                self.ffprobe,
                self.scroll,
            )
        )

        self.editor.setMinimumWidth(
            1000
        )
        self.editor.setMinimumHeight(
            790
        )

        self.scroll.setWidget(
            self.editor
        )
        root.addWidget(
            self.scroll,
            1,
        )

        self.setStyleSheet(
            """
            QScrollArea#referenceVideoEditorScroll {
                background:#F4F9FF;
                border:0;
            }

            QScrollArea#referenceVideoEditorScroll
            > QWidget > QWidget {
                background:#F4F9FF;
            }

            QScrollBar:vertical {
                background:#EDF4FC;
                width:10px;
                border-radius:5px;
            }

            QScrollBar::handle:vertical {
                background:#8BB9E8;
                min-height:50px;
                border-radius:5px;
            }

            QScrollBar:horizontal {
                background:#EDF4FC;
                height:10px;
                border-radius:5px;
            }

            QScrollBar::handle:horizontal {
                background:#8BB9E8;
                min-width:50px;
                border-radius:5px;
            }

            QScrollBar::add-line,
            QScrollBar::sub-line {
                width:0;
                height:0;
            }
            """
        )

    patched_init._central_linux_paths = True
    ReferenceVideoEditorPage.__init__ = patched_init


def _install_pdf_editor_paths() -> None:
    from monitor_noticias.ui.pdf_editor_reference_page import (
        ReferencePdfEditorPage,
    )

    original_init = (
        ReferencePdfEditorPage.__init__
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
        if not is_linux():
            original_init(
                self,
                app_root,
            )
            return

        paths = (
            AppPaths.for_app_root(
                Path(app_root)
            )
        )

        state_root = Path(
            paths.state_root
        )

        # PdfEditorModel espera recursos e dados sob a mesma raiz.
        # Copiamos somente os dois assets pequenos necessários para a área
        # gravável, preservando o restante dentro do AppImage.
        state_resources = (
            state_root
            / "resources"
        )
        state_resources.mkdir(
            parents=True,
            exist_ok=True,
        )

        for filename in (
            "pdf-default-cover.png",
            "pdf-default-cover.b64",
        ):
            source = (
                paths.resources
                / filename
            )
            target = (
                state_resources
                / filename
            )

            if (
                source.is_file()
                and (
                    not target.is_file()
                    or source.stat().st_size
                    != target.stat().st_size
                )
            ):
                shutil.copy2(
                    source,
                    target,
                )

        original_init(
            self,
            state_root,
        )

    patched_init._central_linux_paths = True
    ReferencePdfEditorPage.__init__ = patched_init


def _install_screen_recorder_boot_paths() -> None:
    from monitor_noticias.ui.screen_recorder_page import (
        ScreenRecorderPage,
    )

    original_init = (
        ScreenRecorderPage.__init__
    )
    original_toggle = (
        ScreenRecorderPage._toggle_module
    )
    original_probe = (
        ScreenRecorderPage._probe_duration
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
        parent=None,
    ) -> None:
        if not is_linux():
            original_init(
                self,
                app_root,
                parent,
            )
            return

        paths = (
            AppPaths.for_app_root(
                Path(app_root)
            )
        )

        # A implementação Windows cria os diretórios usando app_root.
        # Passamos a raiz gravável para impedir qualquer escrita no AppImage.
        original_init(
            self,
            Path(
                paths.state_root
            ),
            parent,
        )

        self._bundle_root = (
            paths.root
        )
        self._runtime_paths = (
            paths
        )
        self.ffmpeg = (
            paths.runtime_binary(
                "ffmpeg"
            )
        )

        for label in self.findChildren(
            QLabel
        ):
            text = (
                label.text()
                or ""
            )

            if "tela do Windows" in text:
                label.setText(
                    text.replace(
                        "tela do Windows",
                        "tela no Ubuntu",
                    )
                )

            if "WASAPI" in text:
                label.setText(
                    text.replace(
                        "WASAPI",
                        "áudio do sistema",
                    )
                )

    def patched_toggle(
        self,
        enabled: bool,
    ) -> None:
        if not is_linux():
            original_toggle(
                self,
                enabled,
            )
            return

        if not enabled:
            original_toggle(
                self,
                False,
            )
            return

        # O backend Windows é gdigrab + WASAPI. Não permitimos iniciar esse
        # fluxo no Linux. A próxima etapa adicionará X11/PipeWire/Wayland.
        self.power_button.blockSignals(
            True
        )
        self.power_button.setChecked(
            False
        )
        self.power_button.blockSignals(
            False
        )

        self._module_enabled = False
        self.power_button.setText(
            "⏻  LIGAR"
        )

        self._apply_state(
            self.OFF,
            "Backend de gravação Ubuntu ainda não ativado. "
            "O suporte X11/PipeWire/Wayland será instalado "
            "na próxima etapa.",
        )

        QMessageBox.information(
            self,
            "Gravador de Tela no Ubuntu",
            "A interface já está compatível com o AppImage. "
            "O motor de captura Linux será conectado na próxima etapa.",
        )

    def patched_probe(
        self,
        path: Path,
    ) -> float:
        if not is_linux():
            return original_probe(
                self,
                path,
            )

        ffprobe = (
            getattr(
                self,
                "_runtime_paths",
                AppPaths.for_app_root(
                    self.app_root
                ),
            )
            .runtime_binary(
                "ffprobe"
            )
        )

        if not ffprobe.is_file():
            return 0.0

        import subprocess

        try:
            result = subprocess.run(
                [
                    str(
                        ffprobe
                    ),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    (
                        "default="
                        "noprint_wrappers=1:"
                        "nokey=1"
                    ),
                    str(
                        path
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20,
            )

            return max(
                0.0,
                float(
                    result.stdout.strip()
                    or 0.0
                ),
            )
        except Exception:
            return 0.0

    patched_init._central_linux_paths = True
    patched_toggle._central_linux_paths = True
    patched_probe._central_linux_paths = True

    ScreenRecorderPage.__init__ = patched_init
    ScreenRecorderPage._toggle_module = patched_toggle
    ScreenRecorderPage._probe_duration = patched_probe


def _install_covers_linux_data_dir() -> None:
    if not is_linux():
        return

    from monitor_noticias.capas_tool.app import config

    def central_data_dir() -> Path:
        paths = AppPaths.discover()

        target = (
            paths.data
            / "capas"
        )
        target.mkdir(
            parents=True,
            exist_ok=True,
        )
        return target

    def central_cache_dir() -> Path:
        target = (
            central_data_dir()
            / "cache"
        )
        target.mkdir(
            parents=True,
            exist_ok=True,
        )
        return target

    def central_settings_path() -> Path:
        return (
            central_data_dir()
            / "settings.json"
        )

    config.data_dir = central_data_dir
    config.cache_dir = central_cache_dir
    config.settings_path = central_settings_path

    # Alguns módulos importaram essas funções por valor.
    try:
        from monitor_noticias.capas_tool.app import ui as covers_ui
        covers_ui.cache_dir = central_cache_dir
    except Exception:
        pass

    try:
        from monitor_noticias.capas_tool.app import valor_email_pdf
        valor_email_pdf.data_dir = central_data_dir
    except Exception:
        pass


def install_linux_boot_patch(
    main_window_class,
) -> None:
    """Compatibilidade de primeiro boot do Central no Ubuntu."""

    global _INSTALLED

    if _INSTALLED:
        return

    _install_main_window_identity(
        main_window_class
    )
    _install_settings_identity()
    _install_reference_video_editor_paths()
    _install_pdf_editor_paths()
    _install_screen_recorder_boot_paths()
    _install_covers_linux_data_dir()

    _INSTALLED = True
