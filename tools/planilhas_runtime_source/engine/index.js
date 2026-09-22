const qrcode = require("qrcode-terminal");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
const {
  Client,
  LocalAuth,
  NoAuth,
} = require("whatsapp-web.js");

const CONFIG_PATH =
  process.env.CONFIG_PATH
  || path.join(
    __dirname,
    "..",
    "config.json"
  );

let CONFIG;

try {
  CONFIG = JSON.parse(
    fs.readFileSync(
      CONFIG_PATH,
      "utf8"
    )
  );
} catch (e) {
  console.error(
    "ERRO CONFIG:",
    e.message
  );
  process.exit(2);
}

const GRUPOS_ID =
  Array.isArray(CONFIG.grupos)
    ? CONFIG.grupos
    : [];

const APPS_SCRIPT_URL =
  String(
    CONFIG.appsScriptUrl
    || ""
  ).trim();

const DIAGNOSTICO_GRUPOS =
  Boolean(
    CONFIG.diagnosticoGrupos
  );

const SHARED_BROWSER =
  process.env.CENTRAL_WHATSAPP_SHARED_BROWSER
  === "1";

const SHARED_BROWSER_URL =
  String(
    process.env.CENTRAL_WHATSAPP_BROWSER_URL
    || "http://127.0.0.1:9223"
  ).trim();

const STATUS_FILE =
  String(
    process.env.CENTRAL_WHATSAPP_STATUS_FILE
    || ""
  ).trim();

const MODO_VISUAL_LOGIN =
  process.env.CENTRAL_WHATSAPP_VISIBLE
  === "1";

const AUTH_ROOT =
  path.join(
    path.dirname(CONFIG_PATH),
    ".wwebjs_auth_v2"
  );

const AUTH_SESSION_DIR =
  path.join(
    AUTH_ROOT,
    "session-monitor-planilha"
  );

// ---------------------------------------------------------------------
// STATUS COMPARTILHADO COM O CENTRAL
// ---------------------------------------------------------------------

function writeSharedStatus(
  state,
  message = "",
  extra = {}
) {
  if (!STATUS_FILE) {
    return;
  }

  try {
    fs.mkdirSync(
      path.dirname(STATUS_FILE),
      { recursive: true }
    );

    const payload = {
      state,
      message,
      updatedAt:
        new Date().toISOString(),
      browserUrl:
        SHARED_BROWSER
          ? SHARED_BROWSER_URL
          : "",
      ...extra,
    };

    const temp =
      `${STATUS_FILE}.tmp`;

    fs.writeFileSync(
      temp,
      JSON.stringify(
        payload,
        null,
        2
      ),
      "utf8"
    );

    fs.renameSync(
      temp,
      STATUS_FILE
    );
  } catch (_) {}
}

// ---------------------------------------------------------------------
// REDE / PROXY
// ---------------------------------------------------------------------

const CENTRAL_PROXY_PRESENT =
  Object.prototype.hasOwnProperty.call(
    process.env,
    "CENTRAL_PROXY_ENABLED"
  );

const CONFIG_PROXY =
  CONFIG.proxy || {};

const PROXY_ATIVO =
  CENTRAL_PROXY_PRESENT
    ? process.env.CENTRAL_PROXY_ENABLED
      === "1"
    : Boolean(
      CONFIG_PROXY.ativo
    );

const PROXY_HOST =
  String(
    CENTRAL_PROXY_PRESENT
      ? (
        process.env.CENTRAL_PROXY_HOST
        || ""
      )
      : (
        CONFIG_PROXY.host
        || ""
      )
  ).trim();

const PROXY_PORT =
  Number(
    CENTRAL_PROXY_PRESENT
      ? (
        process.env.CENTRAL_PROXY_PORT
        || 0
      )
      : (
        CONFIG_PROXY.porta
        || 0
      )
  );

const PROXY_USUARIO =
  String(
    CENTRAL_PROXY_PRESENT
      ? (
        process.env.CENTRAL_PROXY_USERNAME
        || ""
      )
      : (
        CONFIG_PROXY.usuario
        || ""
      )
  ).trim();

const PROXY_SENHA =
  String(
    CENTRAL_PROXY_PRESENT
      ? (
        process.env.CENTRAL_PROXY_PASSWORD
        || ""
      )
      : (
        CONFIG_PROXY.senha
        || ""
      )
  );

const STATE_DIR =
  path.join(
    path.dirname(CONFIG_PATH),
    "data"
  );

const SEEN_FILE =
  path.join(
    STATE_DIR,
    "mensagens-processadas.json"
  );

let seen = new Set();

try {
  fs.mkdirSync(
    STATE_DIR,
    { recursive: true }
  );

  if (
    fs.existsSync(
      SEEN_FILE
    )
  ) {
    const arr =
      JSON.parse(
        fs.readFileSync(
          SEEN_FILE,
          "utf8"
        )
      );

    if (
      Array.isArray(arr)
    ) {
      seen = new Set(
        arr
      );
    }
  }
} catch (_) {}

function jaProcessada(id) {
  return Boolean(
    id
    && seen.has(id)
  );
}

function marcarProcessada(id) {
  if (!id) {
    return;
  }

  seen.add(id);

  if (
    seen.size > 3000
  ) {
    seen = new Set(
      Array.from(seen)
        .slice(-2000)
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
    id =>
      GRUPOS_ID.includes(id)
  );
}

function extrairLink(t) {
  const m =
    String(t || "")
      .match(
        /https?:\/\/[^\s\])]+/i
      );

  return m
    ? m[0]
    : "";
}

function ehSomenteLink(t) {
  return /^https?:\/\/\S+$/i.test(
    String(t || "")
      .trim()
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

  const m =
    limparTexto(data)
      .match(
        /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/
      );

  if (!m) {
    const d = new Date();

    return (
      `${meses[d.getMonth()]}`
      + `${String(d.getFullYear()).slice(-2)}`
    );
  }

  const mes = Number(
    m[2]
  );
  const ano = Number(
    m[3]
  );

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
  const c =
    limparTexto(t);

  if (
    !c
    || c.length > 60
    || /https?:\/\//i.test(c)
    || /[.?!]$/.test(c)
  ) {
    return false;
  }

  const p =
    c.split(/\s+/)
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
  const t =
    normalizarTexto(
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

  const t =
    normalizarTexto(
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

  let p =
    pos.reduce(
      (s, x) =>
        s
        + (
          t.includes(x)
            ? 1
            : 0
        ),
      0
    );

  let n =
    neg.reduce(
      (s, x) =>
        s
        + (
          t.includes(x)
            ? 1
            : 0
        ),
      0
    )
    + raizes.reduce(
      (s, x) =>
        s
        + (
          t.includes(x)
            ? 2
            : 0
        ),
      0
    );

  const tt =
    normalizarTexto(
      titulo
    );

  n +=
    neg.reduce(
      (s, x) =>
        s
        + (
          tt.includes(x)
            ? 2
            : 0
        ),
      0
    )
    + raizes.reduce(
      (s, x) =>
        s
        + (
          tt.includes(x)
            ? 3
            : 0
        ),
      0
    );

  return (
    n > p
      ? "NEGATIVA"
      : p > n
        ? "POSITIVA"
        : "NEUTRA"
  );
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

  const t =
    normalizarTexto(
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

  const temMil =
    mil.some(
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
  const partes =
    String(texto || "")
      .trim()
      .split(/\s+-\s+/)
      .map(
        x => x.trim()
      )
      .filter(Boolean);

  if (
    partes.length < 3
  ) {
    return null;
  }

  const m =
    partes[0]
      .toUpperCase()
      .replace(
        /\s+/g,
        ""
      )
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
    veiculo:
      partes[1],
    titulo:
      partes.slice(2)
        .join(" - "),
    autor:
      "Não Informado",
    link:
      "Vídeo",
  };
}

function interpretarMensagem(texto) {
  const linhas =
    String(texto || "")
      .split(/\r?\n/)
      .map(
        x => x.trim()
      )
      .filter(Boolean);

  const link =
    extrairLink(texto);

  if (!link) {
    return null;
  }

  const iLink =
    linhas.findIndex(
      x => x.includes(link)
    );

  if (iLink < 0) {
    return null;
  }

  const veiculo =
    limparTexto(
      linhas[iLink + 1]
      || ""
    );

  const titulo =
    limparTexto(
      linhas[iLink + 2]
      || ""
    );

  let iData = -1;

  for (
    let i = iLink + 3;
    i < linhas.length;
    i += 1
  ) {
    if (
      ehData(
        linhas[i]
      )
    ) {
      iData = i;
      break;
    }
  }

  const dataPublicacao =
    iData >= 0
      ? limparTexto(
        linhas[iData]
      )
      : "";

  let autor = "";

  if (
    iData >= 0
    && iData - 1
      > iLink + 2
  ) {
    const c =
      limparTexto(
        linhas[iData - 1]
      );

    if (
      pareceAutor(c)
    ) {
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
    return false;
  }

  const proxy = {
    protocol:
      "http",
    host:
      PROXY_HOST,
    port:
      PROXY_PORT,
  };

  if (
    PROXY_USUARIO
  ) {
    proxy.auth = {
      username:
        PROXY_USUARIO,
      password:
        PROXY_SENHA,
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

console.log(
  SHARED_BROWSER
    ? (
      "MODO DO NAVEGADOR: "
      + "CHROME COMPARTILHADO DO CENTRAL"
    )
    : MODO_VISUAL_LOGIN
      ? "MODO DO NAVEGADOR: LOGIN VISUAL"
      : "MODO DO NAVEGADOR: OCULTO (HEADLESS)"
);

if (
  SHARED_BROWSER
) {
  console.log(
    "REMOTE DEBUGGING:",
    SHARED_BROWSER_URL
  );
} else if (
  navegador
) {
  console.log(
    "NAVEGADOR:",
    navegador
  );
}

if (
  CENTRAL_PROXY_PRESENT
) {
  console.log(
    "REDE: configuração recebida do Proxy Geral do Central"
  );
}

if (
  PROXY_ATIVO
  && PROXY_HOST
  && PROXY_PORT
) {
  console.log(
    `PROXY ATIVO: `
    + `${PROXY_HOST}:`
    + `${PROXY_PORT}`
  );

  console.log(
    PROXY_USUARIO
      ? "PROXY COM AUTENTICAÇÃO CONFIGURADA"
      : "PROXY SEM USUÁRIO/SENHA CONFIGURADOS"
  );
} else {
  console.log(
    "PROXY: DESATIVADO"
  );
  console.log(
    "REDE DIRETA FORÇADA: "
    + "proxy do Windows/ambiente ignorado."
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
];

if (
  MODO_VISUAL_LOGIN
) {
  chromeArgs.push(
    "--start-maximized"
  );
  chromeArgs.push(
    "--window-size=1280,820"
  );
}

const proxyArg =
  obterProxyArg();

if (
  proxyArg
) {
  chromeArgs.push(
    proxyArg
  );
} else {
  chromeArgs.push(
    "--no-proxy-server"
  );
}

const authStrategy =
  SHARED_BROWSER
    ? new NoAuth()
    : new LocalAuth({
      clientId:
        "monitor-planilha",
      dataPath:
        AUTH_ROOT,
      rmMaxRetries:
        12,
    });

const puppeteerOptions =
  SHARED_BROWSER
    ? {
      browserURL:
        SHARED_BROWSER_URL,
      defaultViewport:
        null,
    }
    : {
      headless:
        !MODO_VISUAL_LOGIN,
      ...(
        MODO_VISUAL_LOGIN
          ? {
            defaultViewport:
              null,
          }
          : {}
      ),
      ...(
        navegador
          ? {
            executablePath:
              navegador,
          }
          : {}
      ),
      args:
        chromeArgs,
    };

const clientOptions = {
  authStrategy,
  authTimeoutMs:
    SHARED_BROWSER
      ? 180000
      : MODO_VISUAL_LOGIN
        ? 180000
        : 120000,
  puppeteer:
    puppeteerOptions,
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

const client =
  new Client(
    clientOptions
  );

let visualTitleTimer = null;
let shuttingDown = false;

function manterTituloLoginVisual() {
  if (
    !MODO_VISUAL_LOGIN
    && !SHARED_BROWSER
  ) {
    return;
  }

  if (
    visualTitleTimer
  ) {
    return;
  }

  visualTitleTimer =
    setInterval(
      async () => {
        try {
          const page =
            client.pupPage;

          if (
            !page
            || page.isClosed()
          ) {
            return;
          }

          await page.evaluate(
            () => {
              document.title =
                "CENTRAL WHATSAPP";
            }
          );
        } catch (_) {}
      },
      1200
    );
}

async function bringWhatsAppToFront() {
  try {
    const page =
      client.pupPage;

    if (
      page
      && !page.isClosed()
    ) {
      await page.bringToFront();
    }
  } catch (_) {}
}

async function safeDetach() {
  if (
    SHARED_BROWSER
  ) {
    try {
      const browser =
        client.pupBrowser;

      if (
        browser
        && typeof browser.disconnect === "function"
      ) {
        browser.disconnect();
      }
    } catch (_) {}

    return;
  }

  try {
    await client.destroy();
  } catch (_) {}
}

client.on(
  "qr",
  qr => {
    manterTituloLoginVisual();

    console.log(
      "[LOGIN] QR DISPONÍVEL"
    );
    console.log(
      "\nLeia o QR Code:\n"
    );

    qrcode.generate(
      qr,
      { small: true }
    );

    writeSharedStatus(
      "awaiting_qr",
      "Leia o QR Code na janela real do WhatsApp Web."
    );

    bringWhatsAppToFront();
  }
);

client.on(
  "authenticated",
  () => {
    manterTituloLoginVisual();

    console.log(
      "[LOGIN] AUTENTICADO"
    );
    console.log(
      "WhatsApp autenticado."
    );

    writeSharedStatus(
      "authenticated",
      "QR Code aceito. Finalizando o carregamento do WhatsApp."
    );

    bringWhatsAppToFront();
  }
);

client.on(
  "loading_screen",
  (
    percent,
    message
  ) => {
    manterTituloLoginVisual();

    console.log(
      `WhatsApp carregando: `
      + `${percent}% `
      + `${message || ""}`
    );

    writeSharedStatus(
      "starting",
      `WhatsApp carregando: ${percent}% ${message || ""}`
    );
  }
);

client.on(
  "ready",
  () => {
    manterTituloLoginVisual();

    console.log(
      "[LOGIN] PRONTO"
    );
    console.log(
      "\n===================================="
    );
    console.log(
      "SISTEMA ATIVO"
    );
    console.log(
      "===================================="
    );

    console.log(
      SHARED_BROWSER
        ? (
          "WhatsApp conectado no Chrome "
          + "persistente compartilhado."
        )
        : MODO_VISUAL_LOGIN
          ? "WhatsApp conectado no Chrome visual."
          : "WhatsApp conectado em segundo plano."
    );

    if (
      PROXY_ATIVO
      && PROXY_USUARIO
    ) {
      console.log(
        "Autenticação do proxy aplicada ao WhatsApp Web."
      );
    }

    writeSharedStatus(
      "connected",
      "WhatsApp conectado e disponível para a Automação de Planilhas."
    );

    bringWhatsAppToFront();
  }
);

let sessionExpirationHandled =
  false;

async function requireRelogin(
  reason
) {
  if (
    sessionExpirationHandled
    || shuttingDown
  ) {
    return;
  }

  sessionExpirationHandled =
    true;

  console.log(
    "WHATSAPP_RELOGIN_REQUIRED:",
    reason
  );

  console.log(
    "WhatsApp precisa ser conectado novamente. "
    + "Abra a aba WhatsApp do Central e leia um novo QR Code."
  );

  writeSharedStatus(
    "session_expired",
    "WhatsApp precisa ser conectado novamente.",
    {
      reason:
        String(reason || ""),
    }
  );

  await safeDetach();

  setTimeout(
    () => process.exit(21),
    200
  );
}

client.on(
  "disconnected",
  motivo => {
    const reason =
      String(
        motivo || ""
      ).toUpperCase();

    console.log(
      "WhatsApp desconectado:",
      motivo
    );

    if (
      reason.includes(
        "LOGOUT"
      )
    ) {
      requireRelogin(
        "LOGOUT"
      );
      return;
    }

    writeSharedStatus(
      "disconnected",
      `WhatsApp desconectado: ${motivo || "motivo não informado"}`
    );

    if (
      !shuttingDown
    ) {
      console.log(
        "RECONEXÃO: reiniciando apenas o motor; "
        + "o Chrome e o perfil serão preservados."
      );

      safeDetach().finally(
        () => {
          setTimeout(
            () => process.exit(13),
            500
          );
        }
      );
    }
  }
);

async function postar(dados) {
  if (
    !APPS_SCRIPT_URL
  ) {
    throw new Error(
      "Apps Script URL não configurada."
    );
  }

  const proxy =
    obterProxyAxios();

  const cfg = {
    headers: {
      "Content-Type":
        "application/json",
    },
    timeout:
      15000,
    proxy:
      proxy || false,
  };

  const r =
    await axios.post(
      APPS_SCRIPT_URL,
      dados,
      cfg
    );

  console.log(
    "Resposta da planilha:"
  );
  console.log(
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

  if (
    jaProcessada(
      msgId
    )
  ) {
    console.log(
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
    console.log(
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

  if (
    !descobrirGrupo(
      message
    )
  ) {
    return;
  }

  const texto =
    message.body || "";

  if (
    !texto.trim()
  ) {
    return;
  }

  try {
    if (
      message.hasMedia
      && message.type
        === "video"
    ) {
      const video =
        interpretarVideo(
          texto
        );

      if (!video) {
        console.log(
          "Vídeo ignorado: legenda fora do padrão esperado."
        );
        return;
      }

      const aba =
        determinarAba(
          video.data
        );

      console.log(
        "VÍDEO IDENTIFICADO"
      );
      console.log(
        "Data:",
        video.data
      );
      console.log(
        "Aba automática:",
        aba
      );
      console.log(
        "Veículo:",
        video.veiculo
      );
      console.log(
        "Título:",
        video.titulo
      );
      console.log(
        "Autor:",
        video.autor
      );
      console.log(
        "Link:",
        video.link
      );

      const resp =
        await postar({
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
        });

      if (
        resp?.sucesso
      ) {
        marcarProcessada(
          msgId
        );

        console.log(
          "VÍDEO REGISTRADO NA PLANILHA"
        );
        console.log(
          "Linha:",
          resp.linha
        );
      } else {
        console.log(
          "O Apps Script respondeu com erro:",
          resp
        );
      }

      return;
    }

    if (
      ehSomenteLink(
        texto
      )
    ) {
      console.log(
        "MENSAGEM IGNORADA: contém somente link."
      );
      return;
    }

    const noticia =
      interpretarMensagem(
        texto
      );

    if (!noticia) {
      console.log(
        "Mensagem ignorada: não foi possível identificar a notícia."
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
      determinarAba(
        data
      );

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

    console.log(
      "NOTÍCIA IDENTIFICADA"
    );
    console.log(
      "Data:",
      data
    );
    console.log(
      "Aba automática:",
      aba
    );
    console.log(
      "Veículo:",
      noticia.veiculo
    );
    console.log(
      "Título:",
      noticia.titulo
    );
    console.log(
      "Autor:",
      noticia.autor
      || "Não Informado"
    );
    console.log(
      "Análise:",
      analise
    );
    console.log(
      "Assunto:",
      assunto
    );
    console.log(
      "Link:",
      noticia.link
    );

    const resp =
      await postar({
        aba,
        data,
        grupo:
          "",
        veiculo:
          noticia.veiculo,
        titulo:
          noticia.titulo,
        autor:
          noticia.autor
          || "Não Informado",
        analise,
        assunto,
        radar:
          "",
        link:
          noticia.link,
      });

    if (
      resp?.sucesso
    ) {
      marcarProcessada(
        msgId
      );

      console.log(
        "PLANILHA ATUALIZADA"
      );
      console.log(
        "Linha:",
        resp.linha
      );
    } else {
      console.log(
        "O Apps Script respondeu com erro:",
        resp
      );
    }

  } catch (erro) {
    console.error(
      "ERRO AO ENVIAR PARA PLANILHA"
    );

    if (
      erro?.response?.status
    ) {
      console.error(
        "HTTP:",
        erro.response.status
      );
    }

    console.error(
      erro?.response?.data
      || erro?.message
      || erro
    );
  }
}

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
    if (
      message.fromMe
    ) {
      enviarParaPlanilha(
        message
      );
    }
  }
);

client.on(
  "auth_failure",
  erro => {
    console.error(
      "Falha na autenticação:",
      erro
    );

    requireRelogin(
      `auth_failure: ${erro || ""}`
    );
  }
);

process.on(
  "uncaughtException",
  erro => {
    console.error(
      "ERRO NÃO TRATADO:",
      erro
    );

    writeSharedStatus(
      "error",
      String(
        erro?.message
        || erro
      )
    );
  }
);

process.on(
  "unhandledRejection",
  erro => {
    console.error(
      "PROMISE NÃO TRATADA:",
      erro
    );

    writeSharedStatus(
      "error",
      String(
        erro?.message
        || erro
      )
    );
  }
);

async function iniciarWhatsApp() {
  writeSharedStatus(
    "starting",
    SHARED_BROWSER
      ? "Conectando ao Chrome persistente do Central..."
      : "Inicializando WhatsApp..."
  );

  try {
    if (
      SHARED_BROWSER
    ) {
      console.log(
        "[LOGIN] Conectando ao Chrome compartilhado..."
      );
    } else if (
      MODO_VISUAL_LOGIN
    ) {
      console.log(
        "[LOGIN] Abrindo Chrome portátil para autenticação visual..."
      );
    }

    manterTituloLoginVisual();

    await client.initialize();

  } catch (erro) {
    const message =
      String(
        erro?.message
        || erro
        || "erro desconhecido"
      );

    console.error(
      "ERRO AO INICIALIZAR WHATSAPP:",
      message
    );

    if (
      message.includes(
        "ERR_INVALID_AUTH_CREDENTIALS"
      )
    ) {
      if (
        PROXY_ATIVO
      ) {
        console.error(
          "DIAGNÓSTICO: o proxy recusou as credenciais. "
          + "Confira usuário/senha em Configurações > Proxy Geral do Central."
        );
      } else {
        console.error(
          "DIAGNÓSTICO: a conexão direta foi forçada, mas a rede recusou "
          + "autenticação. Se esta rede exigir proxy, ative o Proxy Geral "
          + "do Central."
        );
      }
    }

    if (
      message.toLowerCase()
        .includes(
          "auth timeout"
        )
    ) {
      console.error(
        "DIAGNÓSTICO: auth timeout não apaga mais a sessão. "
        + "O perfil persistente será preservado."
      );

      await requireRelogin(
        "auth timeout"
      );
      return;
    }

    writeSharedStatus(
      "error",
      message
    );

    console.error(
      "O motor será encerrado sem apagar o perfil do WhatsApp."
    );

    await safeDetach();

    setTimeout(
      () => process.exit(1),
      250
    );
  }
}

process.on(
  "SIGINT",
  async () => {
    shuttingDown = true;
    await safeDetach();
    process.exit(0);
  }
);

process.on(
  "SIGTERM",
  async () => {
    shuttingDown = true;
    await safeDetach();
    process.exit(0);
  }
);

process.on(
  "exit",
  () => {
    try {
      if (
        visualTitleTimer
      ) {
        clearInterval(
          visualTitleTimer
        );
      }
    } catch (_) {}
  }
);

iniciarWhatsApp();
