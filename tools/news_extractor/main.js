const { app, BrowserWindow, ipcMain, shell, clipboard, safeStorage, Menu } = require('electron');
const fs = require('fs');
const path = require('path');

// V1.25.10 usa uma camada de correções sobre o motor V1.25.1.
// O arquivo original permanece preservado e pode ser reutilizado sem alterações.
const motor = require('./engine/extrator-materia-v1.25.10-runtime.js');
const corretorRigido = require('./engine/corretor-rigido-ptbr-v1.25.19.js');

const PASTA_NOME = 'ExtratorMaterias';
const ARQUIVO_ULTIMO = 'materia-extraida.txt';
const ARQUIVO_HISTORICO = 'materias-extraidas.txt';
const ARQUIVO_CREDENCIAIS_ASSINANTE = 'credenciais-assinante.json';
const PROVEDOR_VALOR_GLOBO = 'valorGlobo';
const SEPARADOR = '\n' + '#'.repeat(70) + '\n\n';

let mainWindow = null;
let extractionBusy = false;
let idiomaCorretor = 'pt-BR';

function pastaDownload() {
  return path.join(app.getPath('downloads'), PASTA_NOME);
}
function caminhoUltimo() { return path.join(pastaDownload(), ARQUIVO_ULTIMO); }
function caminhoHistorico() { return path.join(pastaDownload(), ARQUIVO_HISTORICO); }
function caminhoCredenciaisAssinante() {
  return path.join(app.getPath('userData'), ARQUIVO_CREDENCIAIS_ASSINANTE);
}

function status(mensagem) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('extracao-status', mensagem);
  }
}

function normalizarProvedor(provedor) {
  const p = String(provedor || '').trim();
  if (!p || p === PROVEDOR_VALOR_GLOBO) return PROVEDOR_VALOR_GLOBO;
  throw new Error('Provedor de assinante não suportado nesta versão.');
}

function lerCofreCredenciais() {
  const arquivo = caminhoCredenciaisAssinante();
  try {
    if (!fs.existsSync(arquivo)) return {};
    const bruto = JSON.parse(fs.readFileSync(arquivo, 'utf8').replace(/^\uFEFF/, ''));
    return bruto && typeof bruto === 'object' ? bruto : {};
  } catch (_) {
    return {};
  }
}

function gravarCofreCredenciais(cofre) {
  const arquivo = caminhoCredenciaisAssinante();
  fs.mkdirSync(path.dirname(arquivo), { recursive: true });
  fs.writeFileSync(arquivo, JSON.stringify(cofre, null, 2), 'utf8');
}

function descriptografarCredenciaisAssinante(provedor) {
  const p = normalizarProvedor(provedor);
  const cofre = lerCofreCredenciais();
  const registro = cofre[p];
  if (!registro || !registro.payload) return null;
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('A proteção de credenciais do Windows não está disponível neste computador.');
  }

  try {
    const buffer = Buffer.from(String(registro.payload), 'base64');
    const texto = safeStorage.decryptString(buffer);
    const dados = JSON.parse(texto);
    const usuario = String(dados?.usuario || '').trim();
    const senha = String(dados?.senha || '');
    if (!usuario || !senha) return null;
    return { usuario, senha };
  } catch (_) {
    throw new Error('Não foi possível abrir as credenciais salvas neste Windows. Apague e salve o acesso novamente.');
  }
}

function obterResumoCredenciaisAssinante(provedor) {
  const credenciais = descriptografarCredenciaisAssinante(provedor);
  if (!credenciais) return { ok: true, salvo: false, usuario: '', temSenha: false };
  return {
    ok: true,
    salvo: true,
    usuario: credenciais.usuario,
    temSenha: !!credenciais.senha
  };
}

function salvarCredenciaisAssinante(provedor, dados = {}) {
  const p = normalizarProvedor(provedor);
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('A proteção de credenciais do Windows não está disponível neste computador. O acesso não será salvo sem criptografia.');
  }

  const usuario = String(dados.usuario || '').trim();
  if (!usuario) throw new Error('Informe o usuário/e-mail da assinatura.');

  let senha = String(dados.senha || '');
  if (!senha) {
    const anterior = descriptografarCredenciaisAssinante(p);
    senha = String(anterior?.senha || '');
  }
  if (!senha) throw new Error('Informe a senha da assinatura.');

  const payload = safeStorage
    .encryptString(JSON.stringify({ usuario, senha }))
    .toString('base64');

  const cofre = lerCofreCredenciais();
  cofre[p] = {
    payload,
    atualizadoEm: new Date().toISOString(),
    formato: 1
  };
  gravarCofreCredenciais(cofre);

  return { ok: true, salvo: true, usuario, temSenha: true };
}

function apagarCredenciaisAssinante(provedor) {
  const p = normalizarProvedor(provedor);
  const cofre = lerCofreCredenciais();
  if (Object.prototype.hasOwnProperty.call(cofre, p)) {
    delete cofre[p];
    if (Object.keys(cofre).length) gravarCofreCredenciais(cofre);
    else {
      try { fs.unlinkSync(caminhoCredenciaisAssinante()); } catch (_) {}
    }
  }
  return { ok: true, salvo: false, usuario: '', temSenha: false };
}

function carregarConfigProxyLocal() {
  const arquivo = path.join(__dirname, 'engine', 'config-proxy.json');
  const padrao = {
    ATIVADO: false,
    SERVIDOR: '',
    PORTA: '',
    TIMEOUT_MS: 45000,
    CERTIFICADO_CA: ''
  };
  try {
    if (!fs.existsSync(arquivo)) return padrao;
    return { ...padrao, ...JSON.parse(fs.readFileSync(arquivo, 'utf8').replace(/^\uFEFF/, '')) };
  } catch (_) {
    return padrao;
  }
}

function configurarConexao(opcoes = {}) {
  const usarProxy = opcoes.usarProxy === true;
  const config = carregarConfigProxyLocal();

  if (!usarProxy) {
    motor.prepararProxy('', '', { ...config, ATIVADO: false });
    return { proxy: false, descricao: 'Conexão direta' };
  }

  const usuario = String(opcoes.usuario || '').trim();
  const senha = String(opcoes.senha || '');
  if (!usuario) throw new Error('Informe o usuário do proxy.');
  if (!senha) throw new Error('Informe a senha do proxy.');

  motor.prepararProxy(usuario, senha, { ...config, ATIVADO: true });
  return { proxy: true, descricao: 'Proxy corporativo ativo' };
}

function salvarResultado(materia) {
  fs.mkdirSync(pastaDownload(), { recursive: true });
  fs.writeFileSync(caminhoUltimo(), materia.resultado, 'utf8');

  const repetida = motor.historicoContemUrl(materia.url, caminhoHistorico());
  if (!repetida) {
    fs.appendFileSync(caminhoHistorico(), materia.resultado + SEPARADOR, 'utf8');
  }

  return repetida;
}

async function extrairMateriaGUI(opcoes) {
  if (extractionBusy) return { ok: false, erro: 'Já existe uma extração em andamento.' };

  const url = String(opcoes?.url || '').trim();
  if (!url) return { ok: false, erro: 'Cole o link da matéria.' };
  if (!/^https?:\/\//i.test(url)) return { ok: false, erro: 'O link precisa começar com http:// ou https://' };

  extractionBusy = true;
  try {
    const conexao = configurarConexao(opcoes || {});
    status(`${conexao.descricao}. Lendo e limpando a matéria com o motor ${motor.VERSAO}...`);

    const materia = await motor.extrairMateria(url);

    if (!materia || !materia.resultado || !materia.texto) {
      throw new Error('O motor não retornou o corpo completo da matéria.');
    }

    status('Matéria extraída. Salvando TXT...');
    const repetida = salvarResultado(materia);

    const detalhe = repetida
      ? ' A URL já existia e não foi repetida no histórico.'
      : ' Também foi adicionada ao histórico.';

    status('✓ Matéria salva em Downloads/ExtratorMaterias.' + detalhe + ' Você pode editar o conteúdo antes de copiar.');
    return {
      ok: true,
      formatado: materia.resultado,
      url: materia.url,
      veiculo: materia.veiculo,
      titulo: materia.titulo,
      subtitulo: materia.subtitulo,
      autor: materia.autor,
      data: materia.data,
      corpoCaracteres: String(materia.texto || '').length,
      repetida,
      pasta: pastaDownload(),
      versaoMotor: motor.VERSAO
    };
  } catch (erro) {
    const mensagem = erro?.message || String(erro);
    status('Erro: ' + mensagem);
    return { ok: false, erro: mensagem };
  } finally {
    extractionBusy = false;
  }
}

function configurarCorretorOrtograficoPtBR(janela) {
  const ses = janela.webContents.session;
  try {
    ses.setSpellCheckerEnabled(true);
    const disponiveis = Array.isArray(ses.availableSpellCheckerLanguages)
      ? ses.availableSpellCheckerLanguages
      : [];

    const exato = disponiveis.find(i => String(i).toLowerCase() === 'pt-br');
    const portugues = disponiveis.find(i => /^pt(?:-|$)/i.test(String(i)));
    const escolhido = exato || portugues || '';

    if (escolhido) {
      ses.setSpellCheckerLanguages([escolhido]);
      idiomaCorretor = escolhido;
    } else {
      idiomaCorretor = 'pt-BR';
    }
  } catch (_) {
    idiomaCorretor = 'pt-BR';
  }

  janela.webContents.on('context-menu', (_event, params) => {
    if (!params.isEditable) return;

    const template = [];
    const palavra = String(params.misspelledWord || '').trim();
    const sugestoes = Array.isArray(params.dictionarySuggestions)
      ? params.dictionarySuggestions.slice(0, 8)
      : [];

    if (palavra) {
      if (sugestoes.length) {
        for (const sugestao of sugestoes) {
          template.push({
            label: sugestao,
            click: () => janela.webContents.replaceMisspelling(sugestao)
          });
        }
      } else {
        template.push({ label: 'Sem sugestões de correção', enabled: false });
      }

      template.push({ type: 'separator' });
      template.push({
        label: `Adicionar “${palavra}” ao dicionário`,
        click: () => janela.webContents.session.addWordToSpellCheckerDictionary(palavra)
      });
      template.push({ type: 'separator' });
    }

    template.push(
      { role: 'cut', label: 'Recortar' },
      { role: 'copy', label: 'Copiar' },
      { role: 'paste', label: 'Colar' },
      { type: 'separator' },
      { role: 'selectAll', label: 'Selecionar tudo' }
    );

    Menu.buildFromTemplate(template).popup({ window: janela });
  });
}


function obterUrlInicialDoMonitor() {
  try {
    const viaEnv = String(process.env.MONITOR_NEWS_URL || '').trim();
    if (viaEnv) return viaEnv;

    const prefixo = '--url=';
    const arg = process.argv.find((item) =>
      String(item || '').startsWith(prefixo)
    );

    if (!arg) return '';
    return String(arg).slice(prefixo.length).trim();
  } catch (_) {
    return '';
  }
}

function estaIncorporadoNoMonitor() {
  return String(process.env.MONITOR_EMBEDDED || '').trim() === '1';
}

function criarJanelaPrincipal() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 680,
    backgroundColor: '#08111f',
    autoHideMenuBar: true,
    icon: path.join(__dirname, 'assets', 'extrator-materias-moderno.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: true
    }
  });

  configurarCorretorOrtograficoPtBR(mainWindow);
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.webContents.on('did-finish-load', () => {
    const urlInicial = obterUrlInicialDoMonitor();
    const incorporado = estaIncorporadoNoMonitor();

    mainWindow.webContents.executeJavaScript(`
      (() => {
        const embedded = ${JSON.stringify(incorporado)};
        if (embedded) {
          document.body.classList.add('monitor-embedded');
        }

        const resultado = document.getElementById('resultado');
        if (resultado) {
          resultado.contentEditable = 'true';
          resultado.spellcheck = true;
          resultado.lang = 'pt-BR';
          resultado.setAttribute('role', 'textbox');
          resultado.setAttribute('aria-multiline', 'true');
          resultado.setAttribute(
            'aria-label',
            'Conteúdo extraído editável com corretor ortográfico PT-BR.'
          );
        }

        const campoUrl = document.getElementById('url');
        const inicial = ${JSON.stringify(urlInicial)};

        if (campoUrl && inicial) {
          campoUrl.value = inicial;
          campoUrl.dispatchEvent(
            new Event('input', { bubbles: true })
          );
          campoUrl.dispatchEvent(
            new Event('change', { bubbles: true })
          );
          campoUrl.scrollIntoView({
            block: 'center',
            behavior: 'auto'
          });
          campoUrl.focus();
          campoUrl.setSelectionRange(
            campoUrl.value.length,
            campoUrl.value.length
          );
        }
      })();
    `).catch(() => {});
  });
}

app.whenReady().then(() => {
  try {
    const config = carregarConfigProxyLocal();
    motor.prepararProxy('', '', { ...config, ATIVADO: false });
  } catch (_) {}

  criarJanelaPrincipal();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) criarJanelaPrincipal();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.handle('extrair-materia', async (_event, opcoes) => extrairMateriaGUI(opcoes));
ipcMain.handle('revisar-texto-rigido', async (_event, texto) => {
  try {
    const issues = await corretorRigido.revisarTexto(String(texto || ''));
    return {
      ok: true,
      issues,
      total: issues.length,
      idioma: 'pt-BR',
      modo: 'rigido'
    };
  } catch (erro) {
    return {
      ok: false,
      erro: erro?.message || String(erro),
      issues: [],
      total: 0
    };
  }
});
ipcMain.handle('obter-credenciais-assinante', async (_event, provedor) => {
  try {
    return obterResumoCredenciaisAssinante(provedor);
  } catch (erro) {
    return { ok: false, erro: erro?.message || String(erro), salvo: false, usuario: '', temSenha: false };
  }
});
ipcMain.handle('salvar-credenciais-assinante', async (_event, provedor, dados) => {
  try {
    return salvarCredenciaisAssinante(provedor, dados || {});
  } catch (erro) {
    return { ok: false, erro: erro?.message || String(erro) };
  }
});
ipcMain.handle('apagar-credenciais-assinante', async (_event, provedor) => {
  try {
    return apagarCredenciaisAssinante(provedor);
  } catch (erro) {
    return { ok: false, erro: erro?.message || String(erro) };
  }
});
ipcMain.handle('obter-estado', async () => ({
  ultimoExiste: fs.existsSync(caminhoUltimo()),
  historicoExiste: fs.existsSync(caminhoHistorico()),
  pasta: pastaDownload(),
  versaoMotor: motor.VERSAO,
  corretorOrtografico: {
    ativo: (() => {
      try { return !!mainWindow?.webContents?.session?.isSpellCheckerEnabled(); } catch (_) { return false; }
    })(),
    idioma: idiomaCorretor,
    rigido: true
  },
  proxyConfigurado: (() => {
    const c = carregarConfigProxyLocal();
    return !!(String(c.SERVIDOR || '').trim() && String(c.PORTA || '').trim());
  })(),
  acessoAssinanteValorSalvo: (() => {
    try { return obterResumoCredenciaisAssinante(PROVEDOR_VALOR_GLOBO).salvo; } catch (_) { return false; }
  })()
}));
ipcMain.handle('abrir-ultimo', async () => {
  if (!fs.existsSync(caminhoUltimo())) return { ok: false, erro: 'O arquivo ainda não foi criado.' };
  const erro = await shell.openPath(caminhoUltimo());
  return erro ? { ok: false, erro } : { ok: true };
});
ipcMain.handle('abrir-historico', async () => {
  if (!fs.existsSync(caminhoHistorico())) return { ok: false, erro: 'O arquivo ainda não foi criado.' };
  const erro = await shell.openPath(caminhoHistorico());
  return erro ? { ok: false, erro } : { ok: true };
});
ipcMain.handle('abrir-pasta', async () => {
  fs.mkdirSync(pastaDownload(), { recursive: true });
  const erro = await shell.openPath(pastaDownload());
  return erro ? { ok: false, erro } : { ok: true };
});
