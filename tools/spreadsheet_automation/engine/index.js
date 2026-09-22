const QRCode = require("qrcode");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");

const { Client, LocalAuth } = require("whatsapp-web.js");

/*
 * V22 — correção específica para:
 * "Protocol error (Runtime.callFunctionOn): Execution context was destroyed"
 *
 * O whatsapp-web.js chama Client.inject() durante a inicialização e também
 * depois de navegações internas do WhatsApp Web. Quando a página navega
 * exatamente no momento de uma evaluate(), o Puppeteer invalida o contexto
 * JavaScript e a Promise rejeita.
 *
 * A correção anterior destruía o browser e recriava a sessão; isso podia
 * deixar arquivos do perfil do Chrome ainda bloqueados (EPERM) e impedir
 * a geração do QR.
 *
 * Aqui a injeção é repetida NA MESMA página depois que a navegação estabiliza.
 * Não apaga, não renomeia e não recria a sessão por causa desse erro transitório.
 */
const _originalInject = Client.prototype.inject;

function isExecutionContextNavigationError(err) {
  const message = String(err?.message || err || "").toLowerCase();
  return (
    message.includes("execution context was destroyed")
    || message.includes("cannot find context with specified id")
    || message.includes("inspected target navigated or closed")
    || message.includes("most likely because of a navigation")
  );
}

Client.prototype.inject = async function (...args) {
  const maxAttempts = 8;
  let lastError = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await _originalInject.apply(this, args);
    } catch (err) {
      lastError = err;

      if (!isExecutionContextNavigationError(err)) {
        throw err;
      }

      const page = this.pupPage;
      if (!page || page.isClosed()) {
        throw err;
      }

      log(
        `WhatsApp Web navegou durante a inicialização. `
        + `Repetindo injeção sem reiniciar a sessão `
        + `(${attempt}/${maxAttempts})...`
      );

      emit("initialization_retry", {
        attempt,
        maxAttempts,
        message: String(err?.message || err || ""),
      });

      // Dá tempo para o novo execution context do Chromium ficar disponível.
      await new Promise(resolve => setTimeout(resolve, 700 + attempt * 250));

      try {
        await page.waitForFunction(
          "window.Debug?.VERSION != undefined",
          { timeout: 10000 }
        );
      } catch (_) {
        // A próxima tentativa de inject() faz a verificação novamente.
      }
    }
  }

  throw lastError;
};

const EVENT_PREFIX = "CENTRAL_EVENT:";

function emit(type, payload = {}) {
  try {
    process.stdout.write(
      EVENT_PREFIX
      + JSON.stringify({ type, ...payload })
      + "\n"
    );
  } catch (_) {}
}

function log(...args) {
  console.log(...args);
}

function error(...args) {
  console.error(...args);
}

const CONFIG_PATH =
  process.env.CONFIG_PATH
  || path.join(__dirname, "..", "config.default.json");

let CONFIG;

try {
  CONFIG = JSON.parse(
    fs.readFileSync(CONFIG_PATH, "utf8")
  );

  if (!CONFIG || typeof CONFIG !== "object") {
    throw new Error("JSON inválido");
  }
} catch (e) {
  emit(
    "engine_error",
    {
      message: `ERRO CONFIG: ${e.message}`,
    }
  );
  error("ERRO CONFIG:", e.message);
  process.exit(2);
}

const GRUPOS_ID = Array.isArray(CONFIG.grupos)
  ? CONFIG.grupos.map(String)
  : [];

const APPS_SCRIPT_URL =
  String(CONFIG.appsScriptUrl || "").trim();

const DIAGNOSTICO_GRUPOS =
  Boolean(CONFIG.diagnosticoGrupos);

// O proxy pertence somente ao Central.
const PROXY_ATIVO =
  process.env.CENTRAL_PROXY_ENABLED === "1";

const PROXY_HOST =
  String(
    process.env.CENTRAL_PROXY_HOST || ""
  ).trim();

const PROXY_PORT =
  Number(
    process.env.CENTRAL_PROXY_PORT || 0
  );

const PROXY_USUARIO =
  String(
    process.env.CENTRAL_PROXY_USERNAME || ""
  ).trim();

const PROXY_SENHA =
  String(
    process.env.CENTRAL_PROXY_PASSWORD || ""
  );

const STATE_DIR = path.resolve(
  process.env.CENTRAL_STATE_DIR
  || path.join(
    path.dirname(CONFIG_PATH),
    "state"
  )
);

const AUTH_DIR = path.resolve(
  process.env.CENTRAL_AUTH_DIR
  || path.join(
    path.dirname(CONFIG_PATH),
    "whatsapp-auth"
  )
);

fs.mkdirSync(
  STATE_DIR,
  { recursive: true }
);

fs.mkdirSync(
  AUTH_DIR,
  { recursive: true }
);

const SEEN_FILE =
  path.join(
    STATE_DIR,
    "mensagens-processadas.json"
  );

let seen = new Set();

try {
  if (fs.existsSync(SEEN_FILE)) {
    const arr = JSON.parse(
      fs.readFileSync(
        SEEN_FILE,
        "utf8"
      )
    );

    if (Array.isArray(arr)) {
      seen = new Set(arr);
    }
  }
} catch (_) {}

function jaProcessada(id) {
  return Boolean(
    id && seen.has(id)
  );
}

function marcarProcessada(id) {
  if (!id) {
    return;
  }

  seen.add(id);

  if (seen.size > 3000) {
    seen = new Set(
      Array.from(seen).slice(-2000)
    );
  }

  try {
    fs.writeFileSync(
      SEEN_FILE,
      JSON.stringify(
        Array.from(seen),
        null,
        2
      ),
      "utf8"
    );
  } catch (_) {}
}

function normalizarTexto(t) {
  return String(t || "")
    .normalize("NFD")
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
    .toLowerCase();
}

function limparTexto(t) {
  return String(t || "")
    .trim()
    .replace(
      /^\*+|\*+$/g,
      ""
    )
    .replace(
      /^_+|_+$/g,
      ""
    )
    .trim();
}

function descobrirGrupo(m) {
  return [
    m.to,
    m.from,
    m.id?.remote,
  ].find(
    id => GRUPOS_ID.includes(id)
  );
}

function extrairLink(t) {
  const m = String(t || "")
    .match(
      /https?:\/\/[^\s\])]+/i
    );

  return m
    ? m[0]
    : "";
}

function ehSomenteLink(t) {
  return /^https?:\/\/\S+$/i.test(
    String(t || "").trim()
  );
}

function ehData(t) {
  return /^\d{2}\/\d{2}\/\d{4}$/.test(
    limparTexto(t)
  );
}

function determinarAba(data) {
  const meses = [
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
  ];

  const m = limparTexto(data).match(
    /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/
  );

  if (!m) {
    const d = new Date();

    return (
      `${meses[d.getMonth()]}`
      + `${String(d.getFullYear()).slice(-2)}`
    );
  }

  const mes = Number(m[2]);
  const ano = Number(m[3]);

  if (
    mes < 1
    || mes > 12
    || ano < 2000
  ) {
    const d = new Date();

    return (
      `${meses[d.getMonth()]}`
      + `${String(d.getFullYear()).slice(-2)}`
    );
  }

  return (
    `${meses[mes - 1]}`
    + `${String(ano).slice(-2)}`
  );
}

function pareceAutor(t) {
  const c = limparTexto(t);

  if (
    !c
    || c.length > 60
    || /https?:\/\//i.test(c)
    || /[.?!]$/.test(c)
  ) {
    return false;
  }

  const p = c
    .split(/\s+/)
    .filter(Boolean);

  return (
    p.length >= 2
    && p.length <= 8
  );
}

function ehAssuntoInternacional(
  titulo,
  texto
) {
  const t = normalizarTexto(
    `${titulo} ${texto}`
  );

  const termos = [
    "estados unidos",
    "donald trump",
    "trump",
    "eua",
    "ucrania",
    "russia",
    "israel",
    "gaza",
    "ira",
    "faixa de gaza",
  ];

  return termos.some(
    x => new RegExp(
      `(^|[^a-z0-9])`
      + `${x.replace(/ /g, "\\s+")}`
      + `([^a-z0-9]|$)`,
      "i"
    ).test(t)
  );
}

function classificarAnalise(
  titulo,
  texto
) {
  if (
    ehAssuntoInternacional(
      titulo,
      texto
    )
  ) {
    return "NEUTRA";
  }

  const t = normalizarTexto(
    `${titulo} ${texto}`
  );

  const pos = [
    "sucesso",
    "resgate",
    "salvamento",
    "premio",
    "reconhecimento",
    "homenagem",
    "conquista",
    "beneficio",
    "apoio",
    "parceria",
    "modernizacao",
    "avanco",
    "cooperacao",
    "entrega",
    "melhoria",
    "fortalecimento",
    "excelencia",
  ];

  const neg = [
    "critica",
    "denuncia",
    "falha",
    "erro",
    "problema",
    "investigacao",
    "irregularidade",
    "crise",
    "prejuizo",
    "ataque",
    "condenacao",
    "corrupcao",
    "fraude",
    "falsificacao",
    "adulteracao",
    "desvio",
    "escandalo",
    "prisao",
    "acusacao",
    "crime",
    "ilegal",
    "negligencia",
    "fracasso",
    "dano",
    "ameaca",
    "risco",
    "violacao",
    "abuso",
    "omissao",
    "suspeita",
    "traficante",
    "faccao",
    "comando vermelho",
    "pcc",
  ];

  const raizes = [
    "fraud",
    "corrup",
    "falsific",
    "adulter",
    "irregular",
    "conden",
    "investig",
    "denunc",
    "neglig",
    "crimin",
    "desvi",
  ];

  let p = pos.reduce(
    (s, x) =>
      s + (t.includes(x) ? 1 : 0),
    0
  );

  let n =
    neg.reduce(
      (s, x) =>
        s + (t.includes(x) ? 1 : 0),
      0
    )
    + raizes.reduce(
      (s, x) =>
        s + (t.includes(x) ? 2 : 0),
      0
    );

  const tt = normalizarTexto(titulo);

  n +=
    neg.reduce(
      (s, x) =>
        s + (tt.includes(x) ? 2 : 0),
      0
    )
    + raizes.reduce(
      (s, x) =>
        s + (tt.includes(x) ? 3 : 0),
      0
    );

  return n > p
    ? "NEGATIVA"
    : p > n
      ? "POSITIVA"
      : "NEUTRA";
}

function classificarAssunto(
  veiculo,
  titulo,
  texto
) {
  if (
    ehAssuntoInternacional(
      titulo,
      texto
    )
  ) {
    return "OUTROS";
  }

  const t = normalizarTexto(
    `${veiculo} ${titulo} ${texto}`
  );

  const marinha = [
    "marinha do brasil",
    "marinha brasileira",
    "forca naval",
    "aviacao naval",
    "corpo de fuzileiros navais",
    "fuzileiros navais",
    "distrito naval",
    "amazonia azul",
    "autoridade maritima",
    "capitania dos portos",
    "navio da marinha",
    "navio-patrulha",
    "nam atlantico",
    "fragata",
    "corveta",
    "navio patrulha",
    "navio-aerodromo",
    "submarino da marinha",
    "esquadra brasileira",
  ];

  if (
    marinha.some(
      x => t.includes(x)
    )
  ) {
    return "MB";
  }

  const mil = [
    "forcas armadas",
    "exercito brasileiro",
    "aeronautica",
    "forca aerea brasileira",
    "militares",
    "militar",
    "generais",
    "general",
    "brigadeiro",
    "almirante",
  ];

  const pol = [
    "presidente da republica",
    "presidente lula",
    "governo federal",
    "congresso nacional",
    "senado",
    "camara dos deputados",
    "stf",
    "supremo tribunal federal",
    "ministro",
    "ministerio",
    "deputado",
    "senador",
    "eleicao",
    "politica",
    "partido",
    "planalto",
  ];

  const temMil = mil.some(
    x => t.includes(x)
  );

  if (
    temMil
    && pol.some(
      x => t.includes(x)
    )
  ) {
    return "FFAA(PLT)";
  }

  if (temMil) {
    return "FFAA";
  }

  return "OUTROS";
}

function interpretarVideo(texto) {
  const partes = String(texto || "")
    .trim()
    .split(/\s+-\s+/)
    .map(x => x.trim())
    .filter(Boolean);

  if (partes.length < 3) {
    return null;
  }

  const m = partes[0]
    .toUpperCase()
    .replace(/\s+/g, "")
    .match(
      /^(\d{1,2})(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)$/
    );

  if (!m) {
    return null;
  }

  const meses = {
    JAN: "01",
    FEV: "02",
    MAR: "03",
    ABR: "04",
    MAI: "05",
    JUN: "06",
    JUL: "07",
    AGO: "08",
    SET: "09",
    OUT: "10",
    NOV: "11",
    DEZ: "12",
  };

  return {
    data:
      `${m[1].padStart(2, "0")}/`
      + `${meses[m[2]]}/`
      + `${new Date().getFullYear()}`,
    veiculo: partes[1],
    titulo: partes
      .slice(2)
      .join(" - "),
    autor: "Não Informado",
    link: "Vídeo",
  };
}

function interpretarMensagem(texto) {
  const linhas = String(texto || "")
    .split(/\r?\n/)
    .map(x => x.trim())
    .filter(Boolean);

  const link = extrairLink(texto);

  if (!link) {
    return null;
  }

  const iLink = linhas.findIndex(
    x => x.includes(link)
  );

  if (iLink < 0) {
    return null;
  }

  const veiculo =
    limparTexto(
      linhas[iLink + 1] || ""
    );

  const titulo =
    limparTexto(
      linhas[iLink + 2] || ""
    );

  let iData = -1;

  for (
    let i = iLink + 3;
    i < linhas.length;
    i += 1
  ) {
    if (ehData(linhas[i])) {
      iData = i;
      break;
    }
  }

  const dataPublicacao =
    iData >= 0
      ? limparTexto(linhas[iData])
      : "";

  let autor = "";

  if (
    iData >= 0
    && iData - 1 > iLink + 2
  ) {
    const c =
      limparTexto(
        linhas[iData - 1]
      );

    if (pareceAutor(c)) {
      autor = c;
    }
  }

  return {
    link,
    veiculo,
    titulo,
    autor,
    dataPublicacao,
  };
}

function obterProxyAxios() {
  if (
    !PROXY_ATIVO
    || !PROXY_HOST
    || !PROXY_PORT
  ) {
    return undefined;
  }

  const proxy = {
    protocol: "http",
    host: PROXY_HOST,
    port: PROXY_PORT,
  };

  if (PROXY_USUARIO) {
    proxy.auth = {
      username: PROXY_USUARIO,
      password: PROXY_SENHA,
    };
  }

  return proxy;
}

function obterProxyArg() {
  return (
    PROXY_ATIVO
    && PROXY_HOST
    && PROXY_PORT
  )
    ? (
      `--proxy-server=http://`
      + `${PROXY_HOST}:`
      + `${PROXY_PORT}`
    )
    : null;
}

function localizarNavegador() {
  const candidatos = [
    process.env.CHROME_PATH,
    CONFIG.chromePath,
    path.join(
      process.cwd(),
      "chrome",
      "chrome.exe"
    ),
    process.env.PROGRAMFILES
      && path.join(
        process.env.PROGRAMFILES,
        "Google",
        "Chrome",
        "Application",
        "chrome.exe"
      ),
    process.env["PROGRAMFILES(X86)"]
      && path.join(
        process.env["PROGRAMFILES(X86)"],
        "Google",
        "Chrome",
        "Application",
        "chrome.exe"
      ),
    process.env.LOCALAPPDATA
      && path.join(
        process.env.LOCALAPPDATA,
        "Google",
        "Chrome",
        "Application",
        "chrome.exe"
      ),
    process.env.PROGRAMFILES
      && path.join(
        process.env.PROGRAMFILES,
        "Microsoft",
        "Edge",
        "Application",
        "msedge.exe"
      ),
    process.env["PROGRAMFILES(X86)"]
      && path.join(
        process.env["PROGRAMFILES(X86)"],
        "Microsoft",
        "Edge",
        "Application",
        "msedge.exe"
      ),
  ].filter(Boolean);

  return candidatos.find(
    p => {
      try {
        return fs.existsSync(p);
      } catch (_) {
        return false;
      }
    }
  );
}

const navegador =
  localizarNavegador();

try {
  const wwebVersion =
    require("whatsapp-web.js/package.json").version;
  log(
    "WHATSAPP-WEB.JS:",
    wwebVersion
  );
} catch (_) {}


emit(
  "engine_start",
  {
    groups: GRUPOS_ID.length,
  }
);

emit(
  "network",
  {
    mode:
      PROXY_ATIVO
        ? "PROXY"
        : "DIRECT",
    host:
      PROXY_ATIVO
        ? PROXY_HOST
        : "",
  }
);

emit(
  "browser",
  {
    path: navegador || "",
  }
);

log(
  "MODO DO NAVEGADOR: VISUAL CONTROLADO PELO CENTRAL"
);

if (navegador) {
  log(
    "NAVEGADOR:",
    navegador
  );
}

if (
  PROXY_ATIVO
  && PROXY_HOST
  && PROXY_PORT
) {
  log(
    `REDE: PROXY GERAL DO CENTRAL `
    + `${PROXY_HOST}:`
    + `${PROXY_PORT}`
  );

  log(
    PROXY_USUARIO
      ? "PROXY GERAL COM AUTENTICAÇÃO"
      : "PROXY GERAL SEM AUTENTICAÇÃO"
  );
} else {
  log(
    "REDE: CONEXÃO DIRETA "
    + "(PROXY GERAL DESATIVADO)"
  );
}

const chromeArgs = [
  "--no-sandbox",
  "--disable-setuid-sandbox",
  "--disable-gpu",
  "--disable-dev-shm-usage",
  "--disable-background-networking",
  "--disable-background-timer-throttling",
  "--disable-renderer-backgrounding",
  "--disable-backgrounding-occluded-windows",
  "--window-size=1200,820",
  "--window-position=-32000,-32000",
];

const proxyArg =
  obterProxyArg();

if (proxyArg) {
  chromeArgs.push(proxyArg);
}

const clientOptions = {
  authStrategy: new LocalAuth({
    clientId:
      "monitor-planilha",
    dataPath:
      AUTH_DIR,
    rmMaxRetries: 10,
  }),
  puppeteer: {
    headless: false,
    ...(navegador
      ? {
        executablePath:
          navegador,
      }
      : {}),
    args:
      chromeArgs,
  },
};

if (
  PROXY_ATIVO
  && PROXY_USUARIO
) {
  clientOptions.proxyAuthentication = {
    username:
      PROXY_USUARIO,
    password:
      PROXY_SENHA,
  };
}

let client =
  new Client(clientOptions);

let reconectando = false;
let shuttingDown = false;
let qrReceived = false;
let initialized = false;

function wait(ms) {
  return new Promise(
    resolve =>
      setTimeout(resolve, ms)
  );
}

let browserViewEnabled = false;
let browserFrameTimer = null;
let browserFrameBusy = false;
let lastBrowserPid = 0;
let browserPidTimer = null;
let dbRecoveryAttempted = false;
let authResetInProgress = false;

async function browserPage() {
  const page = client?.pupPage;

  if (
    !page
    || page.isClosed()
  ) {
    return null;
  }

  return page;
}

async function emitBrowserFrame(force = false) {
  emitBrowserProcess();

  if (
    browserFrameBusy
    || (!browserViewEnabled && !force)
  ) {
    return;
  }

  const page = await browserPage();

  if (!page) {
    if (force) {
      emit(
        "browser_view_status",
        {
          message:
            "Chrome ainda está inicializando...",
        }
      );
    }
    return;
  }

  browserFrameBusy = true;

  try {
    let bodyText = "";

    try {
      bodyText =
        await page.evaluate(
          () => document.body?.innerText || ""
        );
    } catch (_) {}

    const normalized =
      String(bodyText || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();

    const databaseError =
      normalized.includes(
        "erro no banco de dados do seu navegador"
      )
      || normalized.includes(
        "erro no banco de dados do navegador"
      );

    if (
      databaseError
      && !dbRecoveryAttempted
      && !authResetInProgress
      && !initialized
    ) {
      dbRecoveryAttempted = true;

      emit(
        "browser_db_error",
        {
          message:
            "WhatsApp Web detectou banco local corrompido.",
        }
      );

      setTimeout(
        () => {
          resetWhatsAppAuth(
            "recuperação automática do banco local"
          );
        },
        250
      );
    }

    const base64 =
      await page.screenshot(
        {
          type: "jpeg",
          quality: 68,
          encoding: "base64",
          captureBeyondViewport: false,
        }
      );

    let title = "";
    let url = "";

    try {
      title = await page.title();
    } catch (_) {}

    try {
      url = page.url();
    } catch (_) {}

    emit(
      "browser_frame",
      {
        dataUrl:
          `data:image/jpeg;base64,${base64}`,
        title,
        url,
      }
    );

  } catch (e) {
    if (force) {
      emit(
        "browser_view_status",
        {
          message:
            `Não foi possível capturar a tela: `
            + `${e.message}`,
        }
      );
    }
  } finally {
    browserFrameBusy = false;
  }
}


function ensureBrowserFrameTimer() {
  if (browserFrameTimer) {
    return;
  }

  browserFrameTimer =
    setInterval(
      () => {
        emitBrowserFrame(false);
      },
      1500
    );
}

function currentBrowserPid() {
  try {
    const proc =
      client?.pupBrowser?.process?.();

    return Number(
      proc?.pid || 0
    );
  } catch (_) {
    return 0;
  }
}

function emitBrowserProcess() {
  const pid =
    currentBrowserPid();

  if (
    pid > 0
    && pid !== lastBrowserPid
  ) {
    lastBrowserPid = pid;

    emit(
      "browser_process",
      {
        pid,
      }
    );
  }
}

function ensureBrowserPidTimer() {
  if (browserPidTimer) {
    return;
  }

  browserPidTimer =
    setInterval(
      emitBrowserProcess,
      300
    );
}

ensureBrowserPidTimer();

async function browserWindowBounds() {
  const page =
    await browserPage();

  if (!page) {
    throw new Error(
      "Chrome ainda não foi criado."
    );
  }

  const session =
    await page.target().createCDPSession();

  const info =
    await session.send(
      "Browser.getWindowForTarget"
    );

  return {
    session,
    windowId:
      info.windowId,
  };
}

async function showBrowserWindow() {
  emit(
    "browser_view_status",
    {
      message:
        "A janela do Chrome é incorporada diretamente na aba WhatsApp.",
    }
  );
}


async function hideBrowserWindow() {
  try {
    const {
      session,
      windowId,
    } =
      await browserWindowBounds();

    // Move a MESMA janela para fora da área visível. Mantém a renderização
    // ativa para o preview da aba WhatsApp continuar funcionando.
    await session.send(
      "Browser.setWindowBounds",
      {
        windowId,
        bounds: {
          windowState: "normal",
          left: -32000,
          top: -32000,
          width: 1200,
          height: 820,
        },
      }
    );

    emit(
      "browser_window",
      {
        message:
          "Janela real ocultada; sessão continua ativa.",
      }
    );

  } catch (e) {
    emit(
      "browser_view_status",
      {
        message:
          `Não foi possível ocultar a janela: `
          + `${e.message}`,
      }
    );
  }
}

function activeSessionDir() {
  return path.join(
    AUTH_DIR,
    "session-monitor-planilha"
  );
}

async function removeSessionDirWithRetries(
  sessionDir
) {
  let lastError = null;

  for (
    let attempt = 1;
    attempt <= 12;
    attempt += 1
  ) {
    try {
      fs.rmSync(
        sessionDir,
        {
          recursive: true,
          force: true,
          maxRetries: 3,
          retryDelay: 300,
        }
      );

      return true;

    } catch (e) {
      lastError = e;
      await wait(
        350 + attempt * 180
      );
    }
  }

  throw lastError;
}

async function resetWhatsAppAuth(
  reason = "solicitação do usuário"
) {
  if (
    authResetInProgress
    || shuttingDown
  ) {
    return;
  }

  authResetInProgress = true;
  initialized = false;
  qrReceived = false;

  emit(
    "auth_reset_started",
    {
      reason,
    }
  );

  log(
    "RECRIANDO SESSÃO DO WHATSAPP:",
    reason
  );

  const oldPid =
    currentBrowserPid();

  try {
    await safeDestroy();
  } catch (_) {}

  await wait(900);

  // Em Windows, Chromium pode manter LevelDB/IndexedDB aberto por alguns
  // instantes após browser.close(). Mata SOMENTE a árvore do Chrome iniciado
  // por este Puppeteer, nunca o Chrome pessoal do usuário.
  if (
    process.platform === "win32"
    && oldPid > 0
  ) {
    try {
      spawnSync(
        "taskkill",
        [
          "/PID",
          String(oldPid),
          "/T",
          "/F",
        ],
        {
          windowsHide: true,
          stdio: "ignore",
        }
      );
    } catch (_) {}
  }

  await wait(700);

  const sessionDir =
    activeSessionDir();

  try {
    if (fs.existsSync(sessionDir)) {
      await removeSessionDirWithRetries(
        sessionDir
      );
    }
  } catch (e) {
    authResetInProgress = false;

    emit(
      "auth_reset_error",
      {
        message:
          `Não foi possível limpar a sessão local: `
          + `${e.message}`,
      }
    );

    error(
      "Falha ao limpar sessão local:",
      e
    );
    return;
  }

  client =
    new Client(
      clientOptions
    );

  installClientEvents();

  lastBrowserPid = 0;
  authResetInProgress = false;

  emit(
    "auth_reset_done"
  );

  log(
    "Sessão local limpa. "
    + "Inicializando WhatsApp para gerar novo QR..."
  );

  try {
    await initializeWithRecovery();
  } catch (e) {
    emit(
      "auth_reset_error",
      {
        message:
          `Falha ao reiniciar WhatsApp: `
          + `${e.message}`,
      }
    );
  }
}

async function reloadWhatsApp() {
  const page =
    await browserPage();

  if (!page) {
    emit(
      "browser_view_status",
      {
        message:
          "Chrome ainda está inicializando...",
      }
    );
    return;
  }

  try {
    emit(
      "browser_view_status",
      {
        message:
          "Recarregando WhatsApp Web...",
      }
    );

    await page.reload(
      {
        waitUntil:
          "domcontentloaded",
        timeout: 45000,
      }
    );

    await wait(1200);
    await emitBrowserFrame(true);

  } catch (e) {
    emit(
      "browser_view_status",
      {
        message:
          `Falha ao recarregar: `
          + `${e.message}`,
      }
    );
  }
}

ensureBrowserFrameTimer();

function recoverableInitializeError(err) {
  const text =
    String(
      err?.message
      || err
      || ""
    ).toLowerCase();

  return (
    text.includes(
      "execution context was destroyed"
    )
    || text.includes(
      "cannot find context"
    )
    || text.includes(
      "target closed"
    )
    || text.includes(
      "session closed"
    )
    || text.includes(
      "most likely because of a navigation"
    )
  );
}

async function safeDestroy() {
  try {
    await client.destroy();
  } catch (_) {}
}

function noteLegacySession() {
  const legacyDir = path.join(
    AUTH_DIR,
    "session-central-planilhas"
  );

  if (fs.existsSync(legacyDir)) {
    log(
      "Sessão integrada antiga detectada em session-central-planilhas. "
      + "Ela será preservada, mas a V22 usa o clientId original monitor-planilha."
    );
  }
}

function installClientEvents() {
  client.on(
    "qr",
    async qr => {
      qrReceived = true;

      log(
        "WhatsApp solicitou autenticação "
        + "por QR Code."
      );

      try {
        const dataUrl =
          await QRCode.toDataURL(
            qr,
            {
              width: 360,
              margin: 2,
              errorCorrectionLevel: "M",
            }
          );

        emit(
          "qr",
          {
            dataUrl,
          }
        );

        browserViewEnabled = true;
        emitBrowserFrame(true);
      } catch (e) {
        emit(
          "engine_error",
          {
            message:
              `Falha ao gerar QR: `
              + `${e.message}`,
          }
        );

        error(
          "Falha ao gerar QR:",
          e.message
        );
      }
    }
  );

  client.on(
    "authenticated",
    () => {
      log(
        "WhatsApp autenticado."
      );

      emit(
        "authenticated"
      );
    }
  );

  client.on(
    "loading_screen",
    (percent, message) => {
      log(
        `WhatsApp carregando: `
        + `${percent}% `
        + `${message || ""}`
      );

      emit(
        "loading",
        {
          percent,
          message:
            message || "",
        }
      );
    }
  );

  client.on(
    "ready",
    () => {
      initialized = true;

      log(
        "SISTEMA ATIVO"
      );

      log(
        "WhatsApp conectado em segundo plano."
      );

      emit(
        "ready"
      );

      emitBrowserFrame(true);
    }
  );

  client.on(
    "disconnected",
    async motivo => {
      log(
        "WhatsApp desconectado:",
        motivo
      );

      emit(
        "disconnected",
        {
          reason:
            String(motivo || ""),
        }
      );

      if (
        reconectando
        || shuttingDown
      ) {
        return;
      }

      reconectando = true;

      log(
        "RECONEXÃO: tentativa em 5 segundos..."
      );

      emit(
        "reconnecting"
      );

      await wait(5000);

      if (shuttingDown) {
        reconectando = false;
        return;
      }

      try {
        await safeDestroy();

        client =
          new Client(
            clientOptions
          );

        installClientEvents();

        await initializeWithRecovery();
      } catch (e) {
        error(
          "Falha na reconexão:",
          e.message
        );

        emit(
          "engine_error",
          {
            message:
              `Falha na reconexão: `
              + `${e.message}`,
          }
        );
      } finally {
        reconectando = false;
      }
    }
  );

  client.on(
    "message",
    message =>
      enviarParaPlanilha(
        message
      )
  );

  client.on(
    "message_create",
    message => {
      if (message.fromMe) {
        enviarParaPlanilha(
          message
        );
      }
    }
  );

  client.on(
    "auth_failure",
    erro => {
      error(
        "Falha na autenticação:",
        erro
      );

      emit(
        "auth_failure",
        {
          message:
            String(erro || ""),
        }
      );
    }
  );
}

async function initializeWithRecovery() {
  const maxBrowserAttempts = 3;
  let lastError = null;

  noteLegacySession();

  for (
    let attempt = 1;
    attempt <= maxBrowserAttempts;
    attempt += 1
  ) {
    if (shuttingDown) {
      return;
    }

    try {
      qrReceived = false;

      log(
        `Inicializando WhatsApp `
        + `(tentativa ${attempt}/`
        + `${maxBrowserAttempts})...`
      );

      emit(
        "initializing",
        {
          attempt,
          maxAttempts:
            maxBrowserAttempts,
        }
      );

      browserViewEnabled = true;
      emitBrowserProcess();

      // O preview começa ANTES de initialize() resolver. Isso é intencional:
      // mesmo se o evento "qr" falhar por uma navegação do WhatsApp Web,
      // a página real continua sendo capturada e exibida na aba WhatsApp.
      emitBrowserFrame(true);

      await client.initialize();

      emitBrowserFrame(true);

      // O QR/ready será entregue pelos eventos do cliente.
      return;

    } catch (e) {
      if (authResetInProgress) {
        return;
      }

      lastError = e;

      const message =
        String(
          e?.message
          || e
          || ""
        );

      error(
        "Falha ao inicializar WhatsApp:",
        message
      );

      // O erro transitório de navegação já recebeu 8 tentativas dentro
      // do próprio Client.inject(). Só chegamos aqui se realmente não
      // foi possível estabilizar a página ou ocorreu outro erro.
      if (
        attempt
        >= maxBrowserAttempts
      ) {
        break;
      }

      emit(
        "initialization_retry",
        {
          attempt,
          maxAttempts:
            maxBrowserAttempts,
          message,
        }
      );

      await safeDestroy();

      // Aguarda o Chrome liberar handles do perfil antes de abrir outro.
      await wait(
        1800 + attempt * 700
      );

      client =
        new Client(
          clientOptions
        );

      installClientEvents();
    }
  }

  const finalMessage =
    String(
      lastError?.message
      || lastError
      || "Erro desconhecido"
    );

  emit(
    "engine_error",
    {
      message:
        `Falha ao inicializar WhatsApp: `
        + `${finalMessage}`,
    }
  );

  error(
    "ERRO AO INICIALIZAR WHATSAPP:",
    finalMessage
  );

  process.exit(1);
}

async function postar(dados) {
  if (!APPS_SCRIPT_URL) {
    throw new Error(
      "Apps Script URL não configurada."
    );
  }

  const cfg = {
    headers: {
      "Content-Type":
        "application/json",
    },
    timeout: 15000,
  };

  const proxy =
    obterProxyAxios();

  if (proxy) {
    cfg.proxy = proxy;
  }

  const r = await axios.post(
    APPS_SCRIPT_URL,
    dados,
    cfg
  );

  log(
    "Resposta da planilha:",
    r.data
  );

  return r.data;
}

async function enviarParaPlanilha(
  message
) {
  const msgId =
    message.id?._serialized
    || message.id?.id
    || "";

  if (jaProcessada(msgId)) {
    log(
      "Mensagem duplicada ignorada:",
      msgId
    );
    return;
  }

  if (
    DIAGNOSTICO_GRUPOS
    && [
      message.from,
      message.to,
      message.id?.remote,
    ].some(
      id =>
        String(id || "")
          .endsWith("@g.us")
    )
  ) {
    log(
      "DIAGNÓSTICO DE GRUPO",
      {
        from:
          message.from,
        to:
          message.to,
        remote:
          message.id?.remote,
        fromMe:
          message.fromMe,
        type:
          message.type,
        reconhecido:
          descobrirGrupo(message)
          || "NÃO",
      }
    );
  }

  if (!descobrirGrupo(message)) {
    return;
  }

  const texto =
    message.body || "";

  if (!texto.trim()) {
    return;
  }

  try {
    if (
      message.hasMedia
      && message.type === "video"
    ) {
      const video =
        interpretarVideo(texto);

      if (!video) {
        log(
          "Vídeo ignorado: legenda fora "
          + "do padrão esperado."
        );
        return;
      }

      const aba =
        determinarAba(
          video.data
        );

      log(
        "VÍDEO IDENTIFICADO"
      );
      log("Data:", video.data);
      log("Aba automática:", aba);
      log("Veículo:", video.veiculo);
      log("Título:", video.titulo);
      log("Autor:", video.autor);
      log("Link:", video.link);

      const resp =
        await postar(
          {
            aba,
            data:
              video.data,
            grupo:
              "",
            veiculo:
              video.veiculo,
            titulo:
              video.titulo,
            autor:
              video.autor,
            analise:
              "",
            assunto:
              "",
            radar:
              "",
            link:
              "Vídeo",
          }
        );

      if (resp?.sucesso) {
        marcarProcessada(msgId);

        log(
          "VÍDEO REGISTRADO NA PLANILHA"
        );
        log(
          "Linha:",
          resp.linha
        );

        emit(
          "sheet_success",
          {
            kind:
              "video",
            line:
              resp.linha
              || "--",
          }
        );
      } else {
        log(
          "O Apps Script respondeu com erro:",
          resp
        );

        emit(
          "sheet_error",
          {
            message:
              "O Apps Script respondeu "
              + "com erro ao registrar o vídeo.",
          }
        );
      }

      return;
    }

    if (ehSomenteLink(texto)) {
      log(
        "MENSAGEM IGNORADA: "
        + "contém somente link."
      );
      return;
    }

    const noticia =
      interpretarMensagem(
        texto
      );

    if (!noticia) {
      log(
        "Mensagem ignorada: não foi possível "
        + "identificar a notícia."
      );
      return;
    }

    const data =
      noticia.dataPublicacao
      || new Date()
        .toLocaleDateString(
          "pt-BR"
        );

    const aba =
      determinarAba(data);

    const analise =
      classificarAnalise(
        noticia.titulo,
        texto
      );

    const assunto =
      classificarAssunto(
        noticia.veiculo,
        noticia.titulo,
        texto
      );

    const autor =
      noticia.autor
      || "Não Informado";

    const identified = {
      titulo:
        noticia.titulo,
      veiculo:
        noticia.veiculo,
      data,
      assunto,
      analise,
      autor,
      link:
        noticia.link,
    };

    emit(
      "news_identified",
      {
        data:
          identified,
      }
    );

    log(
      "NOTÍCIA IDENTIFICADA"
    );
    log("Data:", data);
    log("Aba automática:", aba);
    log("Veículo:", noticia.veiculo);
    log("Título:", noticia.titulo);
    log("Autor:", autor);
    log("Análise:", analise);
    log("Assunto:", assunto);
    log("Link:", noticia.link);

    const resp =
      await postar(
        {
          aba,
          data,
          grupo:
            "",
          veiculo:
            noticia.veiculo,
          titulo:
            noticia.titulo,
          autor,
          analise,
          assunto,
          radar:
            "",
          link:
            noticia.link,
        }
      );

    if (resp?.sucesso) {
      marcarProcessada(msgId);

      log(
        "PLANILHA ATUALIZADA"
      );
      log(
        "Linha:",
        resp.linha
      );

      emit(
        "sheet_success",
        {
          kind:
            "news",
          line:
            resp.linha
            || "--",
        }
      );
    } else {
      log(
        "O Apps Script respondeu com erro:",
        resp
      );

      emit(
        "sheet_error",
        {
          message:
            "O Apps Script respondeu "
            + "com erro ao registrar a notícia.",
        }
      );
    }

  } catch (erro) {
    error(
      "ERRO AO ENVIAR PARA PLANILHA"
    );

    if (erro?.response?.status) {
      error(
        "HTTP:",
        erro.response.status
      );
    }

    error(
      erro?.response?.data
      || erro?.message
      || erro
    );

    emit(
      "sheet_error",
      {
        message:
          String(
            erro?.response?.data
            || erro?.message
            || "Erro ao enviar para planilha"
          ),
        status:
          erro?.response?.status
          || 0,
      }
    );
  }
}

process.on(
  "uncaughtException",
  erro => {
    error(
      "ERRO NÃO TRATADO:",
      erro
    );

    emit(
      "engine_error",
      {
        message:
          String(
            erro?.message
            || erro
          ),
      }
    );
  }
);

process.on(
  "unhandledRejection",
  erro => {
    error(
      "PROMISE NÃO TRATADA:",
      erro
    );

    emit(
      "engine_error",
      {
        message:
          String(
            erro?.message
            || erro
          ),
      }
    );
  }
);

async function shutdown(
  reason = "solicitação"
) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;

  if (browserFrameTimer) {
    clearInterval(browserFrameTimer);
    browserFrameTimer = null;
  }

  if (browserPidTimer) {
    clearInterval(browserPidTimer);
    browserPidTimer = null;
  }

  log(
    "Encerrando motor:",
    reason
  );

  await safeDestroy();

  process.exit(0);
}

const input =
  readline.createInterface(
    {
      input:
        process.stdin,
      terminal:
        false,
    }
  );

input.on(
  "line",
  line => {
    const cmd =
      String(line || "")
        .trim()
        .toUpperCase();

    if (
      cmd === "STOP"
      || cmd === "EXIT"
      || cmd === "QUIT"
    ) {
      shutdown(
        "comando do Central"
      );
      return;
    }

    if (cmd === "VIEW_ON") {
      browserViewEnabled = true;
      emitBrowserFrame(true);
      return;
    }

    if (cmd === "VIEW_OFF") {
      browserViewEnabled = false;
      return;
    }

    if (cmd === "SCREENSHOT") {
      emitBrowserFrame(true);
      return;
    }

    if (cmd === "SHOW_BROWSER") {
      showBrowserWindow();
      return;
    }

    if (cmd === "HIDE_BROWSER") {
      hideBrowserWindow();
      return;
    }

    if (cmd === "RELOAD_WHATSAPP") {
      reloadWhatsApp();
      return;
    }

    if (cmd === "RESET_AUTH") {
      resetWhatsAppAuth(
        "solicitação do Central"
      );
      return;
    }
  }
);

process.on(
  "SIGINT",
  () => shutdown("SIGINT")
);

process.on(
  "SIGTERM",
  () => shutdown("SIGTERM")
);

installClientEvents();

initializeWithRecovery().catch(
  erro => {
    error(
      "FALHA FINAL AO INICIALIZAR:",
      erro?.message || erro
    );

    emit(
      "engine_error",
      {
        message:
          String(
            erro?.message
            || erro
          ),
      }
    );

    process.exit(1);
  }
);
