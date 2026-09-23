# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH)

pdfium_datas, pdfium_bins, pdfium_hidden = collect_all(
    "pypdfium2"
)
keyring_datas, keyring_bins, keyring_hidden = collect_all(
    "keyring"
)
secret_datas, secret_bins, secret_hidden = collect_all(
    "secretstorage"
)

CAPAS_ASSETS = (
    ROOT
    / "src"
    / "monitor_noticias"
    / "capas_tool"
    / "assets"
)

APP_ASSETS = (
    ROOT
    / "src"
    / "monitor_noticias"
    / "assets"
)

capas_datas = [
    (
        str(CAPAS_ASSETS / "newspapers.json"),
        "monitor_noticias/capas_tool/assets",
    ),
    (
        str(CAPAS_ASSETS / "principais_capas_cover.png"),
        "monitor_noticias/capas_tool/assets",
    ),
    (
        str(CAPAS_ASSETS / "app_icon.png"),
        "monitor_noticias/capas_tool/assets",
    ),
    (
        str(CAPAS_ASSETS / "app_icon.ico"),
        "monitor_noticias/capas_tool/assets",
    ),
]

app_datas = [
    (
        str(APP_ASSETS / "app_icon.png"),
        "monitor_noticias/assets",
    ),
    (
        str(APP_ASSETS / "app_icon.ico"),
        "monitor_noticias/assets",
    ),
]

hidden = list(
    dict.fromkeys(
        pdfium_hidden
        + keyring_hidden
        + secret_hidden
        + [
            "PySide6.QtNetwork",
            "PySide6.QtMultimedia",
            "PySide6.QtMultimediaWidgets",
            "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets",
            "keyring.backends.SecretService",
            "secretstorage",
        ]
    )
)

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=(
        pdfium_bins
        + keyring_bins
        + secret_bins
    ),
    datas=(
        pdfium_datas
        + keyring_datas
        + secret_datas
        + capas_datas
        + app_datas
    ),
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        "scripts/pyi_runtime_linux_validation.py",
    ],
    excludes=[
        "pytest",
        "pyaudiowpatch",
        "_portaudiowpatch",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CentralInteligenteDeMidia",
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
    name="CentralInteligenteDeMidia",
)
