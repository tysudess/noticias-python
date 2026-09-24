from monitor_noticias.networking.proxy import (
    ProxyConfig,
    corporate_tls_compatibility,
)


def test_tls_compatibility_is_restricted():
    assert corporate_tls_compatibility(
        ProxyConfig(
            enabled=True,
            host="proxy-7dn.mb",
            port=6060,
            username="u",
            password="p",
        )
    )

    assert not corporate_tls_compatibility(
        ProxyConfig(
            enabled=False,
            host="proxy-7dn.mb",
            port=6060,
            username="u",
            password="p",
        )
    )

    assert not corporate_tls_compatibility(
        ProxyConfig(
            enabled=True,
            host="outro-proxy",
            port=6060,
            username="u",
            password="p",
        )
    )

    assert not corporate_tls_compatibility(
        ProxyConfig(
            enabled=True,
            host="proxy-7dn.mb",
            port=8080,
            username="u",
            password="p",
        )
    )
