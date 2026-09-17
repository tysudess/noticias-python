from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _console_safe(text: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()

    if os.name == "nt":
        root = runner_temp / "Teste Edição Monitor"
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(
            workspace,
            root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
    else:
        root = workspace

    foreign_cwd = runner_temp / "cwd-fora"
    foreign_cwd.mkdir(parents=True, exist_ok=True)
    stdout_path = runner_temp / "pass15-entrypoint-stdout.log"
    stderr_path = runner_temp / "pass15-entrypoint-stderr.log"
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"

    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            [sys.executable, str(root / "run.py")],
            cwd=foreign_cwd,
            env=env,
            stdout=out,
            stderr=err,
        )
        time.sleep(6)
        early_code = process.poll()
        if early_code not in (None, 0):
            raise RuntimeError(
                f"run.py encerrou prematuramente com {early_code}\n"
                f"STDOUT:\n{_read(stdout_path)}\nSTDERR:\n{_read(stderr_path)}"
            )

        expected = [
            root / "logs" / "monitor-noticias.log",
            root / "data" / "news.db",
            root / "data" / "videos.db",
            root / "resources" / "monitor-icon.svg",
        ]
        missing = [str(path) for path in expected if not path.exists()]
        if missing:
            raise RuntimeError(
                "Arquivos esperados não foram criados/resolvidos: " + ", ".join(missing)
                + f"\nSTDOUT:\n{_read(stdout_path)}\nSTDERR:\n{_read(stderr_path)}"
            )

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    print(_console_safe(f"ENTRYPOINT OK root={root} cwd={foreign_cwd}"))
    stdout_text = _read(stdout_path)
    stderr_text = _read(stderr_path)
    if stdout_text:
        print(_console_safe(stdout_text))
    if stderr_text:
        print(_console_safe(stderr_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
