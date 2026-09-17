from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessResult:
    exit_code: int
    output: str


def _hidden_windows_kwargs() -> dict[str, object]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"startupinfo": startupinfo, "creationflags": creationflags}


def _normalize_command(command: Sequence[str]) -> list[str]:
    if not command:
        raise ValueError("Comando vazio.")
    argv = [str(x) for x in command]
    if os.name == "nt" and Path(argv[0]).name.lower() == "powershell.exe":
        if not any(x.lower() == "-windowstyle" for x in argv[1:]):
            argv = [argv[0], "-WindowStyle", "Hidden", *argv[1:]]
    return argv


class HiddenProcessRunner:
    """Equivalente de HiddenWindowsProcess sem shell=True e sem concatenação de argv."""

    def start(
        self,
        command: Sequence[str],
        *,
        directory: Path,
        environment: Mapping[str, str] | None = None,
        merge_stderr: bool = True,
    ) -> subprocess.Popen[str]:
        argv = _normalize_command(command)
        env = os.environ.copy()
        if environment:
            env.update({str(k): str(v) for k, v in environment.items()})
        stderr = subprocess.STDOUT if merge_stderr else subprocess.PIPE
        return subprocess.Popen(
            argv,
            cwd=str(directory),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            **_hidden_windows_kwargs(),
        )

    def run(
        self,
        command: Sequence[str],
        *,
        directory: Path,
        environment: Mapping[str, str] | None = None,
        stdin_text: str = "",
        timeout: float | None = None,
    ) -> ProcessResult:
        process = self.start(command, directory=directory, environment=environment)
        try:
            output, _ = process.communicate(stdin_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.destroy_tree(process)
            raise
        return ProcessResult(process.returncode, output or "")

    def destroy_tree(self, process: subprocess.Popen[object] | None) -> None:
        if process is None:
            return
        if os.name == "nt" and process.poll() is None:
            try:
                subprocess.run(
                    ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8,
                    check=False,
                    shell=False,
                    **_hidden_windows_kwargs(),
                )
            except Exception:
                log.exception("Falha ao encerrar árvore de processo PID=%s", process.pid)
        if process.poll() is None:
            try:
                process.kill()
            except Exception:
                log.exception("Falha ao encerrar processo PID=%s", getattr(process, "pid", "?"))
