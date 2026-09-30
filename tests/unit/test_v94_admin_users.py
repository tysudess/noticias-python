from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_admin_tab_is_installed_only_for_admin_profile():
    source = _read(
        "src/monitor_noticias/ui/admin_users_integration.py"
    )

    assert 'upper() != "ADMIN"' in source
    assert "AdminUsersPage" in source
    assert 'label_text="Administração"' in source


def test_application_installs_admin_after_authentication():
    source = _read(
        "src/monitor_noticias/app/application.py"
    )

    auth_pos = source.index(
        "install_authenticated_window("
    )
    admin_pos = source.index(
        "install_admin_users_page("
    )

    assert auth_pos < admin_pos


def test_admin_requests_use_current_token_and_device():
    source = _read(
        "src/monitor_noticias/auth/admin_api.py"
    )

    assert '"token": session.token' in source
    assert '"device_id": runtime.device.device_id' in source
    assert '"admin_list_users"' in source
    assert '"admin_create_user"' in source
    assert '"admin_reset_password"' in source


def test_server_rechecks_admin_profile_for_every_admin_action():
    source = _read(
        "tools/auth_server/Code.gs"
    )

    assert 'const AUTH_VERSION = "1.3.0";' in source
    assert 'action === "admin_list_users"' in source
    assert 'action === "admin_create_user"' in source
    assert 'action === "admin_reset_password"' in source

    assert "function requireAdminSession_" in source
    assert 'String(user.profile || "").toUpperCase() !== "ADMIN"' in source
    assert 'code: "ADMIN_REQUIRED"' in source


def test_admin_passwords_are_hashed_and_not_stored_in_plaintext_column():
    source = _read(
        "tools/auth_server/Code.gs"
    )

    create_start = source.index(
        "function adminCreateUser_"
    )
    reset_start = source.index(
        "function adminResetPassword_"
    )

    create_block = source[
        create_start:reset_start
    ]
    reset_block = source[
        reset_start:source.index(
            "function publicUser_"
        )
    ]

    assert "hashPassword_(" in create_block
    assert "hashPassword_(" in reset_block

    # NOVA_SENHA (coluna D) deve continuar vazia; salt/hash/iterações
    # são escritos diretamente.
    assert 'sheet.appendRow([' in create_block
    assert '      "",\n      salt,\n      passwordHash,\n      iterations,' in create_block
    assert '      "",\n      salt,\n      passwordHash,\n      iterations,' in reset_block

    assert "revokeSessionsForUser_(username)" in reset_block
    assert "setValue(true)" in reset_block


def test_admin_create_validates_username_profile_password_and_device_limit():
    source = _read(
        "tools/auth_server/Code.gs"
    )

    assert '/^[a-z0-9._-]{3,64}$/' in source
    assert "temporaryPassword.length < 8" in source
    assert '["ADMIN", "OPERADOR", "EDICAO", "CONSULTA"]' in source
    assert "Math.min(20" in source


def test_resetting_current_admin_is_redirected_to_my_account():
    source = _read(
        "tools/auth_server/Code.gs"
    )

    assert 'code: "ADMIN_SELF_RESET"' in source
    assert "use Minha conta" in source


def test_admin_ui_has_create_list_and_reset_controls():
    source = _read(
        "src/monitor_noticias/ui/admin_users_page.py"
    )

    assert "Criar novo usuário" in source
    assert "Usuários cadastrados" in source
    assert "Redefinir senha" in source
    assert "Sem data de validade" in source
    assert "Máx. dispositivos" in source
