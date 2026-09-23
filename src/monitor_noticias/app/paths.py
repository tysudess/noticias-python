from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from monitor_noticias.platform.binaries import (
    bundled_binary,
    resolve_binary,
    writable_binary,
)
from monitor_noticias.platform.current import (
    appimage_original_path,
    is_appimage,
    is_linux,
)


APP_DATA_DIRNAME = (
    "Central-Inteligente-de-Midia-Data"
)

XDG_APP_DIRNAME = (
    "CentralInteligenteDeMidia"
)


def _development_root() -> Path:
    return Path(
        __file__
    ).resolve().parents[3]


def resolve_app_root() -> Path:
    if getattr(
        sys,
        "frozen",
        False,
    ):
        return (
            Path(
                sys.executable
            )
            .resolve()
            .parent
        )

    return _development_root()


def _xdg_state_root() -> Path:
    data_home = (
        os.environ.get(
            "XDG_DATA_HOME"
        )
        or ""
    ).strip()

    if data_home:
        return (
            Path(data_home)
            .expanduser()
            / XDG_APP_DIRNAME
        )

    return (
        Path.home()
        / ".local"
        / "share"
        / XDG_APP_DIRNAME
    )


def _directory_is_writable(
    directory: Path,
) -> bool:
    try:
        directory = (
            Path(directory)
            .expanduser()
        )

        return (
            directory.exists()
            and directory.is_dir()
            and os.access(
                directory,
                os.W_OK,
            )
        )
    except Exception:
        return False


def resolve_state_root(
    app_root: Path | None = None,
) -> Path:
    root = (
        Path(app_root)
        if app_root is not None
        else resolve_app_root()
    )

    if is_appimage():
        original = appimage_original_path()

        if original is not None:
            parent = original.parent

            if _directory_is_writable(
                parent
            ):
                return (
                    parent
                    / APP_DATA_DIRNAME
                )

        return _xdg_state_root()

    if (
        not getattr(
            sys,
            "frozen",
            False,
        )
        or _directory_is_writable(
            root
        )
    ):
        return root

    if is_linux():
        return _xdg_state_root()

    return root


def _same_path(
    left: Path,
    right: Path,
) -> bool:
    try:
        return (
            Path(left).resolve()
            == Path(right).resolve()
        )
    except Exception:
        return (
            Path(left)
            == Path(right)
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AppPaths:
    root: Path
    state_root: Path | None = None

    def __post_init__(
        self,
    ) -> None:
        root = Path(self.root)

        state = (
            Path(self.state_root)
            if self.state_root is not None
            else root
        )

        object.__setattr__(
            self,
            "root",
            root,
        )
        object.__setattr__(
            self,
            "state_root",
            state,
        )

    @classmethod
    def discover(
        cls,
    ) -> "AppPaths":
        root = resolve_app_root()

        return cls(
            root=root,
            state_root=resolve_state_root(
                root
            ),
        )

    @classmethod
    def for_app_root(
        cls,
        app_root: Path,
    ) -> "AppPaths":
        """Preserva caminhos explícitos de testes e reconhece a raiz real.

        As páginas atuais recebem apenas `paths.root`. Dentro de AppImage,
        esta função recupera também o `state_root` gravável correspondente.
        """

        requested = Path(app_root)
        discovered = cls.discover()

        if _same_path(
            requested,
            discovered.root,
        ):
            return discovered

        return cls(
            root=requested,
            state_root=requested,
        )

    @property
    def resources(self) -> Path:
        return self.root / "resources"

    @property
    def data(self) -> Path:
        return (
            Path(self.state_root)
            / "data"
        )

    @property
    def bin(self) -> Path:
        return self.root / "bin"

    @property
    def user_bin(self) -> Path:
        return (
            Path(self.state_root)
            / "bin"
        )

    @property
    def logs(self) -> Path:
        return (
            Path(self.state_root)
            / "logs"
        )

    @property
    def temp(self) -> Path:
        return (
            Path(self.state_root)
            / "temp"
        )

    @property
    def videos(self) -> Path:
        return (
            Path(self.state_root)
            / "Videos"
        )

    @property
    def video_editor_exports(self) -> Path:
        return (
            Path(self.state_root)
            / "VideoEditorExports"
        )

    @property
    def news_db(self) -> Path:
        return self.data / "news.db"

    @property
    def videos_db(self) -> Path:
        return self.data / "videos.db"

    def runtime_binary(
        self,
        name: str,
        *,
        allow_system: bool = True,
    ) -> Path:
        return resolve_binary(
            self.root,
            name,
            state_root=Path(
                self.state_root
            ),
            allow_system=allow_system,
        )

    def writable_binary(
        self,
        name: str,
    ) -> Path:
        return writable_binary(
            self.root,
            Path(self.state_root),
            name,
        )

    @property
    def ffmpeg(self) -> Path:
        return self.runtime_binary(
            "ffmpeg"
        )

    @property
    def ffprobe(self) -> Path:
        return self.runtime_binary(
            "ffprobe"
        )

    @property
    def yt_dlp(self) -> Path:
        return self.runtime_binary(
            "yt-dlp"
        )

    @property
    def deno(self) -> Path:
        return self.runtime_binary(
            "deno"
        )

    def ensure_runtime_dirs(
        self,
    ) -> None:
        for directory in (
            self.data,
            self.logs,
            self.temp,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
