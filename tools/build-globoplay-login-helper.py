from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "globoplay-login-helper.py"
RESOURCE_DIR = ROOT / "resources" / "globoplay-login-helper"
TARGET = RESOURCE_DIR / "GloboplayLoginHelper.exe"
WORK = ROOT / ".globoplay-helper-build"
DIST = WORK / "dist"
SPEC = WORK / "spec"
PYIWORK = WORK / "work"


def ensure_packages() -> None:
    missing = importlib.util.find_spec("PySide6") is None or importlib.util.find_spec("PyInstaller") is None
    if not missing:
        return
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "PySide6==6.9.1",
        "PyInstaller==6.15.0",
    ])


def main() -> int:
    if os.name != "nt":
        print("Build do helper Globoplay ignorado fora do Windows.")
        return 0
    if not SOURCE.exists():
        raise SystemExit(f"Fonte do helper ausente: {SOURCE}")

    ensure_packages()
    shutil.rmtree(WORK, ignore_errors=True)
    DIST.mkdir(parents=True, exist_ok=True)
    SPEC.mkdir(parents=True, exist_ok=True)
    PYIWORK.mkdir(parents=True, exist_ok=True)

    subprocess.check_call([
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "GloboplayLoginHelper",
        "--distpath",
        str(DIST),
        "--workpath",
        str(PYIWORK),
        "--specpath",
        str(SPEC),
        str(SOURCE),
    ], cwd=str(ROOT))

    built = DIST / "GloboplayLoginHelper.exe"
    if not built.exists() or built.stat().st_size < 20_000_000:
        raise SystemExit("Helper Globoplay não foi gerado corretamente.")

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, TARGET)
    print(f"Helper Globoplay gerado: {TARGET} ({TARGET.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
