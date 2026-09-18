from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from datetime import date
from .config import bundle_dir, downloads_dir

MONTHS = ["JAN","FEV","MAR","ABR","MAI","JUN","JUL","AGO","SET","OUT","NOV","DEZ"]
MAX_WIDTH = 2000
JPEG_QUALITY = 93
PDF_PAGE_WIDTH = 2000


def build_filename(d: date) -> str:
    return f"{d.day:02d}{MONTHS[d.month-1]} - PRINCIPAIS CAPAS.pdf"


def _prepare(src: Path, out: Path, margin_percent: int):
    im = Image.open(src)
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, "white")
        if "A" in im.getbands():
            bg.paste(im, mask=im.getchannel("A"))
        else:
            bg.paste(im.convert("RGB"))
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > MAX_WIDTH:
        nh = max(1, round(im.height * MAX_WIDTH / im.width))
        im = im.resize((MAX_WIDTH, nh), Image.Resampling.LANCZOS)
    im.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=False, subsampling=0)
    pad = round(PDF_PAGE_WIDTH * max(0, min(6, margin_percent)) / 100)
    draw_w = PDF_PAGE_WIDTH - pad*2
    draw_h = max(1, round(im.height * draw_w / im.width))
    return dict(file=out, iw=im.width, ih=im.height, pw=PDF_PAGE_WIDTH, ph=draw_h+pad*2, pad=pad, dw=draw_w, dh=draw_h)


def _write_pdf(dest: Path, pages: list[dict]):
    offsets = [0] * (3*len(pages)+3)
    count = 0
    with open(dest, "wb") as f:
        def write(b):
            nonlocal count
            if isinstance(b, str): b = b.encode("latin-1")
            f.write(b); count += len(b)
        write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets[1]=count; write("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        offsets[2]=count
        kids="".join(f"{3+i*3} 0 R " for i in range(len(pages)))
        write(f"2 0 obj\n<< /Type /Pages /Count {len(pages)} /Kids [ {kids}] >>\nendobj\n")
        for i,p in enumerate(pages):
            po=3+i*3; co=po+1; io=po+2
            offsets[po]=count
            write(f"{po} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {p['pw']} {p['ph']}] /Resources << /XObject << /Im0 {io} 0 R >> >> /Contents {co} 0 R >>\nendobj\n")
            content=f"q\n{p['dw']} 0 0 {p['dh']} {p['pad']} {p['pad']} cm\n/Im0 Do\nQ\n".encode("ascii")
            offsets[co]=count; write(f"{co} 0 obj\n<< /Length {len(content)} >>\nstream\n"); write(content); write("endstream\nendobj\n")
            data=p['file'].read_bytes()
            offsets[io]=count
            write(f"{io} 0 obj\n<< /Type /XObject /Subtype /Image /Width {p['iw']} /Height {p['ih']} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Interpolate true /Length {len(data)} >>\nstream\n")
            write(data); write("\nendstream\nendobj\n")
        xref=count; total=len(offsets)-1
        write(f"xref\n0 {total+1}\n0000000000 65535 f \n")
        for i in range(1,total+1): write(f"{offsets[i]:010d} 00000 n \n")
        write(f"trailer\n<< /Size {total+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n")


def export_pdf(entries, target_date: date) -> Path:
    dest = downloads_dir() / build_filename(target_date)
    weekend = target_date.weekday() >= 5
    with TemporaryDirectory() as td:
        pages=[]; idx=0
        standard = bundle_dir()/"assets"/"principais_capas_cover.png"
        p=Path(td)/f"{idx:02d}.jpg"; idx+=1; pages.append(_prepare(standard,p,0))
        for e in entries:
            if not e.selected: continue
            if weekend and e.name == "VALOR ECONÔMICO": continue
            src=e.current_path
            if not src or not src.exists(): continue
            p=Path(td)/f"{idx:02d}.jpg"; idx+=1
            pages.append(_prepare(src,p,e.pdf_margin_percent))
        _write_pdf(dest,pages)
    return dest
