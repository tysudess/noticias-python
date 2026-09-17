from pathlib import Path

from monitor_noticias.app.composition import AppContainer
from monitor_noticias.app.paths import AppPaths
from monitor_noticias.app.preferences import SharedPreferences
from monitor_noticias.repositories import NewsRepository, VideoRepository
from monitor_noticias.ui.runtime_controller import RuntimeUiController


def test_real_container_builds_all_runtime_services_with_automation_paused(tmp_path: Path):
    paths=AppPaths(tmp_path); paths.ensure_runtime_dirs()
    prefs=SharedPreferences(paths.data/"prefs"/"monitor_prefs.properties")
    prefs.update(desktop_automatic_monitoring=False)
    container=AppContainer.build(paths)
    try:
        assert isinstance(container.news_repository,NewsRepository)
        assert isinstance(container.video_repository,VideoRepository)
        assert isinstance(container.controller,RuntimeUiController)
        assert container.controller.search_available is True
        assert len(container.controller.video_sources)==134
        assert container.automation.settings.automatic_monitoring is False
    finally:
        container.close()
        container.close()
