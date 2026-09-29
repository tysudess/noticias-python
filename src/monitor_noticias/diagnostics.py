from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import tempfile
import time
import zipfile

from monitor_noticias.version import (
    APP_DISPLAY_NAME,
    APP_VERSION,
    platform_version_label,
)


@dataclass(slots=True)
class DiagnosticItem:
    key: str
    label: str
    status: str
    detail: str
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(slots=True)
class DiagnosticReport:
    generated_at: str
    app: str
    version: str
    platform: str
    items: list[DiagnosticItem]

    @property
    def errors(self) -> int:
        return sum(1 for item in self.items if item.status == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for item in self.items if item.status == "warning")

    @property
    def overall_status(self) -> str:
        if self.errors:
            return "error"
        if self.warnings:
            return "warning"
        return "ok"

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "app": self.app,
            "version": self.version,
            "platform": self.platform,
            "overall_status": self.overall_status,
            "errors": self.errors,
            "warnings": self.warnings,
            "items": [asdict(item) for item in self.items],
        }


class SystemDiagnostics:
    """Diagnóstico local e de conectividade sem expor credenciais."""

    def __init__(self, paths, controller, auth_runtime=None) -> None:
        self.paths = paths
        self.controller = controller
        self.auth_runtime = auth_runtime

    @staticmethod
    def _timed(operation):
        started = time.monotonic()
        try:
            value = operation()
            return value, int((time.monotonic() - started) * 1000), None
        except Exception as exc:
            return None, int((time.monotonic() - started) * 1000), exc

    @staticmethod
    def _writable(directory: Path) -> tuple[bool, str]:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                prefix="central-diag-",
                suffix=".tmp",
                dir=directory,
                delete=False,
            ) as handle:
                handle.write(b"ok")
                probe = Path(handle.name)
            probe.unlink(missing_ok=True)
            return True, str(directory)
        except Exception as exc:
            return False, f"{directory} — {exc}"

    def _binary_item(
        self,
        key: str,
        label: str,
        path: Path,
        *,
        warning_only: bool = False,
    ) -> DiagnosticItem:
        candidate = Path(path)
        exists = candidate.is_file()
        return DiagnosticItem(
            key=key,
            label=label,
            status=(
                "ok"
                if exists
                else ("warning" if warning_only else "error")
            ),
            detail=(
                str(candidate)
                if exists
                else f"Não encontrado: {candidate}"
            ),
        )

    def run(self) -> DiagnosticReport:
        items: list[DiagnosticItem] = []

        items.append(
            DiagnosticItem(
                key="app",
                label="Aplicativo",
                status="ok",
                detail=(
                    f"{APP_DISPLAY_NAME} v{APP_VERSION} • "
                    f"{platform_version_label()} • Python {platform.python_version()}"
                ),
            )
        )

        for key, label, directory in (
            ("data_dir", "Pasta de dados", self.paths.data),
            ("logs_dir", "Pasta de logs", self.paths.logs),
            ("temp_dir", "Pasta temporária", self.paths.temp),
        ):
            ok, detail = self._writable(Path(directory))
            items.append(
                DiagnosticItem(
                    key=key,
                    label=label,
                    status="ok" if ok else "error",
                    detail=detail,
                )
            )

        for key, label, db_path in (
            ("news_db", "Banco de notícias", self.paths.news_db),
            ("videos_db", "Banco de vídeos", self.paths.videos_db),
        ):
            db = Path(db_path)

            if not db.is_file():
                items.append(
                    DiagnosticItem(
                        key=key,
                        label=label,
                        status="warning",
                        detail=f"Ainda não criado: {db}",
                    )
                )
                continue

            started = time.monotonic()
            try:
                with sqlite3.connect(
                    f"file:{db.as_posix()}?mode=ro",
                    uri=True,
                    timeout=3,
                ) as connection:
                    row = connection.execute("PRAGMA quick_check").fetchone()
                result = str(row[0] if row else "").lower()
                ok = result == "ok"
                detail = (
                    f"Integridade OK • {db.stat().st_size:,} bytes • {db}"
                    if ok
                    else f"PRAGMA quick_check: {result or 'sem resposta'}"
                )
            except Exception as exc:
                ok = False
                detail = str(exc) or exc.__class__.__name__

            items.append(
                DiagnosticItem(
                    key=key,
                    label=label,
                    status="ok" if ok else "error",
                    detail=detail,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
            )

        for key, label, path in (
            ("ffmpeg", "FFmpeg", self.paths.ffmpeg),
            ("ffprobe", "FFprobe", self.paths.ffprobe),
            ("yt_dlp", "yt-dlp", self.paths.yt_dlp),
            ("deno", "Deno", self.paths.deno),
        ):
            items.append(self._binary_item(key, label, Path(path)))

        if os.name == "nt":
            globoplay = (
                self.paths.resources
                / "globoplay-login-helper"
                / "GloboplayLoginHelper.exe"
            )
            news_extractor = (
                self.paths.root
                / "tools"
                / "news_extractor"
                / "ExtratorMateriasPortable-V1.25.19.exe"
            )
        else:
            globoplay = (
                self.paths.resources
                / "globoplay-login-helper"
                / "GloboplayLoginHelper"
            )
            news_extractor = (
                self.paths.root
                / "tools"
                / "news_extractor"
                / "ExtratorMateriasPortable-V1.25.19"
            )

        items.append(
            self._binary_item(
                "globoplay_helper",
                "Helper Globoplay",
                globoplay,
                warning_only=True,
            )
        )
        items.append(
            self._binary_item(
                "news_extractor",
                "Motor do Extrator de Notícias",
                news_extractor,
            )
        )

        try:
            backend = self.controller.proxy.secure_backend_label
            items.append(
                DiagnosticItem(
                    key="credential_store",
                    label="Cofre de credenciais",
                    status="ok",
                    detail=str(backend),
                )
            )
        except Exception as exc:
            items.append(
                DiagnosticItem(
                    key="credential_store",
                    label="Cofre de credenciais",
                    status="error",
                    detail=str(exc) or exc.__class__.__name__,
                )
            )

        cfg = self.controller.proxy_config

        if cfg.enabled:
            result, elapsed, exc = self._timed(self.controller.test_proxy)

            if exc is not None:
                items.append(
                    DiagnosticItem(
                        key="proxy",
                        label="Proxy Geral",
                        status="error",
                        detail=str(exc) or exc.__class__.__name__,
                        duration_ms=elapsed,
                    )
                )
            else:
                ok, message = result
                items.append(
                    DiagnosticItem(
                        key="proxy",
                        label="Proxy Geral",
                        status="ok" if ok else "error",
                        detail=(
                            f"{cfg.host}:{cfg.port} • {message}"
                        ),
                        duration_ms=elapsed,
                    )
                )
        else:
            items.append(
                DiagnosticItem(
                    key="proxy",
                    label="Proxy Geral",
                    status="ok",
                    detail="Desativado — conexão direta selecionada.",
                )
            )

        if self.auth_runtime is None:
            items.append(
                DiagnosticItem(
                    key="auth_server",
                    label="Servidor de autenticação",
                    status="warning",
                    detail="Autenticação não está ativa nesta execução.",
                )
            )
        else:
            result, elapsed, exc = self._timed(
                self.auth_runtime.client.test_server
            )
            if exc is not None:
                items.append(
                    DiagnosticItem(
                        key="auth_get",
                        label="Apps Script GET",
                        status="error",
                        detail=str(exc) or exc.__class__.__name__,
                        duration_ms=elapsed,
                    )
                )
            else:
                ok, message = result
                items.append(
                    DiagnosticItem(
                        key="auth_get",
                        label="Apps Script GET",
                        status="ok" if ok else "error",
                        detail=message,
                        duration_ms=elapsed,
                    )
                )

            result, elapsed, exc = self._timed(
                self.auth_runtime.client.test_post_transport
            )
            if exc is not None:
                items.append(
                    DiagnosticItem(
                        key="auth_post",
                        label="Apps Script POST",
                        status="error",
                        detail=str(exc) or exc.__class__.__name__,
                        duration_ms=elapsed,
                    )
                )
            else:
                ok, message = result
                items.append(
                    DiagnosticItem(
                        key="auth_post",
                        label="Apps Script POST",
                        status="ok" if ok else "error",
                        detail=message,
                        duration_ms=elapsed,
                    )
                )

            if self.auth_runtime.session is not None:
                token = self.auth_runtime.session.token
                result, elapsed, exc = self._timed(
                    lambda: self.auth_runtime.client.validate(token)
                )
                if exc is not None:
                    items.append(
                        DiagnosticItem(
                            key="auth_validate",
                            label="Validação real da sessão",
                            status="error",
                            detail=str(exc) or exc.__class__.__name__,
                            duration_ms=elapsed,
                        )
                    )
                else:
                    self.auth_runtime.session = result
                    items.append(
                        DiagnosticItem(
                            key="auth_validate",
                            label="Validação real da sessão",
                            status="ok",
                            detail=(
                                "Token, dispositivo, status, validade e permissões confirmados."
                            ),
                            duration_ms=elapsed,
                        )
                    )
            else:
                items.append(
                    DiagnosticItem(
                        key="auth_validate",
                        label="Validação real da sessão",
                        status="warning",
                        detail="Nenhuma sessão ativa disponível para teste.",
                    )
                )

        try:
            total, used, free = shutil.disk_usage(self.paths.state_root)
            items.append(
                DiagnosticItem(
                    key="disk",
                    label="Espaço livre",
                    status="ok" if free >= 1_000_000_000 else "warning",
                    detail=(
                        f"{free / (1024 ** 3):.1f} GB livres de "
                        f"{total / (1024 ** 3):.1f} GB"
                    ),
                )
            )
        except Exception as exc:
            items.append(
                DiagnosticItem(
                    key="disk",
                    label="Espaço livre",
                    status="warning",
                    detail=str(exc) or exc.__class__.__name__,
                )
            )

        return DiagnosticReport(
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            app=APP_DISPLAY_NAME,
            version=APP_VERSION,
            platform=platform_version_label(),
            items=items,
        )


_SECRET_PATTERNS = (
    re.compile(r"(?i)(senha|password|token|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)(https?://)([^/@:\s]+):([^/@\s]+)@"),
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~-]+"),
)


def sanitize_log_text(text: str) -> str:
    value = str(text or "")
    value = _SECRET_PATTERNS[0].sub(r"\1=***", value)
    value = _SECRET_PATTERNS[1].sub(r"\1***:***@", value)
    value = _SECRET_PATTERNS[2].sub(r"\1***", value)
    return value


def build_diagnostic_package(paths, report: DiagnosticReport) -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = downloads / f"Central-Diagnostico-{stamp}.zip"

    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "diagnostico.json",
            json.dumps(
                report.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
        )

        logs_dir = Path(paths.logs)
        if logs_dir.is_dir():
            for log_file in sorted(logs_dir.glob("*.log")):
                try:
                    data = log_file.read_bytes()[-512_000:]
                    text = data.decode("utf-8", "replace")
                    archive.writestr(
                        f"logs/{log_file.name}",
                        sanitize_log_text(text),
                    )
                except Exception:
                    continue

    return target
