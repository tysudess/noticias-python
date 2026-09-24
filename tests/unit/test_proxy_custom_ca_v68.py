from __future__ import annotations

from pathlib import Path
import ssl

from monitor_noticias.platform.tls import (
    normalize_ca_certificate,
)


def test_normalize_der_certificate_rejects_invalid(
    tmp_path: Path,
):
    source = (
        tmp_path
        / "invalid.cer"
    )
    source.write_bytes(
        b"not-a-certificate"
    )

    target = (
        tmp_path
        / "out.pem"
    )

    try:
        normalize_ca_certificate(
            source,
            target,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Certificado inválido deveria ser rejeitado."
        )
