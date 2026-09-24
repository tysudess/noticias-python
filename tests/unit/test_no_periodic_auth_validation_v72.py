from pathlib import Path

def test_periodic_validation_removed():
    source = Path(
        "src/monitor_noticias/ui/auth_window_integration.py"
    ).read_text(encoding="utf-8")

    assert "_ValidationWorker" not in source
    assert "_auth_validation_timer" not in source
    assert "validate_periodically" not in source
    assert "QTimer" not in source
    assert "QThread" not in source
