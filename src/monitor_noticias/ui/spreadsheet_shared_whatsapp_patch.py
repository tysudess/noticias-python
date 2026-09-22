from __future__ import annotations

from pathlib import Path

from monitor_noticias.ui.spreadsheet_automation_page import (
    SpreadsheetAutomationPage,
)


_PATCHED = False


def install_spreadsheet_shared_whatsapp_patch() -> None:
    """Faz a Automação de Planilhas reutilizar o Chrome dedicado do Central.

    O patch é pequeno e propositalmente não reescreve
    spreadsheet_automation_page.py. Ele apenas acrescenta ao ambiente do
    runtime Electron os caminhos/endpoint da sessão compartilhada.
    """

    global _PATCHED
    if _PATCHED:
        return

    original = SpreadsheetAutomationPage._build_process_environment

    def patched_build_process_environment(
        self: SpreadsheetAutomationPage,
        launch_mode: str = "normal",
    ):
        env = original(self, launch_mode)

        if env is None:
            return None

        app_root = Path(self.app_root)
        data_dir = app_root / "data"
        profile_dir = data_dir / "whatsapp_chrome_profile"
        status_file = data_dir / "whatsapp_shared_status.json"
        pid_file = data_dir / "whatsapp_chrome.pid"

        data_dir.mkdir(parents=True, exist_ok=True)
        profile_dir.mkdir(parents=True, exist_ok=True)

        env.insert(
            "CENTRAL_WHATSAPP_SHARED_BROWSER",
            "1",
        )
        env.insert(
            "CENTRAL_WHATSAPP_BROWSER_URL",
            "http://127.0.0.1:9223",
        )
        env.insert(
            "CENTRAL_WHATSAPP_REMOTE_DEBUGGING_PORT",
            "9223",
        )
        env.insert(
            "CENTRAL_WHATSAPP_PROFILE_DIR",
            str(profile_dir),
        )
        env.insert(
            "CENTRAL_WHATSAPP_STATUS_FILE",
            str(status_file),
        )
        env.insert(
            "CENTRAL_WHATSAPP_PID_FILE",
            str(pid_file),
        )
        env.insert(
            "CENTRAL_WHATSAPP_WEB_URL",
            "https://web.whatsapp.com/",
        )

        return env

    SpreadsheetAutomationPage._build_process_environment = (
        patched_build_process_environment
    )

    _PATCHED = True
