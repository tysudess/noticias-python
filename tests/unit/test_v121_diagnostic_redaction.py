from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

from monitor_noticias.diagnostics import (
    DiagnosticItem,
    DiagnosticReport,
    build_diagnostic_package,
    sanitize_log_text,
)


def test_sanitizer_masks_common_secret_assignment_formats() -> None:
    source = (
        'password=plain-password-123\n'
        'CENTRAL_PROXY_PASSWORD="proxy password with spaces"\n'
        '"access_token": "access-token-value-12345"\n'
        'api_key: api-key-value-12345\n'
        'email=operator@example.test\n'
        'session=raw-session-value-12345\n'
    )

    cleaned = sanitize_log_text(source)

    for secret in (
        "plain-password-123",
        "proxy password with spaces",
        "access-token-value-12345",
        "api-key-value-12345",
        "operator@example.test",
        "raw-session-value-12345",
    ):
        assert secret not in cleaned
    assert "CENTRAL_PROXY_PASSWORD" in cleaned
    assert '"access_token"' in cleaned


def test_sanitizer_masks_auth_headers_cookies_url_credentials_and_query_tokens() -> None:
    source = (
        "Authorization: Bearer bearer-token-123456789\n"
        "Proxy-Authorization: Basic c2VjcmV0LXBhc3M=\n"
        "Cookie: SID=session-cookie-987; session=second-cookie-765\n"
        "Set-Cookie: refresh_token=refresh-cookie-987; Secure\n"
        "GET https://proxy-user:proxy-pass@example.test/resource?api_key=key-secret-123&view=full\n"
        "GET https://example.test/path?access_token=query-token-12345&mode=compact\n"
    )

    cleaned = sanitize_log_text(source)

    for secret in (
        "bearer-token-123456789",
        "c2VjcmV0LXBhc3M=",
        "session-cookie-987",
        "second-cookie-765",
        "refresh-cookie-987",
        "proxy-user",
        "proxy-pass",
        "key-secret-123",
        "query-token-12345",
    ):
        assert secret not in cleaned
    assert "view=full" in cleaned
    assert "mode=compact" in cleaned


def test_sanitizer_masks_jwt_without_removing_unrelated_context() -> None:
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature123456789"
    cleaned = sanitize_log_text(f"Falha ao validar sessão {token}; timeout=10s")
    assert token not in cleaned
    assert "Falha ao validar sessão" in cleaned
    assert "timeout=10s" in cleaned


def test_diagnostic_zip_sanitizes_report_and_log_content(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "monitor-noticias.log").write_text(
        "proxy_password=local-proxy-secret\n"
        "Authorization: Bearer log-bearer-secret-123456\n"
        "Conexão falhou no host proxy.test\n",
        encoding="utf-8",
    )

    report = DiagnosticReport(
        generated_at="2026-10-27T15:00:00-03:00",
        app="Central Inteligente de Mídia",
        version="4.0.2",
        platform="Ubuntu Portable v4.0.2",
        items=[
            DiagnosticItem(
                key="auth_get",
                label="Apps Script GET",
                status="error",
                detail=(
                    "Falha em https://operator:report-secret@example.test/auth"
                    "?access_token=report-token-12345"
                ),
                duration_ms=12,
            )
        ],
    )

    archive_path = build_diagnostic_package(
        SimpleNamespace(logs=logs),
        report,
    )
    assert archive_path.is_file()

    with zipfile.ZipFile(archive_path) as archive:
        diagnostic = json.loads(archive.read("diagnostico.json"))
        log_text = archive.read("logs/monitor-noticias.log").decode("utf-8")

    exported_detail = diagnostic["items"][0]["detail"]
    for secret in (
        "report-secret",
        "operator:",
        "report-token-12345",
        "local-proxy-secret",
        "log-bearer-secret-123456",
    ):
        assert secret not in exported_detail + log_text
    assert "proxy.test" in log_text
    assert "Conexão falhou" in log_text
