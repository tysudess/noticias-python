from monitor_noticias.auth.client import AuthApiClient
from monitor_noticias.auth.device import DeviceIdentity
from monitor_noticias.networking.proxy import ProxyConfig


class FakeProxySettings:
    def __init__(self, config):
        self.config = config

    def load(self):
        return self.config

    def requests_proxies(self, config):
        return {
            "http": "http://proxy",
            "https": "http://proxy",
        }


def test_auth_uses_proxy_when_enabled():
    client = AuthApiClient(
        "https://example.invalid/exec",
        DeviceIdentity("id", "pc", "Windows"),
        proxy_settings=FakeProxySettings(
            ProxyConfig(
                enabled=True,
                host="proxy",
                port=6060,
                username="user",
                password="pass",
            )
        ),
    )

    assert client._proxies() == {
        "http": "http://proxy",
        "https": "http://proxy",
    }


def test_auth_direct_when_proxy_disabled():
    client = AuthApiClient(
        "https://example.invalid/exec",
        DeviceIdentity("id", "pc", "Windows"),
        proxy_settings=FakeProxySettings(
            ProxyConfig(enabled=False)
        ),
    )

    assert client._proxies() is None
