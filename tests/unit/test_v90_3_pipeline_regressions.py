from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_settings_test_refreshes_page_before_startup_toggle():
    source = _read("tests/unit/test_ui_step9.py")
    assert "page.refresh(c.state)" in source
    assert "assert c.startup.calls" in source


def test_gitignore_is_not_a_release_blocker():
    v89 = _read("tests/unit/test_v89_structural_cleanup.py")
    v901 = _read("tests/unit/test_v90_1_pipeline_hotfix.py")

    assert "if not path.is_file():" in v89
    assert "if not path.is_file():" in v901


def test_linux_shutdown_handles_inherited_process_groups_safely():
    source = _read("src/monitor_noticias/platform/processes.py")

    assert "os.getpgid" in source
    assert "os.getpgrp" in source
    assert "process.terminate()" in source
    assert "isolated_group" in source
