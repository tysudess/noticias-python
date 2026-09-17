import logging

from monitor_noticias.app.logging_setup import configure_logging
from monitor_noticias.app.paths import AppPaths


def test_logging_creates_file(tmp_path) -> None:
    paths = AppPaths(tmp_path)
    logger = configure_logging(paths, console=False)
    logger.info("foundation-test")
    for handler in logging.getLogger().handlers:
        handler.flush()
    log_file = paths.logs / "monitor-noticias.log"
    assert log_file.is_file()
    assert "foundation-test" in log_file.read_text(encoding="utf-8")
