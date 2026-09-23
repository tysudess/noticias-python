const fs = require("fs");
const path = require("path");

function normalizeLineEndings(value) {
  return String(value || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n");
}

const runtimeRoot = path.join(
  __dirname,
  ".."
);

const clientTarget = path.join(
  runtimeRoot,
  "node_modules",
  "whatsapp-web.js",
  "src",
  "Client.js"
);

const engineTarget = path.join(
  runtimeRoot,
  "engine",
  "index.js"
);

const mainTarget = path.join(
  runtimeRoot,
  "main.js"
);

if (!fs.existsSync(clientTarget)) {
  throw new Error(
    `Client.js do whatsapp-web.js não encontrado: ${clientTarget}`
  );
}

if (!fs.existsSync(engineTarget)) {
  throw new Error(
    `engine/index.js não encontrado: ${engineTarget}`
  );
}

if (!fs.existsSync(mainTarget)) {
  throw new Error(
    `main.js não encontrado: ${mainTarget}`
  );
}

let source =
  normalizeLineEndings(
    fs.readFileSync(
      clientTarget,
      "utf8"
    )
  );

const originalClient =
  source;

function replaceOnce(
  oldText,
  newText,
  label
) {
  oldText = normalizeLineEndings(
    oldText
  );
  newText = normalizeLineEndings(
    newText
  );

  if (!source.includes(oldText)) {
    throw new Error(
      `Patch incompatível: trecho não encontrado (${label}).`
    );
  }

  source =
    source.replace(
      oldText,
      newText
    );
}

// ---------------------------------------------------------------------
// 1) ESPERA DE AUTENTICAÇÃO RESISTENTE À NAVEGAÇÃO
// ---------------------------------------------------------------------

replaceOnce(
`        if (
            this.options.authTimeoutMs === undefined ||
            this.options.authTimeoutMs == 0
        ) {
            this.options.authTimeoutMs = 30000;
        }
        let start = Date.now();
        let timeout = this.options.authTimeoutMs;
        let res = false;
        while (start > Date.now() - timeout) {
            res = await this.pupPage.evaluate(
                'window.Debug?.VERSION != undefined',
            );
            if (res) {
                break;
            }
            await new Promise((r) => setTimeout(r, 200));
        }
        if (!res) {
            throw 'auth timeout';
        }`,
`        if (
            this.options.authTimeoutMs === undefined ||
            this.options.authTimeoutMs == 0
        ) {
            this.options.authTimeoutMs = 90000;
        }

        try {
            await this.pupPage.waitForFunction(
                'window.Debug?.VERSION != undefined',
                {
                    timeout: this.options.authTimeoutMs,
                    polling: 200,
                },
            );
        } catch (_) {
            throw 'auth timeout';
        }`,
  "auth waitForFunction"
);

// ---------------------------------------------------------------------
// 2) ESPERA DE WWEBJS RESISTENTE À NAVEGAÇÃO
// ---------------------------------------------------------------------

replaceOnce(
`                    let start = Date.now();
                    let res = false;
                    while (start > Date.now() - 30000) {
                        // Check window.WWebJS Injection
                        res = await this.pupPage.evaluate(
                            'window.WWebJS != undefined',
                        );
                        if (res) {
                            break;
                        }
                        await new Promise((r) => setTimeout(r, 200));
                    }
                    if (!res) {
                        throw 'ready timeout';
                    }`,
`                    try {
                        await this.pupPage.waitForFunction(
                            'window.WWebJS != undefined',
                            {
                                timeout: 60000,
                                polling: 200,
                            },
                        );
                    } catch (_) {
                        throw 'ready timeout';
                    }`,
  "ready waitForFunction"
);

// ---------------------------------------------------------------------
// 3) REINJEÇÃO SEGURA APÓS NAVEGAÇÃO
// ---------------------------------------------------------------------

replaceOnce(
`        await this.inject();

        this.pupPage.on('framenavigated', async (frame) => {
            if (frame.url().includes('post_logout=1') || this.lastLoggedOut) {
                this.emit(Events.DISCONNECTED, 'LOGOUT');
                await this.authStrategy.logout();
                await this.authStrategy.beforeBrowserInitialized();
                await this.authStrategy.afterBrowserInitialized();
                this.lastLoggedOut = false;
            }
            await this.inject();
        });`,
`        let reinjectingAfterNavigation = false;

        this.pupPage.on('framenavigated', async (frame) => {
            if (frame !== this.pupPage.mainFrame()) {
                return;
            }

            if (frame.url().includes('post_logout=1') || this.lastLoggedOut) {
                this.emit(Events.DISCONNECTED, 'LOGOUT');
                await this.authStrategy.logout();
                await this.authStrategy.beforeBrowserInitialized();
                await this.authStrategy.afterBrowserInitialized();
                this.lastLoggedOut = false;
            }

            if (reinjectingAfterNavigation) {
                return;
            }

            reinjectingAfterNavigation = true;

            try {
                await this.inject();
            } catch (err) {
                const message = String(err?.message || err || '');

                if (
                    !message.includes('Execution context was destroyed') &&
                    !message.includes('Cannot find context') &&
                    !message.includes('navigat')
                ) {
                    throw err;
                }
            } finally {
                reinjectingAfterNavigation = false;
            }
        });

        let lastInjectError = null;

        for (let attempt = 1; attempt <= 5; attempt += 1) {
            try {
                await this.inject();
                lastInjectError = null;
                break;
            } catch (err) {
                lastInjectError = err;

                const message = String(err?.message || err || '');

                const navigationError =
                    message.includes('Execution context was destroyed') ||
                    message.includes('Cannot find context') ||
                    message.includes('navigat');

                if (!navigationError || attempt >= 5) {
                    throw err;
                }

                await new Promise((resolve) =>
                    setTimeout(resolve, 600 + attempt * 350),
                );
            }
        }

        if (lastInjectError) {
            throw lastInjectError;
        }`,
  "navigation recovery"
);

// ---------------------------------------------------------------------
// 4) CHROME COMPARTILHADO: REUTILIZAR A ABA EXISTENTE
// ---------------------------------------------------------------------
//
// O whatsapp-web.js original faz browser.newPage() sempre que browserURL é
// usado. Na Central isso criava uma aba nova a cada inicialização/reinício do
// motor. A V37 reaproveita primeiro uma aba do WhatsApp já existente; se não
// houver, reaproveita o about:blank criado pelo Central; só então cria aba nova.

replaceOnce(
`            browser = await puppeteer.connect(puppeteerOpts);
            page = await browser.newPage();`,
`            browser = await puppeteer.connect(puppeteerOpts);

            const connectedPages = await browser.pages();

            page =
                connectedPages.find((candidate) => {
                    try {
                        return candidate
                            .url()
                            .includes('web.whatsapp.com');
                    } catch (_) {
                        return false;
                    }
                }) ||
                connectedPages.find((candidate) => {
                    try {
                        const currentUrl = candidate.url();

                        return (
                            currentUrl === 'about:blank' ||
                            currentUrl === ''
                        );
                    } catch (_) {
                        return false;
                    }
                }) ||
                await browser.newPage();`,
  "shared browser tab reuse"
);

// ---------------------------------------------------------------------
// 4.1) PROXY AUTENTICADO: RETENTATIVA DE NAVEGAÇÃO
// ---------------------------------------------------------------------
//
// Em Chrome conectado por remote debugging, uma página antiga pode estar
// parada numa tela de erro de rede. As credenciais são reaplicadas antes de
// repetir a navegação. Não há bypass do Proxy Geral.

replaceOnce(
`        await page.goto(WhatsWebURL, {
            waitUntil: 'load',
            timeout: 0,
            referer: 'https://whatsapp.com/',
        });`,
`        const centralNavigateWhatsApp = async () => {
            await page.goto(WhatsWebURL, {
                waitUntil: 'load',
                timeout: 0,
                referer: 'https://whatsapp.com/',
            });
        };

        try {
            await centralNavigateWhatsApp();
        } catch (err) {
            const message = String(err?.message || err || '');

            const proxyNavigationError =
                this.options.proxyAuthentication !== undefined &&
                (
                    message.includes('ERR_CONNECTION_TIMED_OUT') ||
                    message.includes('ERR_TIMED_OUT') ||
                    message.includes('ERR_PROXY_CONNECTION_FAILED') ||
                    message.includes('ERR_TUNNEL_CONNECTION_FAILED') ||
                    message.includes('ERR_PROXY_AUTH_REQUESTED')
                );

            if (!proxyNavigationError) {
                throw err;
            }

            try {
                await page.goto('about:blank', {
                    waitUntil: 'domcontentloaded',
                    timeout: 30000,
                });
            } catch (_) {}

            try {
                await page.authenticate(null);
            } catch (_) {}

            await new Promise((resolve) =>
                setTimeout(resolve, 500),
            );

            await page.authenticate(
                this.options.proxyAuthentication,
            );

            await new Promise((resolve) =>
                setTimeout(resolve, 700),
            );

            await centralNavigateWhatsApp();
        }`,
  "proxy authenticated navigation retry"
);


// ---------------------------------------------------------------------
// 5) RECUPERAÇÃO DE EVENTOS DE MENSAGEM
// ---------------------------------------------------------------------
//
// Algumas versões recentes do WhatsApp Web podem manter o cliente em ready,
// porém o evento Msg.on('add') deixa de chegar de forma confiável. Mantemos o
// listener nativo e adicionamos uma varredura leve da coleção de mensagens.
// Ambos passam pelo mesmo Set de IDs, evitando emissão duplicada.

replaceOnce(
`            Msg.on('add', (msg) => {
                if (!msg.isNewMsg) return;

                if (msg.type !== 'ciphertext') {
                    window.onAddMessageEvent(
                        window.WWebJS.getMessageModel(msg),
                    );
                    return;
                }

                window.onAddMessageCiphertextEvent(
                    window.WWebJS.getMessageModel(msg),
                );

                if (msg.subtype && msg.subtype.endsWith('_unavailable_fanout'))
                    return;

                requestResend(msg);

                const failTimer = setTimeout(() => {
                    if (msg.type !== 'ciphertext') return;
                    window.onCiphertextFailedEvent(
                        window.WWebJS.getMessageModel(msg),
                    );
                }, 15000);

                msg.once('change:type', (_msg) => {
                    clearTimeout(failTimer);
                    pendingResend.delete(_msg);
                    if (_msg.type === 'revoked') return;
                    window.onAddMessageEvent(
                        window.WWebJS.getMessageModel(_msg),
                    );
                });
            });`,
`            const centralMessageKey = (msg) => {
                try {
                    const id = msg?.id;

                    return (
                        id?._serialized ||
                        (
                            id?.remote?._serialized &&
                            id?.id
                                ? \`\${id.remote._serialized}:\${id.id}\`
                                : ''
                        ) ||
                        id?.id ||
                        ''
                    );
                } catch (_) {
                    return '';
                }
            };

            const centralForwarded =
                window.__centralForwardedMessageIds instanceof Set
                    ? window.__centralForwardedMessageIds
                    : new Set();

            window.__centralForwardedMessageIds =
                centralForwarded;

            const centralRemember = (key) => {
                if (!key) return;

                centralForwarded.add(key);

                while (centralForwarded.size > 5000) {
                    const first =
                        centralForwarded.values().next().value;

                    if (!first) break;

                    centralForwarded.delete(first);
                }
            };

            const centralForwardMessage = (msg) => {
                if (!msg) return false;

                if (
                    msg.type === 'ciphertext' ||
                    msg.type === 'gp2'
                ) {
                    return false;
                }

                const key =
                    centralMessageKey(msg);

                if (
                    key &&
                    centralForwarded.has(key)
                ) {
                    return false;
                }

                centralRemember(key);

                window.onAddMessageEvent(
                    window.WWebJS.getMessageModel(msg),
                );

                return true;
            };

            // Evita importar histórico antigo na primeira varredura.
            // Mensagens recentes (até 3 min) permanecem elegíveis para
            // recuperar algo enviado enquanto o motor terminava de iniciar.
            try {
                const now =
                    Math.floor(Date.now() / 1000);

                const existing =
                    typeof Msg.getModelsArray === 'function'
                        ? Msg.getModelsArray()
                        : [];

                for (const oldMsg of existing) {
                    const timestamp =
                        Number(
                            oldMsg?.t ||
                            oldMsg?.timestamp ||
                            0
                        );

                    if (
                        timestamp &&
                        now - timestamp > 180
                    ) {
                        centralRemember(
                            centralMessageKey(oldMsg)
                        );
                    }
                }
            } catch (_) {}

            Msg.on('add', (msg) => {
                if (!msg.isNewMsg) return;

                if (msg.type !== 'ciphertext') {
                    centralForwardMessage(msg);
                    return;
                }

                window.onAddMessageCiphertextEvent(
                    window.WWebJS.getMessageModel(msg),
                );

                if (msg.subtype && msg.subtype.endsWith('_unavailable_fanout'))
                    return;

                requestResend(msg);

                const failTimer = setTimeout(() => {
                    if (msg.type !== 'ciphertext') return;
                    window.onCiphertextFailedEvent(
                        window.WWebJS.getMessageModel(msg),
                    );
                }, 15000);

                msg.once('change:type', (_msg) => {
                    clearTimeout(failTimer);
                    pendingResend.delete(_msg);

                    if (_msg.type === 'revoked') {
                        return;
                    }

                    centralForwardMessage(_msg);
                });
            });

            if (window.__centralMessagePollTimer) {
                clearInterval(
                    window.__centralMessagePollTimer
                );
            }

            window.__centralMessagePollTimer =
                setInterval(() => {
                    try {
                        const now =
                            Math.floor(Date.now() / 1000);

                        const models =
                            typeof Msg.getModelsArray === 'function'
                                ? Msg.getModelsArray()
                                : [];

                        const start =
                            Math.max(
                                0,
                                models.length - 500
                            );

                        for (
                            let index = start;
                            index < models.length;
                            index += 1
                        ) {
                            const msg =
                                models[index];

                            if (!msg) continue;

                            const timestamp =
                                Number(
                                    msg.t ||
                                    msg.timestamp ||
                                    0
                                );

                            if (
                                !timestamp ||
                                now - timestamp > 180
                            ) {
                                continue;
                            }

                            centralForwardMessage(msg);
                        }
                    } catch (_) {}
                }, 1500);`,
  "message event recovery"
);

if (source === originalClient) {
  throw new Error(
    "Nenhuma alteração foi aplicada ao Client.js."
  );
}

fs.writeFileSync(
  clientTarget,
  source,
  "utf8"
);

// ---------------------------------------------------------------------
// 6) MOTOR: NORMALIZAÇÃO ROBUSTA DOS IDs DOS GRUPOS
// ---------------------------------------------------------------------

let engine =
  normalizeLineEndings(
    fs.readFileSync(
      engineTarget,
      "utf8"
    )
  );

const originalEngine =
  engine;

function replaceEngineOnce(
  oldText,
  newText,
  label
) {
  oldText = normalizeLineEndings(
    oldText
  );
  newText = normalizeLineEndings(
    newText
  );

  if (!engine.includes(oldText)) {
    throw new Error(
      `Patch do motor incompatível: trecho não encontrado (${label}).`
    );
  }

  engine =
    engine.replace(
      oldText,
      newText
    );
}

replaceEngineOnce(
`function descobrirGrupo(m) {
  return [
    m.to,
    m.from,
    m.id?.remote,
  ].find(
    id =>
      GRUPOS_ID.includes(id)
  );
}`,
`function normalizarIdWhatsApp(value) {
  if (!value) {
    return "";
  }

  if (typeof value === "string") {
    return value.trim();
  }

  if (
    typeof value === "object"
  ) {
    if (
      typeof value._serialized
      === "string"
    ) {
      return value._serialized.trim();
    }

    if (
      typeof value.user === "string"
      && typeof value.server === "string"
    ) {
      return (
        \`\${value.user}@\${value.server}\`
      );
    }

    if (
      typeof value.id === "string"
    ) {
      return value.id.trim();
    }
  }

  return String(value || "").trim();
}

function extrairGrupoDeId(value) {
  const text =
    normalizarIdWhatsApp(value);

  if (!text) {
    return "";
  }

  if (
    GRUPOS_ID.includes(text)
  ) {
    return text;
  }

  const match =
    text.match(
      /(\\d+(?:-\\d+)?@g\\.us)/i
    );

  if (
    match
    && GRUPOS_ID.includes(
      match[1]
    )
  ) {
    return match[1];
  }

  return "";
}

function descobrirGrupo(m) {
  const candidates = [
    m?.to,
    m?.from,
    m?.id?.remote,
    m?.id?._serialized,
  ];

  for (
    const candidate
    of candidates
  ) {
    const group =
      extrairGrupoDeId(
        candidate
      );

    if (group) {
      return group;
    }
  }

  return "";
}`,
  "group id normalization"
);

replaceEngineOnce(
`  if (
    !descobrirGrupo(
      message
    )
  ) {
    return;
  }

  const texto =`,
`  const grupoEncontrado =
    descobrirGrupo(
      message
    );

  if (!grupoEncontrado) {
    return;
  }

  console.log(
    "MENSAGEM CAPTURADA DO GRUPO:",
    grupoEncontrado,
    "| tipo:",
    message.type || "",
    "| própria:",
    Boolean(
      message.fromMe
      || message.id?.fromMe
    )
  );

  const texto =`,
  "group message diagnostic"
);

replaceEngineOnce(
`    console.log(
      "[LOGIN] PRONTO"
    );`,
`    console.log(
      "[LOGIN] PRONTO"
    );

    console.log(
      "[MONITOR V37] "
      + "aba compartilhada + eventos + "
      + "varredura de recuperação ativos"
    );`,
  "monitor v37 ready marker"
);


// ---------------------------------------------------------------------
// 7) V38 — PIPELINE WHATSAPP -> APPS SCRIPT
// ---------------------------------------------------------------------
//
// A versão antiga que preenchia a planilha e a versão atual usam o mesmo
// axios.post. A regressão estava antes do POST:
// - o Central compartilhava TÍTULO + LINK;
// - o parser esperava LINK + VEÍCULO + TÍTULO + DATA;
// - mensagem somente com link era descartada;
// - message/message_create podiam competir.
// A V38 aceita os dois formatos, usa prévia do WhatsApp quando necessário,
// passa o grupo real ao Apps Script e registra cada etapa do POST.

replaceEngineOnce(
`function interpretarMensagem(texto) {
  const linhas =
    String(texto || "")
      .split(/\\r?\\n/)
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
}`,
`function veiculoPorLink(link) {
  try {
    const host =
      new URL(link)
        .hostname
        .toLowerCase()
        .replace(/^www\\./, "");

    const known = [
      ["folha.uol.com.br", "Folha de S.Paulo"],
      ["estadao.com.br", "Estadão"],
      ["oglobo.globo.com", "O Globo"],
      ["valor.globo.com", "Valor Econômico"],
      ["g1.globo.com", "G1"],
      ["correiobraziliense.com.br", "Correio Braziliense"],
      ["em.com.br", "Estado de Minas"],
      ["nytimes.com", "The New York Times"],
      ["washingtonpost.com", "The Washington Post"],
      ["cnnbrasil.com.br", "CNN Brasil"],
      ["metropoles.com", "Metrópoles"],
      ["uol.com.br", "UOL"],
      ["bbc.com", "BBC"],
      ["reuters.com", "Reuters"],
    ];

    for (
      const [domain, name]
      of known
    ) {
      if (
        host === domain
        || host.endsWith(
          \`.\${domain}\`
        )
      ) {
        return name;
      }
    }

    return host || "Não Informado";

  } catch (_) {
    return "Não Informado";
  }
}

function interpretarMensagem(
  texto,
  message = null
) {
  const linhas =
    String(texto || "")
      .split(/\\r?\\n/)
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

  // Formato histórico:
  // LINK / VEÍCULO / TÍTULO / [AUTOR] / DATA
  let veiculo =
    limparTexto(
      linhas[iLink + 1]
      || ""
    );

  let titulo =
    limparTexto(
      linhas[iLink + 2]
      || ""
    );

  // Formato que o Central usava antes da V38:
  // TÍTULO / LINK
  const tituloAntesDoLink =
    iLink > 0
      ? limparTexto(
        linhas[iLink - 1]
      )
      : "";

  const previewTitle =
    limparTexto(
      message?.title
      || ""
    );

  const previewDescription =
    limparTexto(
      message?.description
      || ""
    );

  if (
    !veiculo
    || /^https?:\\/\\//i.test(
      veiculo
    )
    || ehData(veiculo)
  ) {
    veiculo =
      veiculoPorLink(
        link
      );
  }

  if (
    !titulo
    || /^https?:\\/\\//i.test(
      titulo
    )
    || ehData(titulo)
  ) {
    titulo =
      tituloAntesDoLink
      || previewTitle
      || previewDescription;
  }

  if (!titulo) {
    return null;
  }

  if (!veiculo) {
    veiculo =
      "Não Informado";
  }

  let iData = -1;

  for (
    let i = 0;
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

  if (iData > 0) {
    const candidate =
      limparTexto(
        linhas[iData - 1]
        || ""
      );

    if (
      candidate
      && candidate !== titulo
      && candidate !== veiculo
      && !candidate.includes(
        link
      )
      && pareceAutor(
        candidate
      )
    ) {
      autor = candidate;
    }
  }

  return {
    link,
    veiculo,
    titulo,
    autor,
    dataPublicacao,
  };
}`,
  "V38 parser de notícias"
);

replaceEngineOnce(
`    if (
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
      );`,
`    if (
      ehSomenteLink(
        texto
      )
    ) {
      console.log(
        "MENSAGEM SOMENTE LINK: "
        + "tentando usar a prévia do WhatsApp."
      );
    }

    const noticia =
      interpretarMensagem(
        texto,
        message
      );`,
  "V38 link simples e parser com preview"
);

replaceEngineOnce(
`async function postar(dados) {
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
}`,
`function normalizarRespostaPlanilha(data) {
  if (
    typeof data === "string"
  ) {
    const clean =
      data.trim();

    if (!clean) {
      return {};
    }

    try {
      return JSON.parse(
        clean
      );
    } catch (_) {
      return {
        sucesso: false,
        erro: clean,
      };
    }
  }

  return (
    data
    && typeof data === "object"
      ? data
      : {}
  );
}

function respostaPlanilhaSucesso(resp) {
  return Boolean(
    resp?.sucesso === true
    || resp?.success === true
    || String(
      resp?.status
      || ""
    ).toUpperCase() === "OK"
  );
}

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
      20000,
    maxRedirects:
      10,
    proxy:
      proxy || false,
    validateStatus:
      () => true,
  };

  console.log(
    "[PLANILHA] ENVIANDO:",
    dados.aba || "",
    "|",
    dados.veiculo || "",
    "|",
    dados.titulo || ""
  );

  const r =
    await axios.post(
      APPS_SCRIPT_URL,
      dados,
      cfg
    );

  console.log(
    "[PLANILHA] HTTP:",
    r.status
  );

  const response =
    normalizarRespostaPlanilha(
      r.data
    );

  console.log(
    "[PLANILHA] RESPOSTA:",
    JSON.stringify(
      response
    )
  );

  if (
    r.status < 200
    || r.status >= 300
  ) {
    throw new Error(
      \`Apps Script respondeu HTTP \${r.status}: \`
      + JSON.stringify(
        response
      )
    );
  }

  return response;
}`,
  "V38 diagnóstico e resposta do Apps Script"
);

// O grupo era conhecido pelo motor, mas o payload enviava string vazia.
// Mantemos compatibilidade e preenchemos o campo com o JID real.
replaceEngineOnce(
`          grupo:
            "",`,
`          grupo:
            grupoEncontrado,`,
  "V38 grupo real no vídeo"
);

replaceEngineOnce(
`        grupo:
          "",`,
`        grupo:
          grupoEncontrado,`,
  "V38 grupo real na notícia"
);

// Aceita o contrato histórico {sucesso:true} e também respostas equivalentes.
replaceEngineOnce(
`      resp?.sucesso`,
`      respostaPlanilhaSucesso(
        resp
      )`,
  "V38 sucesso vídeo"
);

replaceEngineOnce(
`      resp?.sucesso`,
`      respostaPlanilhaSucesso(
        resp
      )`,
  "V38 sucesso notícia"
);

// message_create é emitido tanto para mensagens recebidas quanto enviadas.
// Usamos ambos os eventos como redundância, mas uma trava impede POST duplo
// enquanto a primeira cópia da mesma mensagem ainda está em processamento.
replaceEngineOnce(
`client.on(
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
);`,
`const mensagensEmProcessamento =
  new Set();

function chaveMensagem(
  message
) {
  return String(
    message?.id?._serialized
    || message?.id?.id
    || [
      message?.timestamp
      || "",
      message?.from
      || "",
      message?.to
      || "",
      message?.body
      || "",
    ].join("|")
  );
}

function encaminharMensagem(
  message,
  origem
) {
  const key =
    chaveMensagem(
      message
    );

  if (
    key
    && mensagensEmProcessamento.has(
      key
    )
  ) {
    return;
  }

  if (key) {
    mensagensEmProcessamento.add(
      key
    );
  }

  Promise
    .resolve(
      enviarParaPlanilha(
        message
      )
    )
    .catch(
      erro => {
        console.error(
          "ERRO NO PIPELINE DA MENSAGEM:",
          origem,
          erro?.message
          || erro
        );
      }
    )
    .finally(
      () => {
        if (key) {
          mensagensEmProcessamento.delete(
            key
          );
        }
      }
    );
}

client.on(
  "message",
  message =>
    encaminharMensagem(
      message,
      "message"
    )
);

client.on(
  "message_create",
  message =>
    encaminharMensagem(
      message,
      "message_create"
    )
);`,
  "V38 eventos redundantes sem duplicar POST"
);

// A V37 já introduziu grupoEncontrado. Agora o log de pronto confirma
// configuração real carregada no processo e valida os grupos conhecidos.
replaceEngineOnce(
`    console.log(
      "[MONITOR V37] "
      + "aba compartilhada + eventos + "
      + "varredura de recuperação ativos"
    );`,
`    console.log(
      "[MONITOR V38] "
      + "captura + parser compatível + "
      + "envio diagnosticado ativos"
    );

    console.log(
      "[CONFIG MOTOR] grupos:",
      GRUPOS_ID.length,
      "| Apps Script:",
      APPS_SCRIPT_URL
        ? "CONFIGURADO"
        : "AUSENTE"
    );

    setTimeout(
      async () => {
        for (
          const groupId
          of GRUPOS_ID
        ) {
          try {
            const chat =
              await client.getChatById(
                groupId
              );

            console.log(
              "[GRUPO VALIDADO]",
              groupId,
              "|",
              chat?.name
              || "sem nome"
            );
          } catch (erro) {
            console.error(
              "[GRUPO NÃO VALIDADO]",
              groupId,
              "|",
              erro?.message
              || erro
            );
          }
        }
      },
      1800
    );`,
  "V38 diagnóstico de configuração e grupos"
);

// Se a mensagem for de grupo mas o JID não for um dos três configurados,
// deixa evidência no log em vez de descartar silenciosamente.
replaceEngineOnce(
`  if (!grupoEncontrado) {
    return;
  }

  console.log(
    "MENSAGEM CAPTURADA DO GRUPO:",`,
`  if (!grupoEncontrado) {
    const candidates = [
      message?.from,
      message?.to,
      message?.id?.remote,
      message?.id?._serialized,
    ]
      .map(
        value =>
          normalizarIdWhatsApp(
            value
          )
      )
      .filter(Boolean);

    if (
      candidates.some(
        value =>
          value.includes(
            "@g.us"
          )
      )
    ) {
      console.log(
        "[GRUPO IGNORADO/NÃO CONFIGURADO]",
        candidates.join(
          " | "
        )
      );
    }

    return;
  }

  console.log(
    "MENSAGEM CAPTURADA DO GRUPO:",`,
  "V38 log de grupo não reconhecido"
);


if (engine === originalEngine) {
  throw new Error(
    "Nenhuma alteração foi aplicada ao engine/index.js."
  );
}

fs.writeFileSync(
  engineTarget,
  engine,
  "utf8"
);

// ---------------------------------------------------------------------
// 8) V40 — CHROME COMPARTILHADO + PROXY GERAL
// ---------------------------------------------------------------------
//
// O proxy do Chrome é um argumento de inicialização (--proxy-server).
// Portanto um Chrome antigo NÃO pode ser simplesmente reutilizado quando
// a configuração do Proxy Geral muda. A V40 salva apenas uma assinatura
// (senha em SHA-256), reinicia o Chrome quando necessário e testa a rota
// web.whatsapp.com antes de entregar o navegador ao whatsapp-web.js.

let mainSource =
  normalizeLineEndings(
    fs.readFileSync(
      mainTarget,
      "utf8"
    )
  );

const originalMain =
  mainSource;

function replaceMainOnce(
  oldText,
  newText,
  label
) {
  oldText =
    normalizeLineEndings(
      oldText
    );

  newText =
    normalizeLineEndings(
      newText
    );

  if (
    !mainSource.includes(
      oldText
    )
  ) {
    throw new Error(
      `Patch do main.js incompatível: trecho não encontrado (${label}).`
    );
  }

  mainSource =
    mainSource.replace(
      oldText,
      newText
    );
}

replaceMainOnce(
`function chromeProxyArg() {
  const p =
    effectiveProxyConfig(
      readConfig()
    );

  if (
    p?.ativo
    && p?.host
    && Number(p?.porta)
  ) {
    return (
      \`--proxy-server=http://\`
      + \`\${String(p.host).trim()}:\`
      + \`\${Number(p.porta)}\`
    );
  }

  return "--no-proxy-server";
}

async function ensureSharedChrome() {`,
`function chromeProxyArg() {
  const p =
    effectiveProxyConfig(
      readConfig()
    );

  if (
    p?.ativo
    && p?.host
    && Number(p?.porta)
  ) {
    return (
      \`--proxy-server=http://\`
      + \`\${String(p.host).trim()}:\`
      + \`\${Number(p.porta)}\`
    );
  }

  return "--no-proxy-server";
}

function sharedNetworkStateFile() {
  return path.join(
    path.dirname(
      sharedPidFile()
    ),
    "whatsapp_chrome_network.json"
  );
}

function desiredSharedNetworkState() {
  const crypto =
    require("crypto");

  const p =
    effectiveProxyConfig(
      readConfig()
    );

  const enabled =
    Boolean(
      p?.ativo
    );

  const host =
    enabled
      ? String(
        p?.host
        || ""
      ).trim()
      : "";

  const port =
    enabled
      ? Number(
        p?.porta
        || 0
      )
      : 0;

  const username =
    enabled
      ? String(
        p?.usuario
        || ""
      ).trim()
      : "";

  const password =
    enabled
      ? String(
        p?.senha
        || ""
      )
      : "";

  const secretHash =
    crypto
      .createHash(
        "sha256"
      )
      .update(
        [
          enabled
            ? "1"
            : "0",
          host,
          String(port),
          username,
          password,
        ].join("\\n"),
        "utf8"
      )
      .digest(
        "hex"
      );

  return {
    version: 40,
    proxyEnabled:
      enabled,
    host,
    port,
    username,
    secretHash,
  };
}

function readSharedNetworkState() {
  try {
    return JSON.parse(
      fs.readFileSync(
        sharedNetworkStateFile(),
        "utf8"
      )
    );
  } catch (_) {
    return null;
  }
}

function writeSharedNetworkState(
  state
) {
  try {
    const file =
      sharedNetworkStateFile();

    fs.mkdirSync(
      path.dirname(file),
      {
        recursive: true,
      }
    );

    fs.writeFileSync(
      file,
      JSON.stringify(
        state,
        null,
        2
      ),
      "utf8"
    );
  } catch (_) {}
}

function sameSharedNetworkState(
  current,
  desired
) {
  return Boolean(
    current
    && desired
    && current.version
      === desired.version
    && current.proxyEnabled
      === desired.proxyEnabled
    && String(
      current.host
      || ""
    )
      === String(
        desired.host
        || ""
      )
    && Number(
      current.port
      || 0
    )
      === Number(
        desired.port
        || 0
      )
    && String(
      current.username
      || ""
    )
      === String(
        desired.username
        || ""
      )
    && String(
      current.secretHash
      || ""
    )
      === String(
        desired.secretHash
        || ""
      )
  );
}

function readSharedPid() {
  try {
    return Number(
      fs.readFileSync(
        sharedPidFile(),
        "utf8"
      ).trim()
    ) || 0;
  } catch (_) {
    return 0;
  }
}

async function stopSharedChromeForNetworkChange(
  reason
) {
  const pid =
    readSharedPid();

  parseLine(
    \`CHROME COMPARTILHADO: reiniciando por configuração de rede (\${reason}).\`,
    false
  );

  if (
    pid > 0
    && process.platform === "win32"
  ) {
    try {
      const {
        spawnSync,
      } =
        require(
          "child_process"
        );

      spawnSync(
        "taskkill",
        [
          "/PID",
          String(pid),
          "/T",
          "/F",
        ],
        {
          windowsHide: true,
          stdio: "ignore",
        }
      );
    } catch (_) {}
  } else if (
    pid > 0
  ) {
    try {
      process.kill(
        pid,
        "SIGTERM"
      );
    } catch (_) {}
  }

  for (
    let attempt = 1;
    attempt <= 24;
    attempt += 1
  ) {
    if (
      !await sharedBrowserResponding()
    ) {
      break;
    }

    await new Promise(
      resolve =>
        setTimeout(
          resolve,
          250
        )
    );
  }

  if (
    await sharedBrowserResponding()
  ) {
    throw new Error(
      "O Chrome compartilhado antigo continua ativo na porta 9223. "
      + "Feche a sessão do WhatsApp pelo Central e tente novamente."
    );
  }

  try {
    fs.unlinkSync(
      sharedPidFile()
    );
  } catch (_) {}

  try {
    fs.unlinkSync(
      sharedNetworkStateFile()
    );
  } catch (_) {}
}

async function testWhatsAppThroughCentralProxy() {
  const p =
    effectiveProxyConfig(
      readConfig()
    );

  if (
    !p?.ativo
  ) {
    parseLine(
      "TESTE WHATSAPP: conexão direta selecionada.",
      false
    );

    return;
  }

  const host =
    String(
      p?.host
      || ""
    ).trim();

  const port =
    Number(
      p?.porta
      || 0
    );

  const username =
    String(
      p?.usuario
      || ""
    ).trim();

  const password =
    String(
      p?.senha
      || ""
    );

  if (
    !host
    || !port
    || !username
    || !password
  ) {
    throw new Error(
      "Proxy Geral está ativo, mas host/porta/usuário/senha estão incompletos."
    );
  }

  parseLine(
    \`TESTE WHATSAPP VIA PROXY: \${host}:\${port}\`,
    false
  );

  try {
    const response =
      await axios.get(
        "https://web.whatsapp.com/",
        {
          timeout: 18000,
          maxRedirects: 5,
          proxy: {
            protocol:
              "http",
            host,
            port,
            auth: {
              username,
              password,
            },
          },
          validateStatus:
            () => true,
          headers: {
            "User-Agent":
              "Mozilla/5.0 "
              + "(Windows NT 10.0; Win64; x64) "
              + "AppleWebKit/537.36 "
              + "(KHTML, like Gecko) "
              + "Chrome/131.0 Safari/537.36",
          },
        }
      );

    if (
      response.status === 407
    ) {
      throw new Error(
        "HTTP 407 - credenciais rejeitadas pelo proxy."
      );
    }

    if (
      response.status < 200
      || response.status >= 500
    ) {
      throw new Error(
        \`HTTP \${response.status}\`
      );
    }

    parseLine(
      \`TESTE WHATSAPP VIA PROXY: OK (HTTP \${response.status}).\`,
      false
    );

  } catch (error) {
    const detail =
      error?.code
      || error?.message
      || String(error);

    throw new Error(
      "O Proxy Geral não conseguiu acessar https://web.whatsapp.com/. "
      + \`Detalhe: \${detail}\`
    );
  }
}

async function ensureSharedChrome() {`,
  "V40 helpers de rede do Chrome compartilhado"
);

replaceMainOnce(
`  if (
    await sharedBrowserResponding()
  ) {
    parseLine(
      "CHROME COMPARTILHADO: reutilizando sessão já aberta.",
      false
    );

    return {
      ok: true,
      reused: true,
    };
  }

  const chrome =`,
`  const desiredNetwork =
    desiredSharedNetworkState();

  if (
    await sharedBrowserResponding()
  ) {
    const currentNetwork =
      readSharedNetworkState();

    if (
      sameSharedNetworkState(
        currentNetwork,
        desiredNetwork
      )
    ) {
      parseLine(
        "CHROME COMPARTILHADO: reutilizando sessão já aberta com a mesma configuração de rede.",
        false
      );

      return {
        ok: true,
        reused: true,
      };
    }

    await stopSharedChromeForNetworkChange(
      currentNetwork
        ? "Proxy Geral alterado"
        : "Chrome iniciado por versão anterior"
    );
  }

  await testWhatsAppThroughCentralProxy();

  const chrome =`,
  "V40 validar/reiniciar Chrome antes do reuso"
);

replaceMainOnce(
`    "--disable-background-mode",
    "--disable-features=Translate",
    "--start-maximized",`,
`    "--disable-background-mode",
    "--disable-features=Translate",
    "--disable-quic",
    "--start-maximized",`,
  "V40 desabilitar QUIC no Chrome compartilhado"
);

replaceMainOnce(
`      return {
        ok: true,
        reused: false,
        pid: child.pid,
      };`,
`      writeSharedNetworkState(
        desiredNetwork
      );

      return {
        ok: true,
        reused: false,
        pid: child.pid,
      };`,
  "V40 persistir assinatura de rede"
);

if (
  mainSource === originalMain
) {
  throw new Error(
    "Nenhuma alteração foi aplicada ao main.js."
  );
}

fs.writeFileSync(
  mainTarget,
  mainSource,
  "utf8"
);

// Validação final dos JavaScripts que foram alterados.
const { spawnSync } =
  require("child_process");

for (const target of [
  clientTarget,
  engineTarget,
  mainTarget,
]) {
  const check =
    spawnSync(
      process.execPath,
      [
        "--check",
        target,
      ],
      {
        stdio: "inherit",
      }
    );

  if (
    check.status !== 0
  ) {
    throw new Error(
      `Validação JavaScript falhou: ${target}`
    );
  }
}

console.log(
  "V40 aplicada: sessão compartilhada, pipeline Planilhas e "
  + "Chrome com Proxy Geral validado/reiniciado automaticamente."
);
