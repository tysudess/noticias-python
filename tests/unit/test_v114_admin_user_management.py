from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "tools" / "auth_server" / "apply_admin_users_v114_patch.py"


def _load_patch_module():
    spec = importlib.util.spec_from_file_location("admin_users_v114_patcher", PATCH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_apps_script_patch_adds_actions_and_is_idempotent():
    patcher = _load_patch_module()
    source = """const AUTH_VERSION = "1.3.0";
function doPost(e) {
    } else if (action === "admin_reset_password") {
      response = adminResetPassword_(request);
    } else {
      response = { ok: false, code: "UNKNOWN_ACTION" };
    }
}
function adminResetPassword_(request) {}

function publicUser_(user) {}
"""
    patched = patcher.patch_code(source)
    assert 'const AUTH_VERSION = "1.4.0";' in patched
    assert 'action === "admin_update_user"' in patched
    assert 'action === "admin_delete_user"' in patched
    assert "function adminUpdateUser_(request)" in patched
    assert "function adminDeleteUser_(request)" in patched
    assert "requireAdminSession_(request)" in patched
    assert "LAST_ADMIN_PROTECTED" in patched
    assert "revokeSessionsForUser_(username)" in patched
    assert patcher.patch_code(patched) == patched


def test_admin_api_exposes_edit_and_delete_actions():
    source = (ROOT / "src/monitor_noticias/auth/admin_api.py").read_text(encoding="utf-8")
    assert '"admin_update_user"' in source
    assert '"admin_delete_user"' in source
    assert "max(1, min(20, int(max_devices)))" in source


def test_ui_patch_adds_confirmation_and_management_buttons():
    source = (ROOT / "src/monitor_noticias/ui/admin_user_management_patch.py").read_text(encoding="utf-8")
    assert "Editar usuário" in source
    assert "Excluir usuário" in source
    assert "QMessageBox.question" in source
    assert "Por segurança" in source
    assert "install_admin_user_management_patch" in source


def test_composition_installs_management_patch_without_dropping_existing_patches():
    source = (ROOT / "src/monitor_noticias/app/composition.py").read_text(encoding="utf-8")
    for name in (
        "install_news_site_icons_patch",
        "install_source_list_logos_patch",
        "install_video_defense_term_patch",
        "install_video_preview_layout_patch",
        "install_video_timeline_side_controls_patch",
        "install_admin_user_management_patch",
    ):
        assert name in source


def test_server_guardrails_are_present():
    patcher = _load_patch_module()
    code = patcher.ADMIN_FUNCTIONS
    assert 'username === admin.user.username' in code
    assert 'countActiveAdmins_() <= 1' in code
    assert 'devices.getRange(i + 1, 7).setValue(false)' in code
    assert 'sheet.deleteRow(user.row)' in code
