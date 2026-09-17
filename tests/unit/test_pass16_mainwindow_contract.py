from pathlib import Path


def test_main_window_source_coordinates_tool_shutdown():
    source = (Path(__file__).resolve().parents[2] / "src" / "monitor_noticias" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "extractor.shutdown()" in source
    assert "video_editor.shutdown()" in source
    assert source.index("extractor.shutdown()") < source.index("self.controller.close()")
    assert source.index("video_editor.shutdown()") < source.index("self.controller.close()")
