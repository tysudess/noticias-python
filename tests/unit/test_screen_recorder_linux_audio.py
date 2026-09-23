from monitor_noticias.ui.screen_recorder_audio import AudioDevice
from monitor_noticias.ui.screen_recorder_linux import pulse_source_for


def test_pulse_source_is_extracted():
    device = AudioDevice(
        key="pulse:alsa_output.test.monitor",
        name="Sistema",
        index=-1,
        channels=2,
        rate=48000,
        kind="system",
    )

    assert (
        pulse_source_for(device)
        == "alsa_output.test.monitor"
    )
