from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import shutil
import sys
import urllib.request
from pathlib import Path


PACKAGE_NAMES = [
    "PySide6",
    "PySide6-Essentials",
    "PySide6-Addons",
    "shiboken6",
    "requests",
    "charset-normalizer",
    "idna",
    "urllib3",
    "certifi",
    "beautifulsoup4",
    "soupsieve",
    "lxml",
    "pypdf",
    "pypdfium2",
    "Pillow",
    "typing_extensions",
]

EXTERNAL_LICENSES = [
    (
        "ffmpeg/COPYING.GPLv3.txt",
        "https://raw.githubusercontent.com/FFmpeg/FFmpeg/n9.0/COPYING.GPLv3",
        "FFmpeg GPLv3 text for the n9.0 GPL/version3 build line",
    ),
    (
        "ffmpeg/LICENSE.md",
        "https://raw.githubusercontent.com/FFmpeg/FFmpeg/n9.0/LICENSE.md",
        "FFmpeg upstream licensing overview",
    ),
    (
        "yt-dlp-stable/THIRD_PARTY_LICENSES.txt",
        "https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/THIRD_PARTY_LICENSES.txt",
        "yt-dlp stable bundled executable third-party license aggregate",
    ),
    (
        "yt-dlp-stable/LICENSE.txt",
        "https://raw.githubusercontent.com/yt-dlp/yt-dlp/2026.08.19/LICENSE",
        "yt-dlp stable project license",
    ),
    (
        "yt-dlp-nightly/THIRD_PARTY_LICENSES.txt",
        "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/THIRD_PARTY_LICENSES.txt",
        "yt-dlp nightly bundled executable third-party license aggregate from upstream",
    ),
    (
        "yt-dlp-nightly/LICENSE.txt",
        "https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/LICENSE",
        "yt-dlp nightly project license from upstream",
    ),
    (
        "deno/LICENSE.md",
        "https://raw.githubusercontent.com/denoland/deno/v2.9.6/LICENSE.md",
        "Deno 2.9.6 MIT license",
    ),
]


def _safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def _copy_distribution_licenses(name: str, out_root: Path) -> dict:
    dist = metadata.distribution(name)
    version = dist.version
    copied: list[str] = []
    for item in dist.files or []:
        parts_lower = [p.lower() for p in item.parts]
        basename = item.name.lower()
        if not (
            "licenses" in parts_lower
            or basename.startswith("license")
            or basename.startswith("copying")
            or basename.startswith("notice")
        ):
            continue
        source = Path(dist.locate_file(item))
        if not source.is_file():
            continue
        destination = out_root / "python" / _safe_component(f"{name}-{version}") / Path(*item.parts[-3:])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination.relative_to(out_root.parent).as_posix())
    if not copied:
        raise RuntimeError(f"Nenhum texto de licença/notice encontrado na distribuição instalada: {name} {version}")
    return {
        "component": name,
        "version": version,
        "source": "installed package metadata/files",
        "files": sorted(copied),
    }


def _download(url: str, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "MonitorDeNoticias-Pass24-Compliance"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if len(data) < 80:
        raise RuntimeError(f"Texto de licença inesperadamente pequeno: {url}")
    destination.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("portable_root", type=Path)
    args = parser.parse_args()

    portable_root = args.portable_root.resolve()
    licenses = portable_root / "licenses"
    if licenses.exists():
        shutil.rmtree(licenses)
    licenses.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "schema": 1,
        "purpose": "Redistribution license/notice inventory for the packaged Windows portable",
        "python_runtime": {},
        "python_distributions": [],
        "external_components": [],
    }

    python_license_candidates = [
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE",
        Path(sys.prefix) / "LICENSE.txt",
        Path(sys.prefix) / "LICENSE",
    ]
    python_license = next((p for p in python_license_candidates if p.is_file()), None)
    if python_license is None:
        raise RuntimeError("Texto oficial da licença do runtime Python instalado não foi localizado.")
    py_dest = licenses / "python-runtime" / "LICENSE.txt"
    py_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(python_license, py_dest)
    manifest["python_runtime"] = {
        "version": sys.version.split()[0],
        "license_file": py_dest.relative_to(portable_root).as_posix(),
    }

    for package in PACKAGE_NAMES:
        manifest["python_distributions"].append(_copy_distribution_licenses(package, licenses))

    for relative, url, description in EXTERNAL_LICENSES:
        destination = licenses / relative
        digest = _download(url, destination)
        manifest["external_components"].append(
            {
                "description": description,
                "source_url": url,
                "file": destination.relative_to(portable_root).as_posix(),
                "sha256": digest,
            }
        )

    manifest_path = portable_root / "LICENSES-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not any(licenses.rglob("*")):
        raise RuntimeError("Diretório licenses ficou vazio.")
    print(f"PORTABLE_LICENSES_ROOT={licenses}")
    print(f"PORTABLE_LICENSES_MANIFEST={manifest_path}")
    print(f"PORTABLE_LICENSE_FILE_COUNT={sum(1 for p in licenses.rglob('*') if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
