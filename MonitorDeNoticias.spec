# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# PySide6 is intentionally NOT collected wholesale here. PyInstaller's Qt hooks
# follow the application's real imports and collect the Qt modules/plugins they
# require. This avoids redistributing unrelated Qt modules while preserving the
# functional dependency graph proved by the portable smoke suite.
pdfium_datas, pdfium_bins, pdfium_hidden = collect_all("pypdfium2")

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=pdfium_bins,
    datas=pdfium_datas,
    hiddenimports=pdfium_hidden,
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
