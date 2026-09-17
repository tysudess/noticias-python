from __future__ import annotations

import re
import unicodedata


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_marks).strip()


def compact(value: str) -> str:
    return normalize(value).replace(" ", "")
