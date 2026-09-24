from monitor_noticias.auth.client import AuthApiError, _version_tuple


def test_auth_server_v62_required():
    assert _version_tuple("1.1.1") < (1, 1, 2)
    assert _version_tuple("1.1.2") >= (1, 1, 2)
