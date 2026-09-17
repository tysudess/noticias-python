from __future__ import annotations

import base64
import ctypes
import logging
import os
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)


class WindowsIntegrationUnavailable(RuntimeError):
    pass


class DpapiError(OSError):
    pass


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[DATA_BLOB, object]:
    if not data:
        return DATA_BLOB(0, None), None
    buffer = ctypes.create_string_buffer(data, len(data))
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def _crypt32():
    if os.name != "nt":
        raise WindowsIntegrationUnavailable("DPAPI está disponível somente no Windows.")
    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.restype = wintypes.HLOCAL
    return crypt32, kernel32


def protect_bytes(data: bytes, *, description: str = "") -> bytes:
    """CryptProtectData no escopo CurrentUser, entropy adicional nula."""
    crypt32, kernel32 = _crypt32()
    in_blob, _keep = _blob(data)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        description or None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise DpapiError(ctypes.get_last_error(), "CryptProtectData falhou")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def unprotect_bytes(data: bytes) -> bytes:
    """CryptUnprotectData compatível com ProtectedData.Unprotect(..., CurrentUser)."""
    crypt32, kernel32 = _crypt32()
    in_blob, _keep = _blob(data)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise DpapiError(ctypes.get_last_error(), "CryptUnprotectData falhou")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def protect_text_to_base64(text: str) -> str:
    return base64.b64encode(protect_bytes(text.encode("utf-8"))).decode("ascii")


def unprotect_text_from_base64(value: str) -> str:
    protected = base64.b64decode(value.strip(), validate=True)
    return unprotect_bytes(protected).decode("utf-8")


class DpapiTextStore:
    """Arquivo Base64 contendo blob DPAPI CurrentUser; nunca grava plaintext."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.is_file() and self.path.stat().st_size > 0

    def save(self, text: str) -> None:
        if not text:
            self.delete()
            return
        encoded = protect_text_to_base64(text)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(encoded, encoding="utf-8")
        tmp.replace(self.path)

    def load(self) -> str:
        if not self.exists():
            return ""
        return unprotect_text_from_base64(self.path.read_text(encoding="utf-8").strip())

    def delete(self) -> bool:
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return True
