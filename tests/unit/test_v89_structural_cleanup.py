from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_planilhas_is_not_part_of_active_navigation_anymore():
    sections = _read("src/monitor_noticias/ui/sections.py")
    main_window = _read("src/monitor_noticias/ui/main_window.py")
    application = _read("src/monitor_noticias/app/application.py")

    assert "SPREADSHEETS" not in sections
    assert "SpreadsheetAutomationPage" not in main_window
    assert "SPREADSHEETS" not in main_window
    assert "removed_integrations_guard" not in application


def test_no_fake_weather_and_platform_label_is_dynamic():
    main_window = _read("src/monitor_noticias/ui/main_window.py")
    version = _read("src/monitor_noticias/version.py")

    assert "29°C" not in main_window
    assert "platform_version_label" in main_window
    assert 'APP_VERSION = "4.0.2"' in version
    assert 'return "Windows Portable"' in version
    assert 'return "Ubuntu Portable"' in version


def test_ui_refresh_is_not_forced_twice_per_second():
    main_window = _read("src/monitor_noticias/ui/main_window.py")

    assert "setInterval(1000)" in main_window
    assert "_refresh_current_page_if_changed" in main_window
    assert "_state_signature" in main_window


def test_runtime_dependencies_do_not_ship_pytest():
    runtime = _read("requirements.txt")
    build = _read("requirements-build.txt")

    assert "pytest" not in runtime.lower()
    assert "pytest" in build.lower()


def test_project_version_comes_from_single_python_source():
    pyproject = _read("pyproject.toml")

    assert 'dynamic = ["version"]' in pyproject
    assert 'monitor_noticias.version.APP_VERSION' in pyproject
    assert 'version = "0.0.1"' not in pyproject


def test_windows_workflow_no_longer_packages_planilhas_and_runs_tests():
    workflow = _read(".github/workflows/build-portable.yml")
    lower = workflow.lower()

    assert "planilhas_runtime" not in lower
    assert "automacaoplanilhas" not in lower
    assert '"tools/spreadsheet_automation/**"' not in workflow
    assert "python -m compileall -q src" in workflow
    assert "python -m pytest -q tests/unit" in workflow
    assert "node --check tools/news_extractor/monitor-main.js" in workflow


def test_ubuntu_workflow_runs_tests_before_build():
    workflow = _read(".github/workflows/build-ubuntu.yml")

    assert "python -m compileall -q src" in workflow
    assert "python -m pytest -q tests/unit" in workflow
    assert "node --check tools/news_extractor/monitor-main.js" in workflow


def test_gitignore_blocks_generated_python_files():
    ignore = _read(".gitignore")

    assert "__pycache__/" in ignore
    assert "*.py[cod]" in ignore
    assert ".pytest_cache/" in ignore
    assert "tools/news_extractor/dist/" in ignore
