from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_gitignore_content_if_web_upload_preserved_dotfile():
    path = ROOT / ".gitignore"

    if not path.is_file():
        return

    ignore = path.read_text(encoding="utf-8")
    assert "__pycache__/" in ignore
    assert "*.py[cod]" in ignore
    assert ".pytest_cache/" in ignore
    assert "tools/news_extractor/dist/" in ignore


def test_current_auth_fixtures_use_supported_server_version():
    for name in (
        "tests/unit/test_auth_client.py",
        "tests/unit/test_auth_password_change.py",
        "tests/unit/test_auth_password_force_v61.py",
        "tests/unit/test_auth_password_force_v62.py",
    ):
        source = _read(name)
        assert '"1.2.0"' in source


def test_extractor_test_matches_self_contained_qthread_contract():
    source = _read(
        "tests/unit/test_pass19_extractor_worker.py"
    )
    assert "assert page._download_worker is None" in source
    assert "assert page._download_thread is not None" in source


def test_tls_validation_uses_openssl_x509_parser():
    source = _read(
        "src/monitor_noticias/platform/tls.py"
    )
    assert "load_verify_locations" in source
    assert "_validate_x509_pem" in source


def test_process_destroy_waits_for_final_exit():
    source = _read(
        "src/monitor_noticias/platform/processes.py"
    )
    assert "_wait_finished" in source
    assert "_terminate_linux" in source
    assert "process.wait(" in source
