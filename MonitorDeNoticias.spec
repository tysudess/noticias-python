# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

pdfium_datas, pdfium_bins, pdfium_hidden = collect_all("pypdfium2")

# PyMuPDF/fitz é usado pelo programa Principais Capas para PDF.
pymupdf_datas, pymupdf_bins, pymupdf_hidden = collect_all("pymupdf")

capas_datas = collect_data_files(
    "monitor_noticias.capas_tool",
    includes=["assets/*"],
)

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=pdfium_bins + pymupdf_bins,
    datas=pdfium_datas + pymupdf_datas + capas_datas,
    hiddenimports=(
        pdfium_hidden
        + pymupdf_hidden
        + ["pymupdf", "fitz"]
    ),
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
