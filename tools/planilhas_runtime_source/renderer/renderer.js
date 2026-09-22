const $ = id =>
  document.getElementById(id);

const log = $("log");
let currentConfig = null;

const DEFAULT_APPS_SCRIPT_URL =
  "https://script.google.com/macros/s/AKfycbz9zWPX0OgVa7obrmqm5WSu1fImaTiyWz0pR3wuc13xl-uCS5KYTF4rhbRitrv26PBh/exec";

const DEFAULT_GROUPS = [
  "556191047689-1555547406@g.us",
  "120363025807487932@g.us",
  "556192528699-1447447254@g.us",
];

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
  if (!el) {
    return;
  }

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

function validGroups(groups) {
  if (!Array.isArray(groups)) {
    return [];
  }

  return groups
    .map(
      item =>
        String(item || "")
          .trim()
    )
    .filter(Boolean);
}

function normalizeConfig(config) {
  const source =
    config
    && typeof config === "object"
      ? { ...config }
      : {};

  let changed = false;

  const appsScriptUrl =
    String(
      source.appsScriptUrl
      || ""
    ).trim();

  if (!appsScriptUrl) {
    source.appsScriptUrl =
      DEFAULT_APPS_SCRIPT_URL;
    changed = true;
  } else {
    source.appsScriptUrl =
      appsScriptUrl;
  }

  const groups =
    validGroups(
      source.grupos
    );

  if (!groups.length) {
    source.grupos =
      [...DEFAULT_GROUPS];
    changed = true;
  } else {
    source.grupos =
      groups;
  }

  if (
    typeof source.diagnosticoGrupos
    !== "boolean"
  ) {
    source.diagnosticoGrupos =
      false;
    changed = true;
  }

  if (
    typeof source.chromePath
    !== "string"
  ) {
    source.chromePath =
      "";
    changed = true;
  }

  // Mantém o bloco apenas por compatibilidade do runtime.
  // A interface NÃO exibe nem edita proxy; quando aberto pelo Central,
  // CENTRAL_PROXY_* continua tendo prioridade no processo principal.
  if (
    !source.proxy
    || typeof source.proxy !== "object"
    || Array.isArray(source.proxy)
  ) {
    source.proxy = {
      ativo: false,
      host: "",
      porta: 0,
      usuario: "",
      senha: "",
    };
    changed = true;
  }

  return {
    config: source,
    changed,
  };
}

function renderGroups(c) {
  const list =
    $("groupList");

  list.innerHTML = "";

  const groups =
    validGroups(
      c.grupos
    );

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
  const loaded =
    await window.api
      .getConfig();

  const normalized =
    normalizeConfig(
      loaded
    );

  currentConfig =
    normalized.config;

  if (normalized.changed) {
    const saved =
      await window.api
        .saveConfig(
          currentConfig
        );

    if (saved?.ok) {
      addLog(
        "Configuração padrão restaurada automaticamente: Apps Script e grupos monitorados."
      );
    } else {
      addLog(
        "Não foi possível salvar automaticamente os padrões da Automação.",
        true
      );
    }
  }

  $("appsUrl").value =
    currentConfig.appsScriptUrl
    || DEFAULT_APPS_SCRIPT_URL;

  $("aba").value =
    "Automática pela data da matéria";

  $("chrome").value =
    currentConfig.chromePath
    || "";

  $("grupos").value =
    validGroups(
      currentConfig.grupos
    ).join("\n");

  $("diag").checked =
    !!currentConfig.diagnosticoGrupos;

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
  const groups =
    $("grupos")
      .value
      .split(/\r?\n/)
      .map(
        x => x.trim()
      )
      .filter(Boolean);

  return {
    ...currentConfig,

    appsScriptUrl:
      $("appsUrl")
        .value
        .trim()
      || DEFAULT_APPS_SCRIPT_URL,

    chromePath:
      $("chrome")
        .value
        .trim(),

    diagnosticoGrupos:
      $("diag").checked,

    grupos:
      groups.length
        ? groups
        : [...DEFAULT_GROUPS],

    // O proxy não é editável nesta interface.
    // Preserva apenas o bloco de compatibilidade já existente.
    proxy:
      currentConfig?.proxy
      || {
        ativo: false,
        host: "",
        porta: 0,
        usuario: "",
        senha: "",
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

  } catch (_) {
    feedback.textContent =
      "Use Ctrl+V ou mantenha a URL padrão.";
  }
}

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

$("saveCfg").onclick =
  async () => {
    const cfg =
      formConfig();

    const r =
      await window.api
        .saveConfig(
          cfg
        );

    addLog(
      r.ok
        ? "Configurações salvas."
        : "Falha ao salvar configurações.",
      !r.ok
    );

    if (r.ok) {
      currentConfig =
        cfg;

      $("appsUrl").value =
        cfg.appsScriptUrl;

      $("grupos").value =
        validGroups(
          cfg.grupos
        ).join("\n");

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
