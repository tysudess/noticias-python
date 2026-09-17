from __future__ import annotations

from pathlib import Path
import shutil


MIN_HELPER_SIZE = 20_000_000
RESOURCE_RELATIVE = Path("resources") / "globoplay-login-helper" / "GloboplayLoginHelper.exe"
RUNTIME_RELATIVE = Path("data") / "extractor" / "runtime" / "GloboplayLoginHelper.exe"


def resolve_bundled_helper(app_root: Path) -> Path:
    """Materializa o helper empacotado no runtime, como GloboplayLoginWindow.kt.

    A baseline Kotlin lê `/globoplay-login-helper/GloboplayLoginHelper.exe` dos
    resources e o copia para `data/extractor/runtime/GloboplayLoginHelper.exe`
    antes de iniciar o processo. Não há fallback para helper externo.
    """
    root = Path(app_root)
    source = root / RESOURCE_RELATIVE
    if not source.is_file():
        raise FileNotFoundError(f"Recurso /globoplay-login-helper/GloboplayLoginHelper.exe ausente.")
    if source.stat().st_size <= MIN_HELPER_SIZE:
        raise RuntimeError("Navegador interno foi extraído de forma incompleta.")

    target = root / RUNTIME_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    # Kotlin regrava o target a partir do resource em cada abertura.
    with source.open("rb") as input_file, target.open("wb") as output_file:
        shutil.copyfileobj(input_file, output_file)
    if not target.is_file() or target.stat().st_size <= MIN_HELPER_SIZE:
        raise RuntimeError("Navegador interno foi extraído de forma incompleta.")
    return target
