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

    @staticmethod
    def _wait_finished(
        process: subprocess.Popen[object],
        timeout: float = 2.0,
    ) -> bool:
        try:
            process.wait(
                timeout=timeout
            )
            return True
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return process.poll() is not None

    def _terminate_linux(
        self,
        process: subprocess.Popen[object],
    ) -> bool:
        """Encerra processo Linux sem matar o grupo do próprio Central.

        Processos iniciados por ``HiddenProcessRunner.start`` recebem
        ``start_new_session=True`` e possuem um grupo próprio. Alguns helpers
        legados, porém, são criados por ``subprocess.Popen`` diretamente e
        herdam o grupo do processo principal. Nesse caso, usar ``killpg(pid)``
        não é correto; encerramos apenas o filho.
        """

        try:
            process_group = os.getpgid(
                process.pid
            )
        except ProcessLookupError:
            return True
        except Exception:
            process_group = None

        try:
            current_group = os.getpgrp()
        except Exception:
            current_group = None

        isolated_group = (
            process_group is not None
            and process_group == process.pid
            and process_group != current_group
        )

        try:
            if isolated_group:
                os.killpg(
                    process_group,
                    signal.SIGTERM,
                )
            else:
                process.terminate()

            if self._wait_finished(
                process,
                timeout=3.0,
            ):
                return True

            if isolated_group:
                os.killpg(
                    process_group,
                    signal.SIGKILL,
                )
            else:
                process.kill()

            return self._wait_finished(
                process,
                timeout=2.0,
            )

        except ProcessLookupError:
            return True
        except Exception:
            log.exception(
                "Falha ao encerrar processo/grupo Linux PID=%s",
                process.pid,
            )
            return process.poll() is not None

    def destroy_tree(
        self,
        process: subprocess.Popen[object] | None,
    ) -> None:
        """Encerra a árvore e só retorna depois de o processo realmente sair."""

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

            if self._wait_finished(
                process,
                timeout=2.0,
            ):
                return

        else:
            if self._terminate_linux(
                process
            ):
                return

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

        if process.poll() is None:
            self._wait_finished(
                process,
                timeout=2.0,
            )
