# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all


pdfium_datas, pdfium_bins, pdfium_hidden = collect_all("pypdfium2")
pawp_datas, pawp_bins, pawp_hidden = collect_all("pyaudiowpatch")
trust_datas, trust_bins, trust_hidden = collect_all("truststore")

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
    )
)

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=pdfium_bins + pawp_bins + trust_bins,
    datas=(
        pdfium_datas
        + pawp_datas
        + trust_datas
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
