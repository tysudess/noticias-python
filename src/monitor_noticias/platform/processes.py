from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import signal
import subprocess
from typing import Mapping, Sequence

from .current import is_windows


log = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessResult:
    exit_code: int
    output: str


def _platform_popen_kwargs() -> dict[str, object]:
    if is_windows():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        return {
            "startupinfo": startupinfo,
            "creationflags": getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        }

    return {
        "start_new_session": True,
    }


def _normalize_command(
    command: Sequence[str],
) -> list[str]:
    if not command:
        raise ValueError("Comando vazio.")

    argv = [
        str(item)
        for item in command
    ]

    if (
        is_windows()
        and Path(argv[0]).name.lower()
        == "powershell.exe"
    ):
        if not any(
            item.lower() == "-windowstyle"
            for item in argv[1:]
        ):
            argv = [
                argv[0],
                "-WindowStyle",
                "Hidden",
                *argv[1:],
            ]

    return argv


class HiddenProcessRunner:
    """Runner compatível com Windows e Linux.

    O nome é preservado por compatibilidade com o Extrator existente.
    """

    def start(
        self,
        command: Sequence[str],
        *,
        directory: Path,
        environment: Mapping[str, str] | None = None,
        merge_stderr: bool = True,
    ) -> subprocess.Popen[str]:
        argv = _normalize_command(
            command
        )

        env = os.environ.copy()

        if environment:
            env.update(
                {
                    str(key): str(value)
                    for key, value
                    in environment.items()
                }
            )

        stderr = (
            subprocess.STDOUT
            if merge_stderr
            else subprocess.PIPE
        )

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
            **_platform_popen_kwargs(),
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
        process = self.start(
            command,
            directory=directory,
            environment=environment,
        )

        try:
            output, _ = process.communicate(
                stdin_text,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            self.destroy_tree(
                process
            )
            raise

        return ProcessResult(
            process.returncode,
            output or "",
        )

    def destroy_tree(
        self,
        process: subprocess.Popen[object] | None,
    ) -> None:
        if process is None:
            return

        if process.poll() is not None:
            return

        if is_windows():
            try:
                subprocess.run(
                    [
                        "taskkill.exe",
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8,
                    check=False,
                    shell=False,
                    **_platform_popen_kwargs(),
                )
            except Exception:
                log.exception(
                    "Falha ao encerrar árvore de processo "
                    "Windows PID=%s",
                    process.pid,
                )

        else:
            try:
                os.killpg(
                    process.pid,
                    signal.SIGTERM,
                )

                try:
                    process.wait(
                        timeout=3,
                    )
                except subprocess.TimeoutExpired:
                    os.killpg(
                        process.pid,
                        signal.SIGKILL,
                    )
            except ProcessLookupError:
                return
            except Exception:
                log.exception(
                    "Falha ao encerrar grupo de processos "
                    "Linux PID=%s",
                    process.pid,
                )

        if process.poll() is None:
            try:
                process.kill()
            except Exception:
                log.exception(
                    "Falha ao encerrar processo PID=%s",
                    getattr(
                        process,
                        "pid",
                        "?",
                    ),
                )
