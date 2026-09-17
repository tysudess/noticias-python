from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import requests

from .core import ExtractorEngine


@dataclass(frozen=True, slots=True)
class UpdateResult:
    success: bool
    message: str


class YtDlpUpdater:
    URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    UA = "MonitorDeNoticias-Extractor/3.0.1"

    def __init__(self, engine: ExtractorEngine) -> None:
        self.engine = engine
        self.target = engine.yt_dlp

    def _validate(self, executable: Path) -> str:
        if not executable.is_file() or executable.stat().st_size <= 1_000_000:
            return ""
        try:
            result = self.engine.runner.run(
                [str(executable), "--version"], directory=self.engine.app_root, timeout=30
            )
            if result.exit_code != 0:
                return ""
            return next((x.strip() for x in result.output.splitlines() if x.strip()), "")
        except Exception:
            return ""

    def update(self, progress=lambda _message: None) -> UpdateResult:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        temp = self.target.with_name("yt-dlp.update.tmp.exe")
        backup = self.target.with_name("yt-dlp.backup.exe")
        try:
            progress("Baixando atualização do yt-dlp...")
            with requests.get(
                self.URL,
                headers={"User-Agent": self.UA},
                stream=True,
                timeout=(30, 60),
                allow_redirects=True,
            ) as response:
                response.raise_for_status()
                with temp.open("wb") as output:
                    for chunk in response.iter_content(256 * 1024):
                        if chunk:
                            output.write(chunk)
            if not temp.exists() or temp.stat().st_size <= 1_000_000:
                raise RuntimeError("Arquivo de atualização inválido.")

            progress("Validando novo yt-dlp...")
            version = self._validate(temp)
            if not version:
                raise RuntimeError("O novo yt-dlp não respondeu à validação.")

            progress("Aplicando atualização validada...")
            backup.unlink(missing_ok=True)
            if self.target.exists():
                os.replace(self.target, backup)
            # os.replace é substituição atômica no mesmo volume quando suportada
            # pelo sistema; corresponde ao primeiro caminho ATOMIC_MOVE da baseline.
            os.replace(temp, self.target)

            installed_version = self._validate(self.target)
            if not installed_version:
                raise RuntimeError("Falha ao validar o yt-dlp após a substituição.")

            backup.unlink(missing_ok=True)
            return UpdateResult(True, f"yt-dlp atualizado e validado: {installed_version}")
        except Exception as exc:
            temp.unlink(missing_ok=True)
            current_is_valid = bool(self._validate(self.target)) if self.target.exists() else False
            if not current_is_valid and backup.exists():
                try:
                    self.target.unlink(missing_ok=True)
                    os.replace(backup, self.target)
                except Exception:
                    pass
            restored = self.target.exists() and bool(self._validate(self.target))
            if restored:
                suffix = "O executável anterior foi restaurado e preservado."
            elif backup.exists():
                suffix = f"O backup anterior foi preservado em {backup.name} para recuperação."
            else:
                suffix = "Não foi possível confirmar a restauração automática do executável anterior."
            return UpdateResult(False, f"Atualização não aplicada. {suffix} {exc}")
        finally:
            temp.unlink(missing_ok=True)
            # Intencionalmente não apagamos backup em falha.
