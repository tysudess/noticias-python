const $ = id =>
  document.getElementById(id);

const log = $("log");
let currentConfig = null;

function addLog(
  line,
  isErr = false
) {
  if (!line) {
    return;
  }

  log.textContent +=
    `\n${isErr ? "[ERRO] " : ""}${line}`;

  log.scrollTop =
    log.scrollHeight;
}

function statusClass(
  el,
  value
) {
  const v =
    String(
      value || ""
    ).toUpperCase();

  el.style.color =
    (
      v.includes("CONECTADO")
      || v === "OK"
      || v.includes("ATIVO")
      || v.includes("AUTENTICADO")
    )
      ? "#50ef7e"
      : (
        v.includes("ERRO")
        || v.includes("DESCONECTADO")
        || v.includes("REJEITADA")
        || v.includes("REJEITADAS")
      )
        ? "#ff6670"
        : "#ffd966";
}

function showStatus(s) {
  const motor =
    s.status || "-";

  const whats =
    s.whatsapp || "-";

  const sheet =
    s.planilha || "-";

  const proxy =
    s.proxy || "-";

  $("statusMotor").textContent =
    motor;

  $("statusWhats").textContent =
    whats;

  $("statusSheet").textContent =
    sheet;

  $("summaryMotor").textContent =
    motor;

  $("count").textContent =
    s.processadas ?? 0;

  $("videoCount").textContent =
    s.videos ?? 0;

  $("errorCount").textContent =
    s.erros ?? 0;

  $("lastLine").textContent =
    s.ultimaLinha || "--";

  $("lastUpdate").textContent =
    s.ultimaAtualizacao || "--";

  $("proxyStatus").textContent =
    proxy;

  $("bottomStatus").textContent =
    motor === "RODANDO"
      ? "Sistema iniciado e monitorando..."
      : motor === "PARADO"
        ? "Sistema pronto para iniciar."
        : `Sistema: ${motor}`;

  statusClass(
    $("statusMotor"),
    motor
  );

  statusClass(
    $("statusWhats"),
    whats
  );

  statusClass(
    $("statusSheet"),
    sheet
  );

  statusClass(
    $("proxyStatus"),
    proxy
  );

  const n =
    s.ultimaNoticia || {};

  $("lastTitle").textContent =
    n.titulo
    || "Nenhuma notícia processada ainda";

  $("lastVehicle").textContent =
    n.veiculo || "--";

  $("lastDate").textContent =
    n.data || "--";

  $("lastSubject").textContent =
    n.assunto || "--";

  $("lastAnalysis").textContent =
    n.analise || "--";

  $("lastAuthor").textContent =
    n.autor || "--";
}

function renderGroups(c) {
  const list =
    $("groupList");

  list.innerHTML = "";

  const groups =
    c.grupos || [];

  groups.forEach(
    (id, idx) => {
      const item =
        document.createElement(
          "div"
        );

      item.className =
        "group-item";

      item.innerHTML =
        `<div class="group-badge">♟</div>`
        + `<div><strong>Grupo ${idx + 1}</strong>`
        + `<small>${id}</small></div>`
        + `<span class="pill">ATIVO</span>`;

      list.appendChild(
        item
      );
    }
  );

  $("totalGroups").textContent =
    `Total: ${groups.length} grupo`
    + `${groups.length === 1 ? "" : "s"}`;
}

async function loadConfig() {
  currentConfig =
    await window.api.getConfig();

  $("appsUrl").value =
    currentConfig.appsScriptUrl
    || "";

  $("aba").value =
    "Automática pela data da matéria";

  $("chrome").value =
    currentConfig.chromePath
    || "";

  $("grupos").value =
    (
      currentConfig.grupos
      || []
    ).join("\n");

  $("diag").checked =
    !!currentConfig.diagnosticoGrupos;

  const localProxy =
    currentConfig.proxy
    || {};

  const runtimeProxy =
    currentConfig.runtimeProxy
    || {};

  const managed =
    !!runtimeProxy.managedByCentral;

  const p =
    managed
      ? runtimeProxy
      : localProxy;

  $("proxyAtivo").checked =
    !!p.ativo;

  $("proxyHost").value =
    p.host || "";

  $("proxyPorta").value =
    p.porta || "";

  $("proxyUsuario").value =
    p.usuario || "";

  // Nunca traz a senha do Proxy Geral para o renderer.
  $("proxySenha").value =
    managed
      ? ""
      : (
        localProxy.senha
        || ""
      );

  for (
    const id
    of [
      "proxyAtivo",
      "proxyHost",
      "proxyPorta",
      "proxyUsuario",
      "proxySenha",
    ]
  ) {
    $(id).disabled =
      managed;
  }

  if (managed) {
    $("proxyTestResult").textContent =
      p.ativo
        ? "Proxy controlado pelas Configurações gerais do Central."
        : "Proxy Geral do Central está desativado.";
  }

  renderGroups(
    currentConfig
  );
}

function switchView(viewId) {
  document
    .querySelectorAll(
      ".view"
    )
    .forEach(
      v =>
        v.classList.remove(
          "active-view"
        )
    );

  document
    .querySelectorAll(
      ".nav-btn"
    )
    .forEach(
      b =>
        b.classList.remove(
          "active"
        )
    );

  const view =
    document.getElementById(
      viewId
    );

  if (view) {
    view.classList.add(
      "active-view"
    );
  }

  const btn =
    document.querySelector(
      `.nav-btn[data-view="${viewId}"]`
    );

  if (btn) {
    btn.classList.add(
      "active"
    );
  }
}

document
  .querySelectorAll(
    ".nav-btn"
  )
  .forEach(
    btn =>
      btn.addEventListener(
        "click",
        () =>
          switchView(
            btn.dataset.view
          )
      )
  );

function formConfig() {
  return {
    ...currentConfig,

    appsScriptUrl:
      $("appsUrl")
        .value
        .trim(),

    chromePath:
      $("chrome")
        .value
        .trim(),

    diagnosticoGrupos:
      $("diag").checked,

    grupos:
      $("grupos")
        .value
        .split(/\r?\n/)
        .map(
          x => x.trim()
        )
        .filter(Boolean),

    proxy: {
      ativo:
        $("proxyAtivo")
          .checked,

      host:
        $("proxyHost")
          .value
          .trim(),

      porta:
        Number(
          $("proxyPorta")
            .value
        ) || 0,

      usuario:
        $("proxyUsuario")
          .value
          .trim(),

      senha:
        $("proxySenha")
          .value,
    },
  };
}

async function pasteAppsScriptUrl() {
  const field =
    $("appsUrl");

  const feedback =
    $("appsPasteResult");

  try {
    const text =
      String(
        await window.api
          .readClipboardText()
        || ""
      ).trim();

    if (!text) {
      feedback.textContent =
        "A área de transferência está vazia.";

      field.focus();
      return;
    }

    field.value =
      text;

    field.focus();

    try {
      field.setSelectionRange(
        field.value.length,
        field.value.length
      );
    } catch (_) {}

    feedback.textContent =
      "Conteúdo colado com sucesso.";

    addLog(
      "Apps Script colado a partir da área de transferência."
    );

  } catch (error) {
    feedback.textContent =
      "Não foi possível ler a área de transferência.";

    addLog(
      `Falha ao colar Apps Script: ${
        error?.message
        || error
      }`,
      true
    );
  }
}

// Mantém Ctrl+V funcionando quando o foco realmente chega ao input.
// O botão COLAR existe como fallback confiável para o Electron incorporado.
$("appsUrl").addEventListener(
  "keydown",
  event => {
    if (
      (
        event.ctrlKey
        || event.metaKey
      )
      && String(
        event.key
      ).toLowerCase()
        === "v"
    ) {
      // Não chama preventDefault:
      // deixa o Chromium executar o paste nativo.
      $("appsPasteResult").textContent =
        "Colando...";
    }
  }
);

$("appsUrl").addEventListener(
  "paste",
  () => {
    setTimeout(
      () => {
        $("appsPasteResult").textContent =
          "Conteúdo colado com sucesso.";
      },
      0
    );
  }
);

$("pasteAppsUrl")
  .addEventListener(
    "click",
    pasteAppsScriptUrl
  );

// O click do checkbox agora é tratado explicitamente.
// Isso evita a sensação de que "não ativou" quando o teste era feito antes
// de salvar e ainda lia o valor antigo do config.json.
$("proxyAtivo")
  .addEventListener(
    "change",
    () => {
      $("proxyTestResult").textContent =
        $("proxyAtivo").checked
          ? "Proxy marcado como ativo. Você já pode testar antes de salvar."
          : "Proxy marcado como desativado.";
    }
  );

$("start").onclick =
  async () => {
    const r =
      await window.api.start();

    if (r.message) {
      addLog(
        r.message
      );
    }
  };

$("loginWhats").onclick =
  async () => {
    const r =
      await window.api.startLogin();

    if (r.message) {
      addLog(
        r.message
      );
    }
  };

$("stop").onclick =
  async () => {
    const r =
      await window.api.stop();

    if (r.message) {
      addLog(
        r.message
      );
    }
  };

$("openLog").onclick =
  () =>
    switchView(
      "logview"
    );

$("openCfg").onclick =
  () =>
    window.api
      .openConfigFolder();

$("testProxy").onclick =
  async () => {
    const btn =
      $("testProxy");

    btn.disabled =
      true;

    $("proxyTestResult").textContent =
      "Testando proxy...";

    const r =
      await window.api
        .testProxy(
          formConfig()
        );

    addLog(
      r.message
      || "Teste do proxy concluído.",
      !r.ok
    );

    $("proxyTestResult").textContent =
      r.message
      || "Concluído.";

    btn.disabled =
      false;

    showStatus(
      await window.api
        .getStatus()
    );
  };

$("saveCfg").onclick =
  async () => {
    const cfg =
      formConfig();

    delete cfg.aba;

    const r =
      await window.api
        .saveConfig(
          cfg
        );

    addLog(
      r.ok
        ? "Configurações salvas. Proxy com autenticação disponível."
        : "Falha ao salvar configurações.",
      !r.ok
    );

    if (r.ok) {
      currentConfig =
        cfg;

      renderGroups(
        cfg
      );
    }
  };

$("clearLog").onclick =
  () => {
    log.textContent =
      "";
  };

window.api.onStatus(
  showStatus
);

window.api.onLog(
  ({
    line,
    isErr,
  }) =>
    addLog(
      line,
      isErr
    )
);

(async () => {
  showStatus(
    await window.api
      .getStatus()
  );

  await loadConfig();
})();
