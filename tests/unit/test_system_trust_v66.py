from __future__ import annotations

import sys
import types

from monitor_noticias.platform import tls


def test_system_trust_store_install_is_idempotent(
    monkeypatch,
):
    calls = []

    fake = types.SimpleNamespace(
        inject_into_ssl=lambda: calls.append(
            "inject"
        )
    )

    monkeypatch.setitem(
        sys.modules,
        "truststore",
        fake,
    )

    monkeypatch.setattr(
        tls,
        "_INSTALLED",
        False,
    )
    monkeypatch.setattr(
        tls,
        "_LAST_ERROR",
        "",
    )

    first_ok, _ = (
        tls.install_system_trust_store()
    )
    second_ok, _ = (
        tls.install_system_trust_store()
    )

    assert first_ok
    assert second_ok
    assert calls == ["inject"]
    assert (
        tls.system_trust_store_active()
        is True
    )
