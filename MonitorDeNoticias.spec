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

# V81 — reforço do ícone do executável Windows.
#
# O parâmetro icon= do PyInstaller continua acima. Alguns builds one-dir estavam
# chegando ao Explorer com o ícone genérico. Depois de COLLECT, atualizamos
# explicitamente RT_ICON/RT_GROUP_ICON usando apenas a API nativa do Windows.
if sys.platform == "win32":
    import ctypes
    import struct

    def _make_int_resource(value: int):
        return ctypes.c_void_p(int(value))

    def _read_ico_entries(path: Path):
        raw = path.read_bytes()
        if len(raw) < 6:
            raise RuntimeError("ICO da Central está vazio ou corrompido.")

        reserved, icon_type, count = struct.unpack_from("<HHH", raw, 0)
        if reserved != 0 or icon_type != 1 or count < 1:
            raise RuntimeError("Formato ICO inválido para o executável Windows.")

        entries = []
        offset = 6
        for index in range(count):
            if offset + 16 > len(raw):
                raise RuntimeError("Tabela ICO incompleta.")
            width, height, colors, reserved_byte, planes, bpp, size, image_offset = (
                struct.unpack_from("<BBBBHHII", raw, offset)
            )
            image = raw[image_offset:image_offset + size]
            if len(image) != size:
                raise RuntimeError("Imagem interna do ICO incompleta.")
            entries.append(
                (width, height, colors, reserved_byte, planes, bpp, image)
            )
            offset += 16
        return entries

    def _force_windows_exe_icon(exe_path: Path, ico_path: Path) -> None:
        entries = _read_ico_entries(ico_path)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        begin = kernel32.BeginUpdateResourceW
        begin.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
        begin.restype = ctypes.c_void_p

        update = kernel32.UpdateResourceW
        update.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ushort,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        update.restype = ctypes.c_bool

        end = kernel32.EndUpdateResourceW
        end.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        end.restype = ctypes.c_bool

        handle = begin(str(exe_path), False)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        committed = False
        buffers = []
        try:
            group = bytearray(struct.pack("<HHH", 0, 1, len(entries)))

            for icon_id, entry in enumerate(entries, start=1):
                width, height, colors, reserved_byte, planes, bpp, image = entry
                buf = ctypes.create_string_buffer(image)
                buffers.append(buf)

                ok = update(
                    handle,
                    _make_int_resource(3),      # RT_ICON
                    _make_int_resource(icon_id),
                    0x0409,
                    ctypes.cast(buf, ctypes.c_void_p),
                    len(image),
                )
                if not ok:
                    raise ctypes.WinError(ctypes.get_last_error())

                group.extend(
                    struct.pack(
                        "<BBBBHHIH",
                        width,
                        height,
                        colors,
                        reserved_byte,
                        planes,
                        bpp,
                        len(image),
                        icon_id,
                    )
                )

            group_buf = ctypes.create_string_buffer(bytes(group))
            buffers.append(group_buf)
            ok = update(
                handle,
                _make_int_resource(14),         # RT_GROUP_ICON
                _make_int_resource(1),
                0x0409,
                ctypes.cast(group_buf, ctypes.c_void_p),
                len(group),
            )
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())

            if not end(handle, False):
                raise ctypes.WinError(ctypes.get_last_error())
            committed = True
        finally:
            if not committed:
                try:
                    end(handle, True)
                except Exception:
                    pass

        # Confirma que o Windows reconhece pelo menos um ícone associado.
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        extract = shell32.ExtractIconExW
        extract.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_uint,
        ]
        extract.restype = ctypes.c_uint
        count = extract(str(exe_path), -1, None, None, 0)
        if count < 1:
            raise RuntimeError("O EXE foi gerado sem recurso de ícone reconhecível.")

    _built_exe = Path(DISTPATH) / "MonitorDeNoticias" / "MonitorDeNoticias.exe"
    _built_icon = APP_ASSETS / "app_icon.ico"
    if not _built_exe.is_file():
        raise RuntimeError(f"Executável final não encontrado para aplicar ícone: {_built_exe}")
    _force_windows_exe_icon(_built_exe, _built_icon)
