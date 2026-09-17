from __future__ import annotations

from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
import pytest

from monitor_noticias.pdf_editor import PDF_PAGE_WIDTH_PT, PdfEditorModel, PdfExportQuality


def test_pdf_v2_export_quality_constants_match_kotlin():
    assert [(q.label,q.dpi) for q in PdfExportQuality]==[("Alta (recomendado)",450),("Média",300),("Compacta",220)]
    assert PDF_PAGE_WIDTH_PT==pytest.approx(595.276)


def test_vector_export_does_not_silently_inherit_document_metadata_or_annotations(tmp_path):
    source=tmp_path/"source.pdf"; writer=PdfWriter(); writer.add_blank_page(width=300,height=400); writer.add_metadata({"/Title":"ORIGINAL","/Author":"AUTOR"}); writer.add_uri(0,"https://example.test",(10,10,100,30))
    with source.open("wb") as stream: writer.write(stream)
    model=PdfEditorModel(tmp_path); model.import_files([source]); out=model.export_pdf(tmp_path/"out.pdf",include_cover=False)
    result=PdfReader(str(out)); assert result.metadata.title in (None,""); assert result.metadata.author in (None,""); assert "/Annots" not in result.pages[0]


def test_image_import_is_single_item_and_keeps_original_pixel_aspect(tmp_path):
    image=tmp_path/"wide.webp"; Image.new("RGB",(500,125),(1,2,3)).save(image)
    model=PdfEditorModel(tmp_path); assert model.import_files([image])==[]; out=model.export_pdf(tmp_path/"wide.pdf",include_cover=False)
    page=PdfReader(str(out)).pages[0]; assert float(page.mediabox.width)==pytest.approx(595.276,abs=.01); assert float(page.mediabox.height)==pytest.approx(148.819,abs=.02)


def test_original_file_is_never_overwritten_by_edit_state(tmp_path):
    source=tmp_path/"source.pdf"; writer=PdfWriter(); writer.add_blank_page(width=200,height=300)
    with source.open("wb") as stream: writer.write(stream)
    before=source.read_bytes(); model=PdfEditorModel(tmp_path); model.import_files([source]); model.create_blank_page(); model.delete_selected(); model.export_pdf(tmp_path/"new.pdf",include_cover=False); assert source.read_bytes()==before


def test_no_split_extract_print_ocr_contract_was_added():
    names=set(dir(PdfEditorModel))
    forbidden={"split_pdf","extract_pages","print_pdf","ocr","compress_pdf","convert_pdf"}
    assert names.isdisjoint(forbidden)
