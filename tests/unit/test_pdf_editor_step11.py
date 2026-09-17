from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication, QPushButton
from pypdf import PdfReader, PdfWriter
import pytest

from monitor_noticias.pdf_editor import PdfCrop, PdfEditorModel, PdfExportQuality, PdfItemKind
from monitor_noticias.ui.pdf_editor_page import PdfEditorPage


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def make_pdf(path: Path, sizes: list[tuple[float,float]]) -> Path:
    writer=PdfWriter()
    for width,height in sizes: writer.add_blank_page(width=width,height=height)
    with path.open("wb") as stream: writer.write(stream)
    return path


def make_image(path: Path, size=(300,200), color=(220,40,50)) -> Path:
    Image.new("RGB",size,color).save(path)
    return path


def test_import_exact_supported_types_and_single_pdf_expansion(tmp_path):
    pdf=make_pdf(tmp_path/"multi.pdf",[(200,300),(300,200)])
    png=make_image(tmp_path/"image.png")
    model=PdfEditorModel(tmp_path)
    assert model.import_files([pdf,png])==[]
    assert [p.kind for p in model.pages]==[PdfItemKind.PDF,PdfItemKind.PDF,PdfItemKind.IMAGE]
    assert [p.page_no for p in model.pages[:2]]==[0,1]
    assert model.selected_index==2


def test_blank_delete_reorder_undo_redo_and_limit(tmp_path):
    model=PdfEditorModel(tmp_path)
    for _ in range(33): model.create_blank_page()
    assert model.undo_count==30
    first=model.pages[0].uid; last=model.pages[-1].uid
    assert model.reorder(0,len(model.pages))
    assert model.pages[-1].uid==first
    assert model.undo(); assert model.pages[0].uid==first
    assert model.redo(); assert model.pages[-1].uid==first
    model.selected_index=len(model.pages)-1; assert model.delete_selected(); assert first not in {p.uid for p in model.pages}


def test_zoom_contract_and_visual_resize_values_are_representable(tmp_path):
    model=PdfEditorModel(tmp_path)
    assert model.set_zoom(.1)==.5
    assert model.set_zoom(4.0)==3.0
    for value in (.75,.90,1.0,1.10,1.25): assert model.set_zoom(value)==value


def test_crop_rotation_flip_reset_semantics(tmp_path):
    image=make_image(tmp_path/"img.png",(100,80))
    model=PdfEditorModel(tmp_path); model.import_files([image]); model.selected_index=0
    assert model.apply_crop(PdfCrop(.1,.1,.5,.5)); cropped=model.render_final_page(model.pages[0],120); assert cropped.size==(50,40)
    assert model.rotate_selected(90); assert model.pages[0].crop is None and model.pages[0].rotation==90
    assert model.flip_selected(); assert model.pages[0].flip_x is True and model.pages[0].crop is None


def test_export_preserves_page_order_and_fixed_width_contract(tmp_path):
    pdf=make_pdf(tmp_path/"source.pdf",[(200,400),(400,200)])
    image=make_image(tmp_path/"img.png",(320,160))
    model=PdfEditorModel(tmp_path); model.import_files([pdf,image]); out=model.export_pdf(tmp_path/"out.pdf",include_cover=False)
    reader=PdfReader(str(out)); assert len(reader.pages)==3
    assert float(reader.pages[0].mediabox.width)==pytest.approx(595.276,abs=.01)
    assert float(reader.pages[0].mediabox.height)==pytest.approx(1190.552,abs=.02)
    assert float(reader.pages[1].mediabox.height)==pytest.approx(297.638,abs=.02)
    assert float(reader.pages[2].mediabox.height)==pytest.approx(297.638,abs=.02)


def test_transformed_pdf_is_rasterized_at_high_quality_default(tmp_path):
    pdf=make_pdf(tmp_path/"source.pdf",[(200,300)])
    model=PdfEditorModel(tmp_path); model.import_files([pdf]); model.selected_index=0; model.apply_crop(PdfCrop(0,0,.5,1.0))
    out=model.export_pdf(tmp_path/"cropped.pdf",include_cover=False,quality=PdfExportQuality.HIGH)
    reader=PdfReader(str(out)); assert len(reader.pages)==1
    resources=reader.pages[0]["/Resources"]; assert "/XObject" in resources


def test_include_cover_adds_first_page_and_custom_cover_persists(tmp_path):
    cover=make_image(tmp_path/"cover.jpg",(200,400),(10,20,30)); model=PdfEditorModel(tmp_path); model.save_custom_cover(cover); model.create_blank_page()
    out=model.export_pdf(tmp_path/"cover-out.pdf",include_cover=True); assert len(PdfReader(str(out)).pages)==2
    reloaded=PdfEditorModel(tmp_path); assert reloaded.custom_cover==tmp_path/"data"/"capa_padrao_usuario.png"


def test_bundled_default_cover_asset_is_decodable_and_used():
    repo_root=Path(__file__).resolve().parents[2]
    asset=repo_root/"resources"/"pdf-default-cover.b64"
    assert asset.is_file() and asset.stat().st_size>1000
    model=PdfEditorModel(repo_root)
    image=model.current_cover_image()
    assert image.width>0 and image.height>0
    assert image.getbbox() is not None


def test_password_protected_pdf_is_not_bypassed(tmp_path):
    writer=PdfWriter(); writer.add_blank_page(width=200,height=300); writer.encrypt("secret")
    protected=tmp_path/"protected.pdf"
    with protected.open("wb") as stream: writer.write(stream)
    model=PdfEditorModel(tmp_path); errors=model.import_files([protected]); assert errors and "protegido" in errors[0].lower(); assert model.pages==[]


def test_ui_replaces_placeholder_and_exposes_only_active_controls(app,tmp_path):
    page=PdfEditorPage(tmp_path); texts={b.text() for b in page.findChildren(QPushButton)}
    for required in {"↑  Arquivos","PDF","✂  Cortar","⛶  Redimensionar","▤  Criar","▥  Excluir","↕  Ordenar","✔  GERAR PDF"}: assert required in texts
    assert not any("Girar" in text or "Imprimir" in text or "Dividir" in text or "Extrair páginas" in text for text in texts)
    assert page.model.zoom==1.0; page.deleteLater()
