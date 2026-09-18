# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

pdfium_datas, pdfium_bins, pdfium_hidden = collect_all("pypdfium2")
pawp_datas, pawp_bins, pawp_hidden = collect_all("pyaudiowpatch")

ROOT = Path(SPECPATH)
CAPAS_ASSETS = ROOT / "src" / "monitor_noticias" / "capas_tool" / "assets"

capas_datas = [
    (str(CAPAS_ASSETS / "newspapers.json"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "principais_capas_cover.png"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "app_icon.png"), "monitor_noticias/capas_tool/assets"),
    (str(CAPAS_ASSETS / "app_icon.ico"), "monitor_noticias/capas_tool/assets"),
]

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=pdfium_bins + pawp_bins,
    datas=pdfium_datas + pawp_datas + capas_datas,
    hiddenimports=pdfium_hidden + pawp_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["scripts/pyi_runtime_portable_validation.py"],
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
