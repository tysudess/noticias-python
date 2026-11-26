from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_run_installs_v168_after_v167_and_before_application_main():
    source = _read("run.py")
    v167 = source.index("install_art_studio_v167()")
    v168 = source.index("install_art_studio_v168()")
    main = source.index("from monitor_noticias.app.application import main")
    assert v167 < v168 < main


def test_guides_use_transparent_widget_overlay_not_scene_items():
    source = _read("src/monitor_noticias/ui/art_studio_v168.py")
    assert "class _GuidesOverlay(QWidget)" in source
    assert "WA_TransparentForMouseEvents" in source
    assert "WA_TranslucentBackground" in source
    assert "page.view.viewport()" in source
    assert "page.scene.addItem" not in source
    assert "_serialize_item" not in source


def test_guides_tab_offers_grid_composition_and_safe_margins():
    source = _read("src/monitor_noticias/ui/art_studio_v168.py")
    for token in (
        'tabs.addTab(tab, "▦  Guias")', "Mostrar grade", "Espaçamento da grade",
        "Divisões em terços", "Linha central horizontal e vertical",
        "Mostrar margem interna de 5%", "Ocultar todas as guias",
        "não aparecem na arte exportada",
    ):
        assert token in source


def test_overlay_tracks_resize_paint_and_zoom_events():
    source = _read("src/monitor_noticias/ui/art_studio_v168.py")
    assert "viewport.installEventFilter(self)" in source
    assert "page.view.installEventFilter(self)" in source
    assert "QEvent.Type.Resize" in source
    assert "QEvent.Type.Paint" in source
    assert "QEvent.Type.Wheel" in source
    assert "view.mapFromScene" in source


def test_guides_overlay_is_only_activated_by_view_controls():
    source = _read("src/monitor_noticias/ui/art_studio_v168.py")
    assert "def _read_config(page)" in source
    assert "def _sync_guides(page)" in source
    assert "overlay.set_config(config)" in source
    assert "page.v168_guide_config = config" in source
    assert "def _clear_guides(page)" in source


def test_installer_is_idempotent_and_runs_after_v167():
    source = _read("src/monitor_noticias/ui/art_studio_v168.py")
    assert "_v168_guides_installed" in source
    assert "_v168_installed" in source
    assert "_v168_integration_installed" in source
    assert "original_init(self, *args, **kwargs)" in source
