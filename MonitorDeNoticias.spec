# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import subprocess
import sys

from PyInstaller.utils.hooks import collect_all


pdfium_datas, pdfium_bins, pdfium_hidden = collect_all("pypdfium2")
pawp_datas, pawp_bins, pawp_hidden = collect_all("pyaudiowpatch")
trust_datas, trust_bins, trust_hidden = collect_all("truststore")
# V129: inclui explicitamente a estrutura de runtime do Shiboken exigida
# durante a inicialização do PySide6 no Windows.
shiboken_datas, shiboken_bins, shiboken_hidden = collect_all("shiboken6")

ROOT = Path(SPECPATH)
CAPAS_ASSETS = ROOT / "src" / "monitor_noticias" / "capas_tool" / "assets"
APP_ASSETS = ROOT / "src" / "monitor_noticias" / "assets"

capas_datas = [
    (str(CAPAS_ASSETS / "newspapers.json"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "principais_capas_cover.png"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "app_icon.png"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "app_icon.ico"), "monitor_noticias/capas_tool/assets"),
]

app_datas = [
    (str(APP_ASSETS / "app_icon.png"), "monitor_noticias/assets"),
    (str(APP_ASSETS / "app_icon.ico"), "monitor_noticias/assets"),
]

audio_hidden = list(
    dict.fromkeys(
        pawp_hidden
        + [
            "pyaudiowpatch",
            "_portaudiowpatch",
        ]
    )
)

hidden = list(
    dict.fromkeys(
        pdfium_hidden
        + audio_hidden
        + trust_hidden
        + shiboken_hidden
    )
)

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=pdfium_bins + pawp_bins + trust_bins + shiboken_bins,
    datas=(
        pdfium_datas
        + pawp_datas
        + trust_datas
        + shiboken_datas
        + capas_datas
        + app_datas
    ),
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        "scripts/pyi_runtime_system_trust.py",
        "scripts/pyi_runtime_portable_validation.py",
    ],
    excludes=["pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MonitorDeNoticias",
    icon=str(APP_ASSETS / "app_icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MonitorDeNoticias",
)

# V132: valida a estrutura e importa Shiboken de forma isolada.
# Em um build onedir do PyInstaller 6.x, os pacotes ficam em _internal.
# O PySide6 procura _internal/shiboken6 ao lado de _internal/PySide6;
# não exige uma subpasta shiboken6/libshiboken6.
if sys.platform == "win32":
    _portable_root = Path(DISTPATH) / "MonitorDeNoticias"
    _contents_root_candidates = [
        _portable_root / "_internal",
        _portable_root,
    ]
    _contents_root = next(
        (
            path for path in _contents_root_candidates
            if (path / "PySide6").is_dir()
        ),
        None,
    )
    if _contents_root is None:
        raise RuntimeError(
            "Estrutura PySide6 não encontrada no portable. Caminhos verificados: "
            + "; ".join(str(path / "PySide6") for path in _contents_root_candidates)
        )

    _shiboken_package_dir = _contents_root / "shiboken6"
    if not _shiboken_package_dir.is_dir():
        raise RuntimeError(
            "Runtime Shiboken incompleto: a pasta do pacote "
            f"'{_shiboken_package_dir}' não foi incluída ao lado de PySide6."
        )

    _shiboken_extensions = [
        path for path in _shiboken_package_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pyd"
    ]
    _shiboken_dlls = [
        path for path in _shiboken_package_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".dll"
    ]
    if not _shiboken_extensions:
        raise RuntimeError(
            "Runtime Shiboken incompleto: nenhum módulo .pyd foi encontrado em "
            f"'{_shiboken_package_dir}'."
        )
    if not _shiboken_dlls:
        raise RuntimeError(
            "Runtime Shiboken incompleto: nenhuma DLL foi encontrada em "
            f"'{_shiboken_package_dir}'."
        )

    # O pacote Python PySide6 é congelado no PYZ do PyInstaller e, por isso,
    # não deve ser validado importando PySide6 por um Python externo: isso
    # poderia carregar o pacote do site-packages do runner. Validamos os
    # módulos nativos físicos e importamos exclusivamente o Shiboken do portable.
    _pyside_native_extensions = [
        path for path in (_contents_root / "PySide6").rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".pyd"
        and path.name.lower().startswith("qtcore")
    ]
    if not _pyside_native_extensions:
        raise RuntimeError(
            "Runtime PySide6 incompleto: módulo nativo QtCore (.pyd) "
            f"não foi encontrado em '{_contents_root / 'PySide6'}'."
        )

    _shiboken_smoke_test = r"""
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
_dll_handles = []
for dll_dir in (root, root / "shiboken6", root / "PySide6"):
    if dll_dir.is_dir():
        _dll_handles.append(os.add_dll_directory(str(dll_dir)))
        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
sys.path.insert(0, str(root))

import shiboken6
from shiboken6 import Shiboken

expected_shiboken = (root / "shiboken6").resolve()
actual_shiboken = pathlib.Path(shiboken6.__file__).resolve().parent
if actual_shiboken != expected_shiboken:
    raise RuntimeError(
        f"Shiboken importado de local inesperado: {actual_shiboken}; "
        f"esperado: {expected_shiboken}"
    )
print(f"Shiboken do portable carregado: {actual_shiboken}")
"""
    _smoke = subprocess.run(
        [sys.executable, "-S", "-c", _shiboken_smoke_test, str(_contents_root)],
        cwd=str(_portable_root),
        env={**os.environ, "PYTHONNOUSERSITE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    if _smoke.returncode != 0:
        raise RuntimeError(
            "Teste isolado de importação do Shiboken no portable falhou.\n"
            f"Saída:\n{_smoke.stdout}\nErro:\n{_smoke.stderr}"
        )
    print(_smoke.stdout.strip())
    print(
        "Runtime Shiboken/PySide6 validado: "
        f"{len(_shiboken_extensions)} módulo(s) Shiboken .pyd, "
        f"{len(_shiboken_dlls)} DLL(s) Shiboken e "
        f"{len(_pyside_native_extensions)} módulo(s) QtCore .pyd."
    )

# V82 — NÃO editar o executável depois que o PyInstaller anexar o PKG.
#
# A V81 usava BeginUpdateResourceW/UpdateResourceW depois do COLLECT para
# forçar RT_ICON. Em executáveis PyInstaller isso pode remover/truncar o overlay
# no fim do arquivo, exatamente onde fica o CArchive/PKG. O sintoma é:
#   Could not load PyInstaller's embedded PKG archive from the executable
#
# O ícone continua sendo aplicado pelo mecanismo nativo do PyInstaller no
# parâmetro icon= acima. A validação abaixo é SOMENTE LEITURA: se o EXE perder
# o PKG por qualquer motivo, o build falha antes de gerar/publicar o portable.
if sys.platform == "win32":
    from PyInstaller.archive.readers import CArchiveReader

    _built_exe = (
        Path(DISTPATH)
        / "MonitorDeNoticias"
        / "MonitorDeNoticias.exe"
    )

    if not _built_exe.is_file():
        raise RuntimeError(
            f"Executável final não encontrado para validação: {_built_exe}"
        )

    # Os builds válidos recentes possuem vários MB. Um EXE de poucas centenas
    # de KB é forte indício de bootloader sem o PKG anexado.
    _exe_size = _built_exe.stat().st_size
    if _exe_size < 2_000_000:
        raise RuntimeError(
            "MonitorDeNoticias.exe ficou anormalmente pequeno "
            f"({_exe_size} bytes). O PKG do PyInstaller provavelmente não foi "
            "anexado corretamente."
        )

    try:
        _archive = CArchiveReader(str(_built_exe))
    except Exception as exc:
        raise RuntimeError(
            "MonitorDeNoticias.exe foi gerado sem um PKG/CArchive PyInstaller "
            "legível. O build foi interrompido para não publicar um executável "
            "corrompido."
        ) from exc

    if not getattr(_archive, "toc", None):
        raise RuntimeError(
            "MonitorDeNoticias.exe possui CArchive vazio; o build não será publicado."
        )
