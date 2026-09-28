from __future__ import annotations

from datetime import date
from pathlib import Path

from pypdf import PdfWriter

from monitor_noticias.digital_newspapers.providers import (
    CorreioBrazilienseProvider,
    DigitalNewspaperProvider,
    EstadaoProvider,
    GZHProvider,
)
from monitor_noticias.digital_newspapers.validation import (
    validate_full_edition_pdf,
)


ROOT = Path(__file__).resolve().parents[2]


def _blank_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)


def test_v81_correio_returns_to_v78_direct_all_pdf():
    provider = CorreioBrazilienseProvider()
    assert provider.supports_direct_pdf
    assert not provider.supports_pagewise_pdf
    assert provider.direct_pdf_url(date(2026, 9, 28)).endswith(
        "/correiobraziliense/2026/09/28/all.pdf"
    )


def test_v81_full_edition_validator_rejects_short_false_positives(tmp_path):
    path = tmp_path / "wrong.pdf"
    _blank_pdf(path, 7)

    for provider in (EstadaoProvider(), GZHProvider()):
        try:
            validate_full_edition_pdf(path, provider)
        except RuntimeError as exc:
            assert "descartado" in str(exc).lower()
        else:
            raise AssertionError("PDF curto foi aceito como edição completa")


def test_v81_validator_accepts_a_valid_shape_when_provider_limits_match(tmp_path):
    path = tmp_path / "edition.pdf"
    _blank_pdf(path, 3)
    provider = DigitalNewspaperProvider(
        id="fixture",
        name="Fixture",
        edition_url="https://example.test/edition",
        domains=("example.test",),
        edition_kind="Teste",
        download_strategy="official_pdf",
        min_edition_pages=3,
        min_edition_bytes=1,
    )
    assert validate_full_edition_pdf(path, provider) == 3


def test_v81_browser_requires_explicit_edition_intent_before_pdf_download():
    source = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "browser.py"
    ).read_text(encoding="utf-8")

    assert "mode:'click_candidate'" in source
    assert "def _candidate_looks_like_edition(" in source
    assert "self._edition_download_armed" in source
    assert "PDF ignorado" in source
    assert "validate_full_edition_pdf" in source


def test_v81_credentials_are_local_secure_store_not_source_secrets():
    storage = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "storage.py"
    ).read_text(encoding="utf-8")
    page = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "ui"
        / "digital_newspapers_page.py"
    ).read_text(encoding="utf-8")
    browser = (
        ROOT
        / "src"
        / "monitor_noticias"
        / "digital_newspapers"
        / "browser.py"
    ).read_text(encoding="utf-8")

    assert "class SecureCredentialStore" in storage
    assert "credentials" in storage
    assert "digital-newspaper-credential:" in storage
    assert "Salvar acesso neste PC" in page
    assert "SecureCredentialStore" in page
    assert "_autofill_saved_credentials" in browser
    assert "auto_submit=self._auto_download_active" in browser


def test_v81_windows_spec_force_updates_and_verifies_exe_icon():
    spec = (ROOT / "MonitorDeNoticias.spec").read_text(encoding="utf-8")
    assert "BeginUpdateResourceW" in spec
    assert "UpdateResourceW" in spec
    assert "RT_GROUP_ICON" in spec
    assert "ExtractIconExW" in spec
