from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_art_studio_installs_before_main_application_import():
    source = _read("run.py")
    install_at = source.index("install_art_studio()")
    app_import_at = source.index("from monitor_noticias.app.application import main")
    assert install_at < app_import_at


def test_art_studio_is_added_to_existing_tools_navigation_group():
    source = _read("src/monitor_noticias/ui/art_studio_integration.py")
    assert '"FERRAMENTAS"' in source
    assert '"ART_STUDIO"' in source
    assert '"Estúdio de Artes"' in source
    assert "MainWindow._build_sidebar = build_sidebar_with_art_studio" in source


def test_art_studio_supports_core_editor_features_and_local_projects():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    for token in (
        "def add_image(",
        "def add_text(",
        "def add_shape(",
        "def duplicate_selected(",
        "def bring_to_front(",
        "def send_to_back(",
        "def save_project(",
        "def open_project(",
        "def export_art(",
        '"image_png_base64"',
        '".centralart"',
        '"JPEG"',
        '"PNG"',
        '".pdf"',
    ):
        assert token in source


def test_art_studio_uses_no_new_third_party_runtime_packages():
    source = _read("src/monitor_noticias/ui/art_studio_page.py")
    assert "from PIL import Image as PILImage" in source
    assert "import fabric" not in source.lower()
    assert "adobe" not in source.lower()
