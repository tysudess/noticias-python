from __future__ import annotations

import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
)

from monitor_noticias.networking.proxy import ProxyConfig
from monitor_noticias.ui.login_dialog import ProxyDialog


class FakeProxySettings:
    def load(self):
        return ProxyConfig(
            enabled=True,
            host="proxy.test",
            port=6060,
            username="usuario",
            password="segredo123",
        )


class FakeRuntime:
    proxy_settings = FakeProxySettings()


def test_proxy_password_show_hide():
    app = (
        QApplication.instance()
        or QApplication([])
    )

    dialog = ProxyDialog(
        FakeRuntime()
    )

    assert (
        dialog.password.echoMode()
        == QLineEdit.EchoMode.Password
    )

    assert (
        dialog.password.text()
        == "segredo123"
    )

    dialog.show_password.setChecked(
        True
    )

    assert (
        dialog.password.echoMode()
        == QLineEdit.EchoMode.Normal
    )
    assert (
        dialog.show_password.text()
        == "Ocultar senha"
    )

    dialog.show_password.setChecked(
        False
    )

    assert (
        dialog.password.echoMode()
        == QLineEdit.EchoMode.Password
    )
    assert (
        dialog.show_password.text()
        == "Mostrar senha"
    )

    dialog.close()
    app.processEvents()
