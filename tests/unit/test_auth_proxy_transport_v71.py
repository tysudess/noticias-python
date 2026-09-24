from __future__ import annotations

import json

from monitor_noticias.auth.client import AuthApiClient


def test_login_body_remains_json_text():
    payload = {
        "action": "login",
        "username": "u",
        "password": "p",
    }

    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    assert json.loads(body.decode("utf-8")) == payload


def test_auth_client_uses_proxy_friendly_content_type():
    # O Apps Script usa JSON.parse(e.postData.contents), então o tipo MIME
    # não precisa ser application/json para o corpo continuar sendo JSON.
    client = object.__new__(AuthApiClient)
    headers = AuthApiClient._headers(
        client,
        post=True,
    )

    assert headers["Content-Type"].startswith("text/plain")
