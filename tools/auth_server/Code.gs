const AUTH_VERSION = "1.1.3";

const SHEET_USERS = "USUARIOS";
const SHEET_DEVICES = "DISPOSITIVOS";
const SHEET_SESSIONS = "SESSOES";
const SHEET_LOGS = "LOGS";
const SHEET_CONFIG = "CONFIG";

const DEFAULT_PASSWORD_ITERATIONS = 8000;
const DEFAULT_SESSION_HOURS = 12;

const ALL_PERMISSIONS = [
  "home",
  "news",
  "videos",
  "demands",
  "sources",
  "history",
  "terms",
  "stop",
  "news_extractor",
  "covers",
  "pdf_editor",
  "extractor",
  "video_editor",
  "settings",
];

const PROFILE_PERMISSIONS = {
  ADMIN: ["*"],

  // V64: OPERADOR com todas as abas/funções ativas.
  OPERADOR: ["*"],

  EDICAO: [
    "home",
    "history",
    "covers",
    "pdf_editor",
    "extractor",
    "video_editor",
  ],

  CONSULTA: [
    "home",
    "news",
    "videos",
    "history",
  ],
};


function onOpen() {
  SpreadsheetApp
    .getUi()
    .createMenu("Central Auth")
    .addItem(
      "Preparar / atualizar planilha",
      "setupCentralAuth"
    )
    .addItem(
      "Processar senhas pendentes",
      "processarSenhasPendentes"
    )
    .addItem(
      "Revogar todas as sessões",
      "revogarTodasSessoes"
    )
    .addToUi();
}


function setupCentralAuth() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  ensureSheet_(
    ss,
    SHEET_USERS,
    [
      "USERNAME",
      "NOME",
      "STATUS",
      "NOVA_SENHA",
      "SALT",
      "SENHA_HASH",
      "ITERACOES",
      "PERFIL",
      "VALIDADE",
      "MAX_DISPOSITIVOS",
      "PERMISSOES",
      "CRIADO_EM",
      "ULTIMO_LOGIN",
      "OBSERVACOES",
      "TROCAR_SENHA",
    ]
  );

  ensureSheet_(
    ss,
    SHEET_DEVICES,
    [
      "USERNAME",
      "DEVICE_ID",
      "DEVICE_NAME",
      "OS",
      "PRIMEIRO_ACESSO",
      "ULTIMO_ACESSO",
      "ATIVO",
    ]
  );

  ensureSheet_(
    ss,
    SHEET_SESSIONS,
    [
      "TOKEN_HASH",
      "USERNAME",
      "DEVICE_ID",
      "CRIADO_EM",
      "EXPIRA_EM",
      "REVOGADO",
      "ULTIMA_VALIDACAO",
    ]
  );

  ensureSheet_(
    ss,
    SHEET_LOGS,
    [
      "DATA_HORA",
      "EVENTO",
      "USERNAME",
      "DEVICE_ID",
      "DETALHE",
    ]
  );

  const config = ensureSheet_(
    ss,
    SHEET_CONFIG,
    [
      "CHAVE",
      "VALOR",
    ]
  );

  setConfigIfMissing_(
    config,
    "PASSWORD_ITERATIONS",
    String(DEFAULT_PASSWORD_ITERATIONS)
  );

  setConfigIfMissing_(
    config,
    "SESSION_HOURS",
    String(DEFAULT_SESSION_HOURS)
  );

  ensurePepper_();

  const users = ss.getSheetByName(SHEET_USERS);

  if (
    users.getLastRow() === 1
  ) {
    users.appendRow(
      [
        "admin",
        "Administrador",
        "ATIVO",
        "",
        "",
        "",
        "",
        "ADMIN",
        "",
        2,
        "*",
        new Date(),
        "",
        "Digite uma senha na coluna NOVA_SENHA e use o menu Central Auth.",
        true,
      ]
    );
  }

  // V61: usuários que já possuíam senha antes da coluna TROCAR_SENHA
  // devem ser obrigados a trocar no próximo acesso.
  migratePasswordChangeFlags_(
    users
  );

  formatSheets_();

  SpreadsheetApp
    .getUi()
    .alert(
      "Central Auth",
      (
        "Estrutura criada.\n\n"
        + "1. Na aba USUARIOS, informe uma senha na coluna NOVA_SENHA.\n"
        + "2. Deixe TROCAR_SENHA vazio/TRUE para exigir troca no primeiro acesso.\n"
        + "3. Use Central Auth > Processar senhas pendentes.\n"
        + "4. Atualize a implantação do Web App."
      ),
      SpreadsheetApp.getUi().ButtonSet.OK
    );
}


function processarSenhasPendentes() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_USERS);

  if (!sheet) {
    throw new Error(
      "Execute setupCentralAuth() primeiro."
    );
  }

  const rows = sheet.getDataRange().getValues();

  if (rows.length <= 1) {
    return;
  }

  const iterations = getPasswordIterations_();
  let processed = 0;

  for (
    let rowIndex = 1;
    rowIndex < rows.length;
    rowIndex++
  ) {
    const row = rows[rowIndex];

    const username = normalizeUsername_(
      row[0]
    );

    const newPassword = String(
      row[3] || ""
    );

    if (
      !username
      || !newPassword
    ) {
      continue;
    }

    if (
      newPassword.length < 8
    ) {
      throw new Error(
        "A senha de "
        + username
        + " precisa ter pelo menos 8 caracteres."
      );
    }

    const salt = randomHex_(
      24
    );

    const passwordHash = hashPassword_(
      newPassword,
      salt,
      iterations
    );

    sheet.getRange(
      rowIndex + 1,
      4
    ).setValue("");

    sheet.getRange(
      rowIndex + 1,
      5
    ).setValue(
      salt
    );

    sheet.getRange(
      rowIndex + 1,
      6
    ).setValue(
      passwordHash
    );

    sheet.getRange(
      rowIndex + 1,
      7
    ).setValue(
      iterations
    );

    // V61: toda senha definida pelo administrador é considerada
    // temporária. O usuário precisa criar a própria senha no primeiro acesso.
    sheet.getRange(
      rowIndex + 1,
      15
    ).setValue(
      true
    );

    if (
      !sheet.getRange(
        rowIndex + 1,
        12
      ).getValue()
    ) {
      sheet.getRange(
        rowIndex + 1,
        12
      ).setValue(
        new Date()
      );
    }

    // Alterar a senha encerra sessões anteriores.
    revokeSessionsForUser_(
      username
    );

    logEvent_(
      "PASSWORD_CHANGED",
      username,
      "",
      "Senha processada pela planilha."
    );

    processed++;
  }

  SpreadsheetApp
    .getUi()
    .alert(
      "Central Auth",
      (
        processed
        + " senha(s) processada(s). "
        + "Nenhuma senha em texto puro foi mantida."
      ),
      SpreadsheetApp.getUi().ButtonSet.OK
    );
}


function revogarTodasSessoes() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_SESSIONS);

  if (!sheet || sheet.getLastRow() <= 1) {
    return;
  }

  const values = sheet.getDataRange().getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    sheet.getRange(
      i + 1,
      6
    ).setValue(
      true
    );
  }

  logEvent_(
    "ALL_SESSIONS_REVOKED",
    "",
    "",
    "Todas as sessões foram revogadas pelo administrador."
  );
}


function doGet() {
  return jsonResponse_(
    {
      ok: true,
      service: "Central Inteligente de Mídia Auth",
      version: AUTH_VERSION,
      status: "online",
    }
  );
}


function doPost(e) {
  try {
    const request = parseRequest_(e);
    const action = String(
      request.action || ""
    ).toLowerCase();

    if (action === "login") {
      return jsonResponse_(
        login_(
          request
        )
      );
    }

    if (action === "validate") {
      return jsonResponse_(
        validateSession_(
          request
        )
      );
    }

    if (action === "logout") {
      return jsonResponse_(
        logout_(
          request
        )
      );
    }

    if (action === "change_password") {
      return jsonResponse_(
        changePassword_(
          request
        )
      );
    }

    return jsonResponse_(
      {
        ok: false,
        code: "UNKNOWN_ACTION",
        message: "Ação inválida.",
      }
    );

  } catch (error) {
    return jsonResponse_(
      {
        ok: false,
        code: "SERVER_ERROR",
        message: String(
          error && error.message
          ? error.message
          : error
        ),
      }
    );
  }
}


function login_(request) {
  const lock = LockService.getScriptLock();

  lock.waitLock(
    20000
  );

  try {
    const username = normalizeUsername_(
      request.username
    );

    const password = String(
      request.password || ""
    );

    const deviceId = normalizeDeviceId_(
      request.device_id
    );

    const deviceName = String(
      request.device_name || ""
    ).slice(
      0,
      160
    );

    const osName = String(
      request.os || ""
    ).slice(
      0,
      120
    );

    if (
      !username
      || !password
      || !deviceId
    ) {
      return deny_(
        "INVALID_REQUEST",
        "Informe usuário, senha e dispositivo.",
        username,
        deviceId
      );
    }

    const user = findUser_(
      username
    );

    if (!user) {
      return deny_(
        "INVALID_CREDENTIALS",
        "Usuário ou senha inválidos.",
        username,
        deviceId
      );
    }

    const accessError = userAccessError_(
      user
    );

    if (accessError) {
      return deny_(
        accessError.code,
        accessError.message,
        username,
        deviceId
      );
    }

    if (
      !user.salt
      || !user.passwordHash
    ) {
      return deny_(
        "PASSWORD_NOT_CONFIGURED",
        "A senha deste usuário ainda não foi configurada.",
        username,
        deviceId
      );
    }

    const calculated = hashPassword_(
      password,
      user.salt,
      user.iterations
    );

    if (
      !secureEqual_(
        calculated,
        user.passwordHash
      )
    ) {
      return deny_(
        "INVALID_CREDENTIALS",
        "Usuário ou senha inválidos.",
        username,
        deviceId
      );
    }

    const deviceResult = authorizeDevice_(
      user,
      deviceId,
      deviceName,
      osName
    );

    if (!deviceResult.ok) {
      return deny_(
        deviceResult.code,
        deviceResult.message,
        username,
        deviceId
      );
    }

    revokeSessionsForDevice_(
      username,
      deviceId
    );

    const token = createSessionToken_();
    const tokenHash = hashToken_(
      token
    );

    const now = new Date();
    const expires = new Date(
      now.getTime()
      + getSessionHours_()
      * 60
      * 60
      * 1000
    );

    const sessions = getSheet_(
      SHEET_SESSIONS
    );

    sessions.appendRow(
      [
        tokenHash,
        username,
        deviceId,
        now,
        expires,
        false,
        now,
      ]
    );

    updateUserLastLogin_(
      user.row,
      now
    );

    logEvent_(
      "LOGIN_OK",
      username,
      deviceId,
      "Login autorizado."
    );

    return {
      ok: true,
      token: token,
      expires_at: expires.toISOString(),
      user: publicUser_(
        user
      ),
    };

  } finally {
    lock.releaseLock();
  }
}


function validateSession_(request) {
  const lock = LockService.getScriptLock();

  lock.waitLock(
    20000
  );

  try {
    const token = String(
      request.token || ""
    );

    const deviceId = normalizeDeviceId_(
      request.device_id
    );

    if (
      !token
      || !deviceId
    ) {
      return {
        ok: false,
        code: "SESSION_INVALID",
        message: "Sessão inválida.",
      };
    }

    const session = findSessionByToken_(
      token
    );

    if (!session) {
      return {
        ok: false,
        code: "SESSION_INVALID",
        message: "Sessão inválida ou encerrada.",
      };
    }

    if (
      session.revoked
      || session.deviceId !== deviceId
    ) {
      return {
        ok: false,
        code: "SESSION_REVOKED",
        message: "Sessão revogada.",
      };
    }

    const now = new Date();

    if (
      session.expiresAt.getTime()
      <= now.getTime()
    ) {
      setSessionRevoked_(
        session.row,
        true
      );

      return {
        ok: false,
        code: "SESSION_EXPIRED",
        message: "Sessão expirada. Faça login novamente.",
      };
    }

    const user = findUser_(
      session.username
    );

    if (!user) {
      setSessionRevoked_(
        session.row,
        true
      );

      return {
        ok: false,
        code: "USER_NOT_FOUND",
        message: "Usuário não encontrado.",
      };
    }

    const accessError = userAccessError_(
      user
    );

    if (accessError) {
      setSessionRevoked_(
        session.row,
        true
      );

      return {
        ok: false,
        code: accessError.code,
        message: accessError.message,
      };
    }

    touchSession_(
      session.row,
      now
    );

    touchDevice_(
      session.username,
      deviceId,
      now
    );

    return {
      ok: true,
      token: token,
      expires_at:
        session.expiresAt
        .toISOString(),
      user: publicUser_(
        user
      ),
    };

  } finally {
    lock.releaseLock();
  }
}



function changePassword_(request) {
  const lock = LockService.getScriptLock();

  lock.waitLock(
    20000
  );

  try {
    const token = String(
      request.token || ""
    );

    const deviceId = normalizeDeviceId_(
      request.device_id
    );

    const currentPassword = String(
      request.current_password || ""
    );

    const newPassword = String(
      request.new_password || ""
    );

    if (
      !token
      || !deviceId
      || !currentPassword
      || !newPassword
    ) {
      return {
        ok: false,
        code: "INVALID_REQUEST",
        message: "Informe a senha atual e a nova senha.",
      };
    }

    if (newPassword.length < 8) {
      return {
        ok: false,
        code: "PASSWORD_TOO_SHORT",
        message: "A nova senha precisa ter pelo menos 8 caracteres.",
      };
    }

    if (newPassword === currentPassword) {
      return {
        ok: false,
        code: "PASSWORD_REUSED",
        message: "A nova senha precisa ser diferente da senha atual.",
      };
    }

    const session = findSessionByToken_(
      token
    );

    if (!session) {
      return {
        ok: false,
        code: "SESSION_INVALID",
        message: "Sessão inválida ou encerrada.",
      };
    }

    if (
      session.revoked
      || session.deviceId !== deviceId
    ) {
      return {
        ok: false,
        code: "SESSION_REVOKED",
        message: "Sessão revogada.",
      };
    }

    const now = new Date();

    if (
      session.expiresAt.getTime()
      <= now.getTime()
    ) {
      setSessionRevoked_(
        session.row,
        true
      );

      return {
        ok: false,
        code: "SESSION_EXPIRED",
        message: "Sessão expirada. Faça login novamente.",
      };
    }

    const user = findUser_(
      session.username
    );

    if (!user) {
      setSessionRevoked_(
        session.row,
        true
      );

      return {
        ok: false,
        code: "USER_NOT_FOUND",
        message: "Usuário não encontrado.",
      };
    }

    const accessError = userAccessError_(
      user
    );

    if (accessError) {
      return {
        ok: false,
        code: accessError.code,
        message: accessError.message,
      };
    }

    const currentHash = hashPassword_(
      currentPassword,
      user.salt,
      user.iterations
    );

    if (
      !secureEqual_(
        currentHash,
        user.passwordHash
      )
    ) {
      return {
        ok: false,
        code: "CURRENT_PASSWORD_INVALID",
        message: "A senha atual está incorreta.",
      };
    }

    const iterations = getPasswordIterations_();
    const salt = randomHex_(24);
    const passwordHash = hashPassword_(
      newPassword,
      salt,
      iterations
    );

    const users = getSheet_(
      SHEET_USERS
    );

    users.getRange(
      user.row,
      4
    ).setValue("");

    users.getRange(
      user.row,
      5
    ).setValue(
      salt
    );

    users.getRange(
      user.row,
      6
    ).setValue(
      passwordHash
    );

    users.getRange(
      user.row,
      7
    ).setValue(
      iterations
    );

    users.getRange(
      user.row,
      15
    ).setValue(
      false
    );

    // Derruba todas as sessões anteriores, inclusive a usada para a troca.
    revokeSessionsForUser_(
      user.username
    );

    const newToken = createSessionToken_();
    const tokenHash = hashToken_(
      newToken
    );

    const expires = new Date(
      now.getTime()
      + getSessionHours_()
      * 60
      * 60
      * 1000
    );

    getSheet_(
      SHEET_SESSIONS
    ).appendRow(
      [
        tokenHash,
        user.username,
        deviceId,
        now,
        expires,
        false,
        now,
      ]
    );

    touchDevice_(
      user.username,
      deviceId,
      now
    );

    logEvent_(
      "PASSWORD_CHANGED_SELF",
      user.username,
      deviceId,
      "Senha alterada pelo próprio usuário no aplicativo."
    );

    const refreshedUser = findUser_(
      user.username
    );

    return {
      ok: true,
      token: newToken,
      expires_at: expires.toISOString(),
      user: publicUser_(
        refreshedUser
      ),
    };

  } finally {
    lock.releaseLock();
  }
}

function logout_(request) {
  const lock = LockService.getScriptLock();

  lock.waitLock(
    20000
  );

  try {
    const token = String(
      request.token || ""
    );

    if (!token) {
      return {
        ok: true,
      };
    }

    const session = findSessionByToken_(
      token
    );

    if (session) {
      setSessionRevoked_(
        session.row,
        true
      );

      logEvent_(
        "LOGOUT",
        session.username,
        session.deviceId,
        "Sessão encerrada."
      );
    }

    return {
      ok: true,
    };

  } finally {
    lock.releaseLock();
  }
}


function publicUser_(user) {
  return {
    auth_server_version: AUTH_VERSION,
    username: user.username,
    name: user.name,
    profile: user.profile,
    permissions: resolvePermissions_(
      user.profile,
      user.permissions
    ),
    must_change_password: Boolean(
      user.mustChangePassword
    ),
  };
}


function resolvePermissions_(
  profile,
  rawPermissions
) {
  const raw = String(
    rawPermissions || ""
  ).trim();

  let values = [];

  if (raw) {
    values = raw
      .split(",")
      .map(
        value =>
          value.trim()
          .toLowerCase()
      )
      .filter(Boolean);
  } else {
    values = (
      PROFILE_PERMISSIONS[
        String(
          profile || "CONSULTA"
        ).toUpperCase()
      ]
      || PROFILE_PERMISSIONS.CONSULTA
    );
  }

  if (
    values.indexOf("*")
    >= 0
  ) {
    return ALL_PERMISSIONS.slice();
  }

  const allowed = {};

  ALL_PERMISSIONS.forEach(
    key => {
      allowed[key] = false;
    }
  );

  values.forEach(
    key => {
      if (
        ALL_PERMISSIONS.indexOf(
          key
        ) >= 0
      ) {
        allowed[key] = true;
      }
    }
  );

  // Início sempre pode existir depois do login.
  allowed.home = true;

  return ALL_PERMISSIONS.filter(
    key => allowed[key]
  );
}


function authorizeDevice_(
  user,
  deviceId,
  deviceName,
  osName
) {
  const sheet = getSheet_(
    SHEET_DEVICES
  );

  const values = sheet
    .getDataRange()
    .getValues();

  let activeCount = 0;
  let existingRow = 0;

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    const row = values[i];

    const rowUser = normalizeUsername_(
      row[0]
    );

    const rowDevice = normalizeDeviceId_(
      row[1]
    );

    const active = asBoolean_(
      row[6],
      true
    );

    if (
      rowUser !== user.username
    ) {
      continue;
    }

    if (active) {
      activeCount++;
    }

    if (
      rowDevice === deviceId
    ) {
      existingRow = i + 1;

      if (!active) {
        return {
          ok: false,
          code: "DEVICE_BLOCKED",
          message: "Este computador foi bloqueado pelo administrador.",
        };
      }
    }
  }

  const now = new Date();

  if (existingRow) {
    sheet.getRange(
      existingRow,
      3
    ).setValue(
      deviceName
    );

    sheet.getRange(
      existingRow,
      4
    ).setValue(
      osName
    );

    sheet.getRange(
      existingRow,
      6
    ).setValue(
      now
    );

    return {
      ok: true,
    };
  }

  const maxDevices = Math.max(
    1,
    Number(
      user.maxDevices || 1
    )
  );

  if (
    activeCount
    >= maxDevices
  ) {
    return {
      ok: false,
      code: "DEVICE_LIMIT",
      message:
        "Este usuário atingiu o limite de computadores autorizados.",
    };
  }

  sheet.appendRow(
    [
      user.username,
      deviceId,
      deviceName,
      osName,
      now,
      now,
      true,
    ]
  );

  logEvent_(
    "DEVICE_ADDED",
    user.username,
    deviceId,
    (
      deviceName
      + " / "
      + osName
    )
  );

  return {
    ok: true,
  };
}


function userAccessError_(
  user
) {
  if (
    String(
      user.status || ""
    ).toUpperCase()
    !== "ATIVO"
  ) {
    return {
      code: "USER_BLOCKED",
      message: "Usuário bloqueado ou inativo.",
    };
  }

  if (user.expiresAt) {
    const expiration = new Date(
      user.expiresAt
    );

    if (
      !isNaN(
        expiration.getTime()
      )
    ) {
      const endOfDay = new Date(
        expiration
      );

      endOfDay.setHours(
        23,
        59,
        59,
        999
      );

      if (
        Date.now()
        > endOfDay.getTime()
      ) {
        return {
          code: "USER_EXPIRED",
          message: "O acesso deste usuário expirou.",
        };
      }
    }
  }

  return null;
}


function passwordChangeRequired_(
  row
) {
  const raw = row[14];

  if (
    raw === ""
    || raw === null
    || typeof raw === "undefined"
  ) {
    return Boolean(
      String(
        row[5] || ""
      ).trim()
    );
  }

  return asBoolean_(
    raw,
    true
  );
}


function migratePasswordChangeFlags_(
  sheet
) {
  if (
    !sheet
    || sheet.getLastRow() <= 1
  ) {
    return 0;
  }

  const values = sheet
    .getDataRange()
    .getValues();

  let migrated = 0;

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    const row = values[i];
    const username = normalizeUsername_(
      row[0]
    );
    const passwordHash = String(
      row[5] || ""
    ).trim();
    const raw = row[14];

    if (
      !username
      || !passwordHash
    ) {
      continue;
    }

    if (
      raw === ""
      || raw === null
      || typeof raw === "undefined"
    ) {
      sheet.getRange(
        i + 1,
        15
      ).setValue(
        true
      );

      migrated++;

      logEvent_(
        "PASSWORD_CHANGE_REQUIRED_MIGRATION",
        username,
        "",
        "Usuário existente marcado para troca obrigatória de senha."
      );
    }
  }

  return migrated;
}


function findUser_(
  username
) {
  const sheet = getSheet_(
    SHEET_USERS
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    const row = values[i];

    if (
      normalizeUsername_(
        row[0]
      ) !== username
    ) {
      continue;
    }

    return {
      row: i + 1,
      username: username,
      name: String(
        row[1] || username
      ),
      status: String(
        row[2] || ""
      ),
      salt: String(
        row[4] || ""
      ),
      passwordHash: String(
        row[5] || ""
      ),
      iterations: Math.max(
        1,
        Number(
          row[6]
          || getPasswordIterations_()
        )
      ),
      profile: String(
        row[7] || "CONSULTA"
      ).toUpperCase(),
      expiresAt: row[8] || null,
      maxDevices: Math.max(
        1,
        Number(
          row[9] || 1
        )
      ),
      permissions: String(
        row[10] || ""
      ),
      mustChangePassword: passwordChangeRequired_(
        row
      ),
    };
  }

  return null;
}


function updateUserLastLogin_(
  row,
  when
) {
  getSheet_(
    SHEET_USERS
  )
  .getRange(
    row,
    13
  )
  .setValue(
    when
  );
}


function findSessionByToken_(
  token
) {
  const tokenHash = hashToken_(
    token
  );

  const sheet = getSheet_(
    SHEET_SESSIONS
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    const row = values[i];

    if (
      !secureEqual_(
        String(
          row[0] || ""
        ),
        tokenHash
      )
    ) {
      continue;
    }

    return {
      row: i + 1,
      username: normalizeUsername_(
        row[1]
      ),
      deviceId: normalizeDeviceId_(
        row[2]
      ),
      createdAt: new Date(
        row[3]
      ),
      expiresAt: new Date(
        row[4]
      ),
      revoked: asBoolean_(
        row[5],
        false
      ),
    };
  }

  return null;
}


function revokeSessionsForUser_(
  username
) {
  const sheet = getSheet_(
    SHEET_SESSIONS
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      normalizeUsername_(
        values[i][1]
      ) === username
    ) {
      sheet.getRange(
        i + 1,
        6
      ).setValue(
        true
      );
    }
  }
}


function revokeSessionsForDevice_(
  username,
  deviceId
) {
  const sheet = getSheet_(
    SHEET_SESSIONS
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      normalizeUsername_(
        values[i][1]
      ) === username
      && normalizeDeviceId_(
        values[i][2]
      ) === deviceId
    ) {
      sheet.getRange(
        i + 1,
        6
      ).setValue(
        true
      );
    }
  }
}


function setSessionRevoked_(
  row,
  revoked
) {
  getSheet_(
    SHEET_SESSIONS
  )
  .getRange(
    row,
    6
  )
  .setValue(
    Boolean(
      revoked
    )
  );
}


function touchSession_(
  row,
  when
) {
  getSheet_(
    SHEET_SESSIONS
  )
  .getRange(
    row,
    7
  )
  .setValue(
    when
  );
}


function touchDevice_(
  username,
  deviceId,
  when
) {
  const sheet = getSheet_(
    SHEET_DEVICES
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      normalizeUsername_(
        values[i][0]
      ) === username
      && normalizeDeviceId_(
        values[i][1]
      ) === deviceId
    ) {
      sheet.getRange(
        i + 1,
        6
      ).setValue(
        when
      );
      return;
    }
  }
}


function deny_(
  code,
  message,
  username,
  deviceId
) {
  logEvent_(
    "LOGIN_DENIED",
    username || "",
    deviceId || "",
    (
      String(
        code
      )
      + ": "
      + String(
        message
      )
    )
  );

  return {
    ok: false,
    code: code,
    message: message,
  };
}


function logEvent_(
  event,
  username,
  deviceId,
  detail
) {
  try {
    getSheet_(
      SHEET_LOGS
    )
    .appendRow(
      [
        new Date(),
        String(
          event || ""
        ),
        String(
          username || ""
        ),
        String(
          deviceId || ""
        ),
        String(
          detail || ""
        ).slice(
          0,
          800
        ),
      ]
    );
  } catch (error) {
    console.error(
      error
    );
  }
}


function parseRequest_(
  e
) {
  if (
    !e
    || !e.postData
    || !e.postData.contents
  ) {
    throw new Error(
      "Corpo da requisição ausente."
    );
  }

  return JSON.parse(
    e.postData.contents
  );
}


function jsonResponse_(
  payload
) {
  return ContentService
    .createTextOutput(
      JSON.stringify(
        payload
      )
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );
}


function normalizeUsername_(
  value
) {
  return String(
    value || ""
  )
  .trim()
  .toLowerCase();
}


function normalizeDeviceId_(
  value
) {
  return String(
    value || ""
  )
  .trim()
  .toLowerCase()
  .replace(
    /[^a-z0-9_-]/g,
    ""
  )
  .slice(
    0,
    128
  );
}


function asBoolean_(
  value,
  fallback
) {
  if (
    value === true
    || String(
      value
    ).toLowerCase()
    === "true"
  ) {
    return true;
  }

  if (
    value === false
    || String(
      value
    ).toLowerCase()
    === "false"
  ) {
    return false;
  }

  return Boolean(
    fallback
  );
}


function getPasswordIterations_() {
  const value = Number(
    getConfig_(
      "PASSWORD_ITERATIONS",
      String(
        DEFAULT_PASSWORD_ITERATIONS
      )
    )
  );

  return Math.max(
    1000,
    Math.min(
      30000,
      Math.floor(
        value
        || DEFAULT_PASSWORD_ITERATIONS
      )
    )
  );
}


function getSessionHours_() {
  const value = Number(
    getConfig_(
      "SESSION_HOURS",
      String(
        DEFAULT_SESSION_HOURS
      )
    )
  );

  return Math.max(
    1,
    Math.min(
      168,
      value
      || DEFAULT_SESSION_HOURS
    )
  );
}


function hashPassword_(
  password,
  salt,
  iterations
) {
  const pepper = ensurePepper_();

  const seed = (
    String(
      password
    )
    + "\u001f"
    + String(
      salt
    )
    + "\u001f"
    + pepper
  );

  let bytes = Utilities
    .newBlob(
      seed
    )
    .getBytes();

  for (
    let i = 0;
    i < iterations;
    i++
  ) {
    bytes = Utilities
      .computeDigest(
        Utilities.DigestAlgorithm.SHA_256,
        bytes
      );
  }

  return Utilities
    .base64Encode(
      bytes
    );
}


function hashToken_(
  token
) {
  const pepper = ensurePepper_();

  const bytes = Utilities
    .computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      String(
        token
      )
      + "\u001f"
      + pepper,
      Utilities.Charset.UTF_8
    );

  return Utilities
    .base64Encode(
      bytes
    );
}


function createSessionToken_() {
  const source = [
    Utilities.getUuid(),
    Utilities.getUuid(),
    String(
      Date.now()
    ),
    randomHex_(
      32
    ),
  ].join(
    "|"
  );

  const bytes = Utilities
    .computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      source,
      Utilities.Charset.UTF_8
    );

  return (
    Utilities
    .base64EncodeWebSafe(
      bytes
    )
    .replace(
      /=+$/g,
      ""
    )
    + "."
    + Utilities
      .getUuid()
      .replace(
        /-/g,
        ""
      )
  );
}


function secureEqual_(
  left,
  right
) {
  const a = String(
    left || ""
  );

  const b = String(
    right || ""
  );

  let diff = (
    a.length
    ^ b.length
  );

  const length = Math.max(
    a.length,
    b.length
  );

  for (
    let i = 0;
    i < length;
    i++
  ) {
    const ca = (
      i < a.length
      ? a.charCodeAt(
          i
        )
      : 0
    );

    const cb = (
      i < b.length
      ? b.charCodeAt(
          i
        )
      : 0
    );

    diff |= (
      ca
      ^ cb
    );
  }

  return diff === 0;
}


function randomHex_(
  bytes
) {
  let output = "";

  while (
    output.length
    < bytes * 2
  ) {
    const digest = Utilities
      .computeDigest(
        Utilities.DigestAlgorithm.SHA_256,
        (
          Utilities.getUuid()
          + "|"
          + Date.now()
          + "|"
          + Math.random()
        ),
        Utilities.Charset.UTF_8
      );

    output += digest
      .map(
        value => {
          const normalized = (
            value < 0
            ? value + 256
            : value
          );

          return normalized
            .toString(
              16
            )
            .padStart(
              2,
              "0"
            );
        }
      )
      .join("");
  }

  return output.slice(
    0,
    bytes * 2
  );
}


function ensurePepper_() {
  const props = PropertiesService
    .getScriptProperties();

  let pepper = props.getProperty(
    "AUTH_PASSWORD_PEPPER"
  );

  if (!pepper) {
    pepper = randomHex_(
      32
    );

    props.setProperty(
      "AUTH_PASSWORD_PEPPER",
      pepper
    );
  }

  return pepper;
}


function getSheet_(
  name
) {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName(
      name
    );

  if (!sheet) {
    throw new Error(
      "Aba "
      + name
      + " não encontrada. "
      + "Execute setupCentralAuth()."
    );
  }

  return sheet;
}


function ensureSheet_(
  ss,
  name,
  headers
) {
  let sheet = ss.getSheetByName(
    name
  );

  if (!sheet) {
    sheet = ss.insertSheet(
      name
    );
  }

  if (
    sheet.getLastRow()
    === 0
  ) {
    sheet.getRange(
      1,
      1,
      1,
      headers.length
    ).setValues(
      [
        headers,
      ]
    );
  } else {
    sheet.getRange(
      1,
      1,
      1,
      headers.length
    ).setValues(
      [
        headers,
      ]
    );
  }

  sheet.setFrozenRows(
    1
  );

  return sheet;
}


function formatSheets_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  [
    SHEET_USERS,
    SHEET_DEVICES,
    SHEET_SESSIONS,
    SHEET_LOGS,
    SHEET_CONFIG,
  ].forEach(
    name => {
      const sheet = ss.getSheetByName(
        name
      );

      if (!sheet) {
        return;
      }

      sheet.getRange(
        1,
        1,
        1,
        sheet.getLastColumn()
      )
      .setFontWeight(
        "bold"
      )
      .setBackground(
        "#0B2E63"
      )
      .setFontColor(
        "#FFFFFF"
      );

      sheet.autoResizeColumns(
        1,
        sheet.getLastColumn()
      );
    }
  );
}


function getConfig_(
  key,
  fallback
) {
  const sheet = getSheet_(
    SHEET_CONFIG
  );

  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      String(
        values[i][0] || ""
      ).trim()
      === key
    ) {
      return String(
        values[i][1] || fallback
      );
    }
  }

  return fallback;
}


function setConfigIfMissing_(
  sheet,
  key,
  value
) {
  const values = sheet
    .getDataRange()
    .getValues();

  for (
    let i = 1;
    i < values.length;
    i++
  ) {
    if (
      String(
        values[i][0] || ""
      ).trim()
      === key
    ) {
      return;
    }
  }

  sheet.appendRow(
    [
      key,
      value,
    ]
  );
}
