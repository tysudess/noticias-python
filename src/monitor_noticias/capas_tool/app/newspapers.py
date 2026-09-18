import json
from .config import bundle_dir
from .models import CoverEntry


def load_entries():
    data = json.loads((bundle_dir() / "assets" / "newspapers.json").read_text(encoding="utf-8"))
    out = []
    for row in data:
        if not row.get("enabled", True):
            continue
        out.append(CoverEntry(
            name=row["name"],
            mastheads=row.get("mastheads") or row.get("keywords") or [row["name"]],
            pdf_margin_percent=int(row.get("pdfMarginPercent", 2)),
        ))
    return out
