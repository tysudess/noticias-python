from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import ssl
import threading


log = logging.getLogger(__name__)

_LOCK = threading.Lock()
_INSTALLED = False
_LAST_ERROR = ""

_PEM_CERT_RE = re.compile(
    br"-----BEGIN CERTIFICATE-----\s+.*?-----END CERTIFICATE-----",
    re.DOTALL,
)


def install_system_trust_store() -> tuple[bool, str]:
    """Faz Python/Requests usar o repositório de CAs confiáveis do SO."""

    global _INSTALLED
    global _LAST_ERROR

    with _LOCK:
        if _INSTALLED:
            return True, "Trust store do sistema já está ativo."

        try:
            import truststore

            truststore.inject_into_ssl()

            _INSTALLED = True
            _LAST_ERROR = ""

            log.info(
                "TLS configurado para usar o trust store nativo do sistema."
            )

            return True, "Trust store nativo do sistema ativado."

        except Exception as exc:
            _LAST_ERROR = (
                str(exc)
                or exc.__class__.__name__
            )

            log.exception(
                "Não foi possível ativar o trust store nativo do sistema."
            )

            return (
                False,
                "Não foi possível ativar os certificados do sistema: "
                + _LAST_ERROR,
            )


def system_trust_store_active() -> bool:
    return bool(_INSTALLED)


def system_trust_store_error() -> str:
    return _LAST_ERROR


def normalize_ca_certificate(
    source: Path,
    target_pem: Path,
) -> Path:
    """Valida PEM/DER X.509 e grava uma cópia normalizada em PEM."""

    source = Path(source)
    target_pem = Path(target_pem)

    if not source.is_file():
        raise ValueError(
            "Arquivo de certificado não encontrado."
        )

    data = source.read_bytes()

    if not data:
        raise ValueError(
            "O arquivo de certificado está vazio."
        )

    if len(data) > 2_000_000:
        raise ValueError(
            "O arquivo de certificado é maior do que o esperado."
        )

    pem_blocks = _PEM_CERT_RE.findall(
        data
    )

    normalized: list[str] = []

    if pem_blocks:
        for raw in pem_blocks:
            text = raw.decode(
                "ascii",
                errors="strict",
            )

            # Valida a estrutura do certificado.
            ssl.PEM_cert_to_DER_cert(
                text
            )

            normalized.append(
                text.strip()
            )

    else:
        try:
            pem = ssl.DER_cert_to_PEM_cert(
                data
            )
        except Exception as exc:
            raise ValueError(
                (
                    "Formato de certificado não reconhecido. "
                    "Use um certificado X.509 em PEM ou DER "
                    "(.pem, .crt ou .cer)."
                )
            ) from exc

        # Confirma que o resultado é um certificado válido.
        ssl.PEM_cert_to_DER_cert(
            pem
        )
        normalized.append(
            pem.strip()
        )

    target_pem.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_pem.write_text(
        "\n".join(
            normalized
        )
        + "\n",
        encoding="ascii",
    )

    return target_pem


def build_combined_ca_bundle(
    custom_ca_pem: Path,
    output_bundle: Path,
) -> Path:
    """Combina CAs públicas do certifi com a CA corporativa selecionada."""

    import certifi

    custom_ca_pem = Path(
        custom_ca_pem
    )
    output_bundle = Path(
        output_bundle
    )

    if not custom_ca_pem.is_file():
        raise ValueError(
            "Certificado CA corporativo não encontrado."
        )

    base = Path(
        certifi.where()
    ).read_bytes()

    custom = (
        custom_ca_pem
        .read_bytes()
    )

    output_bundle.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_bundle.write_bytes(
        base.rstrip()
        + b"\n"
        + custom.lstrip()
    )

    return output_bundle


def activate_custom_ca(
    custom_ca_pem: Path,
    output_bundle: Path,
) -> Path:
    """Ativa um bundle CA adicional para Requests/OpenSSL."""

    bundle = build_combined_ca_bundle(
        custom_ca_pem,
        output_bundle,
    )

    os.environ[
        "REQUESTS_CA_BUNDLE"
    ] = str(bundle)

    os.environ[
        "SSL_CERT_FILE"
    ] = str(bundle)

    log.info(
        "CA corporativa ativada: %s",
        custom_ca_pem,
    )

    return bundle


def deactivate_custom_ca(
    output_bundle: Path,
) -> None:
    output_bundle = Path(
        output_bundle
    )

    target = str(
        output_bundle
    )

    for key in (
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
    ):
        if (
            os.environ.get(
                key
            )
            == target
        ):
            os.environ.pop(
                key,
                None,
            )
