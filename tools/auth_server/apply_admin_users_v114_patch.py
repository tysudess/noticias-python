from __future__ import annotations

import re
from pathlib import Path


AUTH_VERSION_RE = re.compile(r'const AUTH_VERSION = "\d+\.\d+\.\d+";')
DISPATCH_MARKER = '''    } else if (action === "admin_reset_password") {
      response = adminResetPassword_(request);
    } else {'''
DISPATCH_REPLACEMENT = '''    } else if (action === "admin_reset_password") {
      response = adminResetPassword_(request);
    } else if (action === "admin_update_user") {
      response = adminUpdateUser_(request);
    } else if (action === "admin_delete_user") {
      response = adminDeleteUser_(request);
    } else {'''


ADMIN_FUNCTIONS = r'''

/* -------------------------------------------------------------------------
 * V114 — Edição e exclusão de usuários pela Central
 * ------------------------------------------------------------------------- */

function countActiveAdmins_() {
  const rows = getSheet_(SHEET_USERS).getDataRange().getValues();
  let count = 0;

  for (let i = 1; i < rows.length; i++) {
    if (
      normalizeUsername_(rows[i][0])
      && String(rows[i][2] || "").trim().toUpperCase() === "ATIVO"
      && String(rows[i][7] || "").trim().toUpperCase() === "ADMIN"
    ) {
      count++;
    }
  }

  return count;
}


function adminUpdateUser_(request) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);

  try {
    const admin = requireAdminSession_(request);

    if (!admin.ok) {
      return admin.response;
    }

    const username = normalizeUsername_(request.username);

    if (!username) {
      return {
        ok: false,
        code: "USERNAME_REQUIRED",
        message: "Informe o usuário que será alterado.",
      };
    }

    if (username === admin.user.username) {
      return {
        ok: false,
        code: "ADMIN_SELF_UPDATE",
        message: "A conta administrativa usada nesta sessão é protegida contra alterações nesta tela.",
      };
    }

    const user = findUser_(username);

    if (!user) {
      return {
        ok: false,
        code: "USER_NOT_FOUND",
        message: "Usuário não encontrado.",
      };
    }

    const name = String(request.name || "").trim().slice(0, 160);
    const profile = String(request.profile || "").trim().toUpperCase();
    const status = String(request.status || "").trim().toUpperCase();

    if (!name) {
      return {
        ok: false,
        code: "NAME_REQUIRED",
        message: "Informe o nome do usuário.",
      };
    }

    if (["ADMIN", "OPERADOR", "EDICAO", "CONSULTA"].indexOf(profile) < 0) {
      return {
        ok: false,
        code: "PROFILE_INVALID",
        message: "Perfil de usuário inválido.",
      };
    }

    if (["ATIVO", "INATIVO", "BLOQUEADO"].indexOf(status) < 0) {
      return {
        ok: false,
        code: "STATUS_INVALID",
        message: "Situação inválida. Use ATIVO, INATIVO ou BLOQUEADO.",
      };
    }

    let validity;
    try {
      validity = parseAdminValidity_(request.validity);
    } catch (error) {
      return {
        ok: false,
        code: "VALIDITY_INVALID",
        message: String(error.message || error),
      };
    }

    let permissions;
    try {
      permissions = sanitizeAdminPermissions_(request.permissions);
    } catch (error) {
      return {
        ok: false,
        code: "PERMISSIONS_INVALID",
        message: String(error.message || error),
      };
    }

    const maxDevicesValue = Number(request.max_devices || 1);
    if (!isFinite(maxDevicesValue) || maxDevicesValue < 1) {
      return {
        ok: false,
        code: "DEVICE_LIMIT_INVALID",
        message: "O limite de dispositivos deve estar entre 1 e 20.",
      };
    }
    const maxDevices = Math.max(1, Math.min(20, Math.floor(maxDevicesValue)));

    const wasActiveAdmin = user.status.toUpperCase() === "ATIVO"
      && user.profile.toUpperCase() === "ADMIN";
    const willRemainActiveAdmin = status === "ATIVO" && profile === "ADMIN";

    if (wasActiveAdmin && !willRemainActiveAdmin && countActiveAdmins_() <= 1) {
      return {
        ok: false,
        code: "LAST_ADMIN_PROTECTED",
        message: "Não é permitido desativar ou rebaixar o último administrador ativo.",
      };
    }

    const sheet = getSheet_(SHEET_USERS);
    sheet.getRange(user.row, 2).setValue(name);
    sheet.getRange(user.row, 3).setValue(status);
    sheet.getRange(user.row, 8).setValue(profile);
    sheet.getRange(user.row, 9).setValue(validity);
    sheet.getRange(user.row, 10).setValue(maxDevices);
    sheet.getRange(user.row, 11).setValue(permissions);

    // Revoga sessões para que o usuário receba permissões e situação atualizadas.
    revokeSessionsForUser_(username);

    logEvent_(
      "ADMIN_USER_UPDATED",
      admin.user.username,
      admin.session.deviceId,
      "Usuário atualizado: " + username + " / perfil " + profile + " / situação " + status
    );

    const updated = findUser_(username);

    return {
      ok: true,
      user: updated ? {
        username: updated.username,
        name: updated.name,
        status: updated.status,
        profile: updated.profile,
        validity: dateToIsoDate_(updated.expiresAt),
        max_devices: updated.maxDevices,
        permissions: updated.permissions,
        must_change_password: updated.mustChangePassword,
      } : {
        username: username,
        name: name,
        status: status,
        profile: profile,
        validity: dateToIsoDate_(validity),
        max_devices: maxDevices,
        permissions: permissions,
      },
    };
  } finally {
    lock.releaseLock();
  }
}


function adminDeleteUser_(request) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);

  try {
    const admin = requireAdminSession_(request);

    if (!admin.ok) {
      return admin.response;
    }

    const username = normalizeUsername_(request.username);

    if (!username) {
      return {
        ok: false,
        code: "USERNAME_REQUIRED",
        message: "Informe o usuário que será excluído.",
      };
    }

    if (username === admin.user.username) {
      return {
        ok: false,
        code: "ADMIN_SELF_DELETE",
        message: "Não é permitido excluir a conta administrativa usada nesta sessão.",
      };
    }

    const user = findUser_(username);

    if (!user) {
      return {
        ok: false,
        code: "USER_NOT_FOUND",
        message: "Usuário não encontrado.",
      };
    }

    if (
      user.status.toUpperCase() === "ATIVO"
      && user.profile.toUpperCase() === "ADMIN"
      && countActiveAdmins_() <= 1
    ) {
      return {
        ok: false,
        code: "LAST_ADMIN_PROTECTED",
        message: "Não é permitido excluir o último administrador ativo.",
      };
    }

    // Encerra todas as sessões e desativa os dispositivos, preservando os
    // registros de auditoria e evitando reuso de uma autorização antiga.
    revokeSessionsForUser_(username);
    const devices = getSheet_(SHEET_DEVICES);
    const deviceRows = devices.getDataRange().getValues();

    for (let i = 1; i < deviceRows.length; i++) {
      if (normalizeUsername_(deviceRows[i][0]) === username) {
        devices.getRange(i + 1, 7).setValue(false);
      }
    }

    const sheet = getSheet_(SHEET_USERS);
    sheet.deleteRow(user.row);

    logEvent_(
      "ADMIN_USER_DELETED",
      admin.user.username,
      admin.session.deviceId,
      "Conta excluída: " + username + " / perfil anterior " + user.profile
    );

    return {
      ok: true,
      username: username,
      deleted: true,
      sessions_revoked: true,
      devices_deactivated: true,
    };
  } finally {
    lock.releaseLock();
  }
}
'''


def patch_code(source: str) -> str:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Code.gs vazio ou inválido.")

    text = source
    has_update_action = 'action === "admin_update_user"' in text
    has_delete_action = 'action === "admin_delete_user"' in text
    has_update_function = "function adminUpdateUser_(request)" in text
    has_delete_function = "function adminDeleteUser_(request)" in text

    if has_update_action and has_delete_action and has_update_function and has_delete_function:
        version = re.search(r'const AUTH_VERSION = "(\d+)\.(\d+)\.(\d+)";', text)
        if version and tuple(map(int, version.groups())) >= (1, 4, 0):
            return text

    version_match = AUTH_VERSION_RE.search(text)
    if not version_match:
        raise ValueError("Não encontrei AUTH_VERSION no Code.gs.")
    text = AUTH_VERSION_RE.sub('const AUTH_VERSION = "1.4.0";', text, count=1)

    has_update_action = 'action === "admin_update_user"' in text
    has_delete_action = 'action === "admin_delete_user"' in text
    if not (has_update_action and has_delete_action):
        if DISPATCH_MARKER not in text:
            raise ValueError(
                "Não encontrei o bloco admin_reset_password no doPost. "
                "O Code.gs pode ter mudado; não foi modificado."
            )
        text = text.replace(DISPATCH_MARKER, DISPATCH_REPLACEMENT, 1)

    has_update_function = "function adminUpdateUser_(request)" in text
    has_delete_function = "function adminDeleteUser_(request)" in text
    if not (has_update_function and has_delete_function):
        marker = "\n\nfunction publicUser_(user) {"
        if marker not in text:
            raise ValueError(
                "Não encontrei o ponto de inserção antes de publicUser_. "
                "O Code.gs pode ter mudado; confira o diff."
            )
        text = text.replace(marker, ADMIN_FUNCTIONS + marker, 1)

    return text


def main() -> int:
    path = Path(__file__).with_name("Code.gs")
    original = path.read_text(encoding="utf-8")
    updated = patch_code(original)
    if updated == original:
        print("Code.gs já contém as operações V114; nenhuma alteração necessária.")
        return 0
    path.write_text(updated, encoding="utf-8", newline="\n")
    print("Code.gs atualizado para Auth Server 1.4.0.")
    print("Confira com: git diff -- tools/auth_server/Code.gs")
    print("Depois publique uma NOVA versão do Web App do Apps Script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
