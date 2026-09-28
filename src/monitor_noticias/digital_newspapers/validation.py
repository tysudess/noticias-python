from __future__ import annotations

from pathlib import Path
import unicodedata

from monitor_noticias.digital_newspapers.providers import DigitalNewspaperProvider


PDF_REJECT_MARKERS = (
    "politica de anticorrupcao",
    "política de anticorrupção",
    "comprovante de operacao",
    "comprovante de operação",
    "titulos outros bancos",
    "títulos outros bancos",
    "pagamento efetuado em",
    "codigo de barras",
    "código de barras",
)


def normalized_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(
        ch
        for ch in text
        if unicodedata.category(ch) != "Mn"
    )
    return " ".join(text.lower().split())


def validate_full_edition_pdf(
    path: Path,
    provider: DigitalNewspaperProvider,
) -> int:
    """Valida se um PDF parece uma edição completa do jornal.

    A validação é deliberadamente conservadora: um PDF válido qualquer não é
    suficiente. Ele precisa ter tamanho e quantidade de páginas compatíveis com
    uma edição completa e não pode conter marcadores inequívocos dos falsos
    positivos já observados (políticas internas, comprovantes bancários etc.).

    Ausência de texto extraível não reprova, porque algumas réplicas são
    compostas apenas por imagens de página.
    """

    if not path.is_file():
        raise RuntimeError("O arquivo PDF não foi criado.")

    size = path.stat().st_size
    min_bytes = max(1, int(provider.min_edition_bytes))
    if size < min_bytes:
        raise RuntimeError(
            "PDF descartado: arquivo pequeno demais para uma edição completa "
            f"({size / 1024:.0f} KB; mínimo {min_bytes / 1024:.0f} KB)."
        )

    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise RuntimeError(
                "O arquivo recebido não possui assinatura PDF válida."
            )

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = len(reader.pages)
    except Exception as exc:
        raise RuntimeError(
            "O arquivo recebido não passou na validação de PDF."
        ) from exc

    min_pages = max(1, int(provider.min_edition_pages))
    if pages < min_pages:
        raise RuntimeError(
            "PDF descartado: possui apenas "
            f"{pages} página(s); mínimo esperado para a edição: {min_pages}."
        )

    extracted: list[str] = []
    for page in reader.pages[: min(3, pages)]:
        try:
            extracted.append(page.extract_text() or "")
        except Exception:
            continue

    normalized = normalized_text("\n".join(extracted))
    if normalized:
        for marker in PDF_REJECT_MARKERS:
            if normalized_text(marker) in normalized:
                raise RuntimeError(
                    "PDF descartado: o conteúdo identificado não corresponde "
                    "a uma edição de jornal."
                )

    return pages
