from monitor_noticias.extractor.login_helper import (
    helper_filename,
)
from monitor_noticias.platform.current import (
    is_windows,
)


def test_globoplay_helper_name_matches_platform():
    if is_windows():
        assert helper_filename() == "GloboplayLoginHelper.exe"
    else:
        assert helper_filename() == "GloboplayLoginHelper"
